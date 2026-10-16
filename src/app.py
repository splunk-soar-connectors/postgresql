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
from soar_sdk.actions_manager import ActionsManager
from soar_sdk.app import App
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

from . import auth
from .assets import Asset


logger = getLogger()


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
        self._connection = auth.create_connection(self.asset)
        try:
            self._cursor = self._connection.cursor()
        except auth.psycopg2.Error as e:
            self.close()
            raise ActionFailure("Database connection failed") from e
        logger.progress("Database connection established")
        return self

    def close(self):
        for resource in (self._cursor, self._connection):
            try:
                if resource is not None:
                    resource.close()
            except (AttributeError, auth.psycopg2.Error):
                pass
        self._cursor = self._connection = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.close()


class PostgresqlActionsManager(ActionsManager):
    """Keep one SQL connection for all parameters in an action run."""

    def __init__(self):
        super().__init__()
        self._action_helper = None
        self._handling_action = False

    def handle(self, input_data, handle=None):
        self._handling_action = True
        try:
            return super().handle(input_data, handle=handle)
        finally:
            if self._action_helper is not None:
                self._action_helper.close()
            self._action_helper = None
            self._handling_action = False

    def handle_action(self, param):
        if self.get_action_identifier() == "run_query":
            param = dict(param)
            if isinstance(param.get("format_vars"), (int, float)):
                param["format_vars"] = str(param["format_vars"])
            if param.get("no_commit") in (None, ""):
                param["no_commit"] = False
        return super().handle_action(param)

    def helper_context(self, asset):
        if not self._handling_action:
            return PostgresqlHelper(asset)
        if self._action_helper is None:
            self._action_helper = PostgresqlHelper(asset).connect()
        return nullcontext(self._action_helper)


app.actions_manager = PostgresqlActionsManager()


@app.test_connectivity()
def test_connectivity(soar: SOARClient, asset: Asset) -> None:
    """Validate the asset configuration for connectivity using supplied configuration."""
    try:
        with app.actions_manager.helper_context(asset) as helper:
            query = "SELECT version();"
            try:
                helper._cursor.execute(query)
            except auth.psycopg2.Error as e:
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


def get_format_vars(format_vars):
    if format_vars:
        format_vars = next(csv.reader([format_vars], quotechar='"', skipinitialspace=True, escapechar="\\"))
    return format_vars


def deduplicate_column_names(columns):
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


def get_rows(cursor):
    columns = cursor.description
    result = []
    if columns is not None:
        column_names = deduplicate_column_names(columns)
        for value in cursor.fetchall():
            info = {}
            for index, column in enumerate(value):
                if isinstance(column, (datetime, date)):
                    column = column.isoformat()
                info[column_names[index]] = column
            result.append(info)
    return columns, result


from .actions import register_actions


register_actions(app)


if __name__ == "__main__":
    app.cli()
