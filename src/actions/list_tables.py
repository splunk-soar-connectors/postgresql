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

from soar_sdk.abstract import SOARClient
from soar_sdk.action_results import ActionOutput, OutputField, PermissiveActionOutput
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger
from soar_sdk.params import Param, Params

from .. import auth
from ..app import app, get_rows
from ..assets import Asset


logger = getLogger()

LIST_TABLES_VERBOSE = (
    "Describes the structure of a table in the database by displaying information about its columns. "
    "The only tables which it will be able to query for must have a name composed of only alphanumeric characters + '_' and '$'."
)


class ListTablesParams(Params):
    table_schema: str = Param(description="Table schema", required=False, default="public")


class ListTablesOutput(PermissiveActionOutput):
    table_name: str | None = OutputField(example_values=["users"], cef_types=["postgres table name"], column_name="Table Name")
    is_insertable_into: str | None = OutputField(example_values=["YES"], column_name="Insertable")
    commit_action: str | None = OutputField()
    is_typed: str | None = OutputField(example_values=["NO"])
    reference_generation: str | None = OutputField()
    self_referencing_column_name: str | None = OutputField()
    table_catalog: str | None = OutputField(example_values=["postgres"])
    table_schema: str | None = OutputField(example_values=["public"])
    table_type: str | None = OutputField(example_values=["BASE TABLE"])
    user_defined_type_catalog: str | None = OutputField()
    user_defined_type_name: str | None = OutputField()
    user_defined_type_schema: str | None = OutputField()


class ListTablesSummary(ActionOutput):
    total_tables: int


def list_tables(params: ListTablesParams, soar: SOARClient, asset: Asset) -> list[ListTablesOutput]:
    logger.progress("In action handler for: list_tables")
    table_schema = params.table_schema

    with app.actions_manager.helper_context(asset) as helper:
        query = "select * from information_schema.schemata where schema_name = %s;"
        try:
            helper._cursor.execute(query, (table_schema,))
        except auth.psycopg2.Error as e:
            raise ActionFailure(f"Error retrieving schemata. Error string: '{e}'") from e

        results = helper._cursor.fetchall()
        if len(results) == 0:
            raise ActionFailure("No matching table schemas could be found")

        query = "select * from information_schema.tables where table_schema = %s;"
        try:
            logger.debug("Executing query")
            helper._cursor.execute(query, (table_schema,))
        except auth.psycopg2.Error as e:
            raise ActionFailure(f"Error listing tables. Error string: '{e}'") from e

        _, result = get_rows(helper._cursor)

    soar.set_summary(ListTablesSummary(total_tables=len(result)))
    soar.set_message("Successfully listed all tables")
    return [ListTablesOutput(**row) for row in result]
