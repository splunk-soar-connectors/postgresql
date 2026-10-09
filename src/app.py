# Copyright (c) 2017-2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

import csv
import json
import tempfile
from datetime import date, datetime

import psycopg2
from soar_sdk.abstract import SOARClient
from soar_sdk.action_results import ActionResult, PermissiveActionOutput
from soar_sdk.actions_manager import ActionsManager
from soar_sdk.app import App
from soar_sdk.asset import AssetField, BaseAsset, FieldCategory
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger


logger = getLogger()

ALLOWED_OTHER_OPTIONS = frozenset(
    {
        "application_name",
        "client_encoding",
        "connect_timeout",
        "keepalives",
        "keepalives_count",
        "keepalives_idle",
        "keepalives_interval",
        "options",
        "port",
        "sslmode",
        "target_session_attrs",
    }
)
LEGACY_ACTIONS = frozenset({"test_connectivity", "run_query", "list_columns", "list_tables"})


class Asset(BaseAsset):
    host: str = AssetField(description="Hostname or IP address", required=True, category=FieldCategory.CONNECTIVITY)
    username: str = AssetField(description="Username", required=True, category=FieldCategory.CONNECTIVITY)
    password: str = AssetField(description="Password", required=True, sensitive=True, category=FieldCategory.CONNECTIVITY)
    database: str = AssetField(description="Database", required=True, category=FieldCategory.CONNECTIVITY)
    other: str | None = AssetField(
        description="JSON object of supported non-file libpq connection parameters. The verify_server_cert setting overrides sslmode",
        required=False,
        category=FieldCategory.CONNECTIVITY,
    )
    verify_server_cert: bool = AssetField(
        description="Verify the PostgreSQL server certificate and hostname",
        required=False,
        default=True,
        category=FieldCategory.CONNECTIVITY,
    )
    ssl_root_cert: str | None = AssetField(
        description="PEM file containing trusted certificate authority certificates. When omitted, libpq uses its default root certificate file",
        required=False,
        is_file=True,
        category=FieldCategory.CONNECTIVITY,
    )


app = App(
    name="PostgreSQL",
    app_type="information",
    logo="logo_postgresql.svg",
    logo_dark="logo_postgresql_dark.svg",
    product_vendor="PostgreSQL",
    product_name="PostgreSQL",
    publisher="Splunk",
    appid="958012c1-4ad4-4e94-9ad2-6a0ffe053532",
    min_phantom_version="7.0.0",
    fips_compliant=True,
    asset_cls=Asset,
)


class PostgresqlHelper:
    def __init__(self, asset: Asset):
        self.asset = asset
        self._connection = None
        self._cursor = None
        self._statement_timeout_set = False

    def connect(self):
        config = self.asset.model_dump()
        host = config["host"]
        username = config["username"]
        password = config["password"]
        database = config["database"]
        other = config.get("other")

        if other:
            try:
                other_dict = json.loads(other)
            except Exception as e:
                raise ActionFailure("'other' is invalid") from e
            if not isinstance(other_dict, dict):
                raise ActionFailure("'other' must be a JSON object")
        else:
            other_dict = {}

        unsupported_options = sorted(set(other_dict) - ALLOWED_OTHER_OPTIONS)
        if unsupported_options:
            raise ActionFailure("'other' contains unsupported connection parameter(s): " + ", ".join(unsupported_options))

        other_dict["sslmode"] = "verify-full" if config.get("verify_server_cert", True) else "require"

        ssl_root_cert_file = None
        try:
            if ssl_root_cert := config.get("ssl_root_cert"):
                ssl_root_cert_file = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".pem")
                ssl_root_cert_file.write(ssl_root_cert)
                ssl_root_cert_file.flush()
                other_dict["sslrootcert"] = ssl_root_cert_file.name

            self._connection = psycopg2.connect(user=username, password=password, dbname=database, host=host, **other_dict)
            self._cursor = self._connection.cursor()
        except Exception as e:
            self.close()
            raise ActionFailure("Database connection failed") from e
        finally:
            if ssl_root_cert_file:
                ssl_root_cert_file.close()

        logger.progress("Database connection established")
        return self

    def close(self):
        if self._cursor is not None:
            try:
                self._cursor.close()
            except Exception:
                pass
            self._cursor = None
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.close()

    @staticmethod
    def _get_format_vars(param):
        format_vars = param.get("format_vars")
        if format_vars:
            format_vars = next(csv.reader([format_vars], quotechar='"', skipinitialspace=True, escapechar="\\"))
        return format_vars

    @staticmethod
    def _deduplicate_column_names(columns):
        names = []
        used = set()
        for index, column in enumerate(columns):
            base_name = column[0] or f"column_{index}"
            name = base_name
            suffix = index
            while name in used:
                name = f"{base_name}__duplicate_{suffix}"
                suffix += 1
            names.append(name)
            used.add(name)
        return names

    def get_rows(self):
        columns = self._cursor.description
        result = []
        if columns is not None:
            column_names = self._deduplicate_column_names(columns)
            for value in self._cursor.fetchall():
                info = {}
                for index, column in enumerate(value):
                    if isinstance(column, (datetime, date)):
                        column = column.isoformat()
                    info[column_names[index]] = column
                result.append(info)
        return columns, result


class PostgresqlActionOutput(PermissiveActionOutput):
    """Keep the legacy aggregate output paths in the generated manifest."""

    @classmethod
    def _to_json_schema(cls, parent_datapath="action_result.data.*", column_order_counter=None):
        if parent_datapath == "action_result.data.*":
            yield {"data_path": "action_result.data", "data_type": "string"}
            yield {"data_path": "action_result.summary", "data_type": "string"}
        yield from super()._to_json_schema(parent_datapath, column_order_counter)


class PostgresqlActionsManager(ActionsManager):
    """Preserve legacy action results and SQL connection lifetime."""

    def __init__(self):
        super().__init__()
        self._action_helper = None
        self.current_action_params = None
        self._current_action_identifier = None

    def handle(self, input_data, handle=None):
        self._current_action_identifier = input_data.identifier
        self._action_helper = None
        try:
            return super().handle(input_data, handle=handle)
        finally:
            if self._action_helper is not None:
                self._action_helper.close()
            self._action_helper = None
            self.current_action_params = None
            self._current_action_identifier = None

    def handle_action(self, param):
        self.current_action_params = dict(param)
        try:
            return super().handle_action(param)
        finally:
            self.current_action_params = None

    def add_result(self, action_result):
        """Restore legacy messages and input parameters after SDK adaptation."""
        if self._current_action_identifier in LEGACY_ACTIONS:
            message = action_result.get_message()
            prefix = f"Action failure in {self._current_action_identifier.replace('_', ' ')}: "
            if message.startswith(prefix):
                message = message[len(prefix) :]
            if self._current_action_identifier == "test_connectivity" and action_result.get_status():
                message = ""

            param = self.current_action_params if self.current_action_params is not None else action_result.get_param()
            if message != action_result.get_message() or param != action_result.get_param():
                legacy_result = ActionResult(status=action_result.get_status(), message=message, param=param)
                for row in action_result.get_data():
                    legacy_result.add_data(row)
                if summary := action_result.get_summary():
                    legacy_result.set_summary(summary)
                action_result = legacy_result

        return super().add_result(action_result)

    def get_action_helper(self, asset):
        if self._current_action_identifier not in ("run_query", "make_request"):
            return None
        if self._action_helper is None:
            helper = PostgresqlHelper(asset)
            helper.connect()
            self._action_helper = helper
        return self._action_helper

    def get_action_params(self, params):
        if self.current_action_params is not None:
            return self.current_action_params
        return params.model_dump()


app.actions_manager = PostgresqlActionsManager()


@app.test_connectivity()
def test_connectivity(soar: SOARClient, asset: Asset) -> None:
    """Validate the asset configuration for connectivity using supplied configuration."""
    try:
        with PostgresqlHelper(asset) as helper:
            query = "SELECT version();"
            try:
                helper._cursor.execute(query)
            except Exception as e:
                raise ActionFailure(f"Test Connectivity Failed. Error string: '{e}'") from e

            for row in helper._cursor:
                logger.progress("Using: %s", row)

            logger.progress("Test Connectivity Passed")
            soar.set_message("Test Connectivity Passed")
    except ActionFailure as e:
        if not e.message.startswith("Test Connectivity Failed"):
            logger.progress(e.message)
            raise ActionFailure("Test Connectivity Failed") from e
        raise


if __name__ == "__main__":
    app.cli()
