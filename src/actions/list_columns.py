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


class ListColumnsParams(Params):
    table_name: str = Param(description="Name of table", required=True, primary=True, cef_types=["postgres table name"])
    table_schema: str = Param(description="Table schema", required=False, default="public")


class ListColumnsOutput(PermissiveActionOutput):
    column_name: str | None = OutputField(example_values=["user_name"], column_name="Column Name")
    data_type: str | None = OutputField(example_values=["character"], column_name="Data Type")
    column_default: str | None = OutputField(column_name="Default")
    is_nullable: str | None = OutputField(example_values=["YES"], column_name="Is Nullable")
    character_maximum_length: int | None = OutputField(example_values=[32])
    character_octet_length: int | None = OutputField()
    character_set_catalog: str | None = OutputField()
    character_set_name: str | None = OutputField()
    character_set_schema: str | None = OutputField()
    collation_catalog: str | None = OutputField()
    collation_name: str | None = OutputField()
    collation_schema: str | None = OutputField()
    datetime_precision: int | None = OutputField()
    domain_catalog: str | None = OutputField(cef_types=["domain"])
    domain_name: str | None = OutputField(cef_types=["domain"])
    domain_schema: str | None = OutputField(cef_types=["domain"])
    dtd_identifier: str | None = OutputField(example_values=["1"])
    generation_expression: str | None = OutputField()
    identity_cycle: str | None = OutputField()
    identity_generation: str | None = OutputField()
    identity_increment: str | None = OutputField()
    identity_maximum: str | None = OutputField()
    identity_minimum: str | None = OutputField()
    identity_start: str | None = OutputField()
    interval_precision: int | None = OutputField()
    interval_type: str | None = OutputField()
    is_generated: str | None = OutputField(example_values=["NEVER"])
    is_identity: str | None = OutputField(example_values=["NO"])
    is_self_referencing: str | None = OutputField(example_values=["NO"])
    is_updatable: str | None = OutputField(example_values=["YES"])
    maximum_cardinality: int | None = OutputField()
    numeric_precision: int | None = OutputField()
    numeric_precision_radix: int | None = OutputField()
    numeric_scale: int | None = OutputField()
    ordinal_position: int | None = OutputField(example_values=[1])
    scope_catalog: str | None = OutputField()
    scope_name: str | None = OutputField()
    scope_schema: str | None = OutputField()
    table_catalog: str | None = OutputField(example_values=["postgres"])
    table_name: str | None = OutputField(example_values=["users"], cef_types=["postgres table name"])
    table_schema: str | None = OutputField(example_values=["public"])
    udt_catalog: str | None = OutputField(example_values=["postgres"])
    udt_name: str | None = OutputField(example_values=["bpchar"])
    udt_schema: str | None = OutputField(example_values=["pg_catalog"])


class ListColumnsSummary(ActionOutput):
    total_columns: int


def list_columns(params: ListColumnsParams, soar: SOARClient, asset: Asset) -> list[ListColumnsOutput]:
    logger.progress("In action handler for: list_columns")
    table_name = params.table_name
    table_schema = params.table_schema

    with app.actions_manager.helper_context(asset) as helper:
        query = "SELECT * FROM information_schema.tables WHERE table_name = %s and table_schema = %s;"
        try:
            helper._cursor.execute(query, (table_name, table_schema))
        except auth.psycopg2.Error as e:
            raise ActionFailure(f"Error listing columns. Error string: '{e}'") from e

        results = helper._cursor.fetchall()
        if len(results) == 0:
            raise ActionFailure("The specified table could not be found")

        query = "SELECT * FROM INFORMATION_SCHEMA.COLUMNS where table_name = %s and table_schema = %s;"
        try:
            logger.debug("Executing query")
            helper._cursor.execute(query, (table_name, table_schema))
        except auth.psycopg2.Error as e:
            raise ActionFailure(f"Error listing columns. Error string: '{e}'") from e

        _, result = get_rows(helper._cursor)

    soar.set_summary(ListColumnsSummary(total_columns=len(result)))
    soar.set_message("Successfully listed all columns")
    return [ListColumnsOutput(**row) for row in result]
