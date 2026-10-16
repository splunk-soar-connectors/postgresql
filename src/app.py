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
from contextlib import nullcontext
from datetime import date, datetime

from soar_sdk.abstract import SOARClient
from soar_sdk.action_results import ActionResult, PermissiveActionOutput
from soar_sdk.actions_manager import ActionsManager
from soar_sdk.app import App
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

from .assets import Asset
from .auth import create_connection


logger = getLogger()

LEGACY_ACTIONS = frozenset({"test_connectivity", "run_query", "list_columns", "list_tables"})


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
        import psycopg2

        self._connection = create_connection(self.asset)
        try:
            self._cursor = self._connection.cursor()
        except psycopg2.Error as e:
            self.close()
            raise ActionFailure("Database connection failed") from e
        logger.progress("Database connection established")
        return self

    def close(self):
        import psycopg2

        for resource in (self._cursor, self._connection):
            try:
                if resource is not None:
                    resource.close()
            except psycopg2.Error:
                pass
        self._cursor = self._connection = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.close()

    @staticmethod
    def _get_format_vars(format_vars):
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
        self._current_action_params = None

    def handle(self, input_data, handle=None):
        try:
            return super().handle(input_data, handle=handle)
        finally:
            if self._action_helper is not None:
                self._action_helper.close()
            self._action_helper = None

    def handle_action(self, param):
        self._current_action_params = dict(param)
        try:
            return super().handle_action(param)
        finally:
            self._current_action_params = None

    def add_result(self, action_result):
        """Restore legacy messages and input parameters after SDK adaptation."""
        action_identifier = self.get_action_identifier()
        if action_identifier in LEGACY_ACTIONS:
            message = action_result.get_message()
            prefix = f"Action failure in {action_identifier.replace('_', ' ')}: "
            if message.startswith(prefix):
                message = message[len(prefix) :]
            if action_identifier == "test_connectivity" and action_result.get_status():
                message = ""

            param = self._current_action_params if self._current_action_params is not None else action_result.get_param()
            if message != action_result.get_message() or param != action_result.get_param():
                legacy_result = ActionResult(status=action_result.get_status(), message=message, param=param)
                for row in action_result.get_data():
                    legacy_result.add_data(row)
                if summary := action_result.get_summary():
                    legacy_result.set_summary(summary)
                action_result = legacy_result

        return super().add_result(action_result)

    def helper_context(self, asset):
        if self._current_action_params is None:
            return PostgresqlHelper(asset)
        if self._action_helper is None:
            self._action_helper = PostgresqlHelper(asset).connect()
        return nullcontext(self._action_helper)


app.actions_manager = PostgresqlActionsManager()


@app.test_connectivity()
def test_connectivity(soar: SOARClient, asset: Asset) -> None:
    """Validate the asset configuration for connectivity using supplied configuration."""
    import psycopg2

    try:
        with app.actions_manager.helper_context(asset) as helper:
            query = "SELECT version();"
            try:
                helper._cursor.execute(query)
            except psycopg2.Error as e:
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


from .actions import register_actions


register_actions(app)


if __name__ == "__main__":
    app.cli()
