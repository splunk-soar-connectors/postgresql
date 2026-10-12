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
from soar_sdk.action_results import OutputField
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger
from soar_sdk.params import Param, Params

from ..app import Asset, PostgresqlActionOutput, PostgresqlHelper, app


logger = getLogger()


class ListColumnsParams(Params):
    table_name: str = Param(description="Name of table", required=True, primary=True, cef_types=["postgres table name"])
    table_schema: str = Param(description="Table schema", required=False, default="public")


class ListColumnsOutput(PostgresqlActionOutput):
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
    datetime_precision: str | None = OutputField()
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
    interval_precision: str | None = OutputField()
    interval_type: str | None = OutputField()
    is_generated: str | None = OutputField(example_values=["NEVER"])
    is_identity: str | None = OutputField(example_values=["NO"])
    is_self_referencing: str | None = OutputField(example_values=["NO"])
    is_updatable: str | None = OutputField(example_values=["YES"])
    maximum_cardinality: str | None = OutputField()
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


@app.action(
    description="List the columns of a table",
    action_type="investigate",
    read_only=True,
    render_as="table",
)
def list_columns(params: ListColumnsParams, soar: SOARClient, asset: Asset) -> list[ListColumnsOutput]:
    logger.progress("In action handler for: list_columns")
    table_name = params.table_name
    table_schema = params.table_schema

    with PostgresqlHelper(asset) as helper:
        query = "SELECT * FROM information_schema.tables WHERE table_name = %s and table_schema = %s;"
        try:
            helper._cursor.execute(query, (table_name, table_schema))
        except Exception as e:
            raise ActionFailure(f"Error listing columns. Error string: '{e}'") from e

        results = helper._cursor.fetchall()
        if len(results) == 0:
            raise ActionFailure("The specified table could not be found")

        query = "SELECT * FROM INFORMATION_SCHEMA.COLUMNS where table_name = %s and table_schema = %s;"
        try:
            logger.debug("Executing query")
            helper._cursor.execute(query, (table_name, table_schema))
        except Exception as e:
            raise ActionFailure(f"Error listing columns. Error string: '{e}'") from e

        columns = PostgresqlHelper._deduplicate_column_names(helper._cursor.description)
        result = [{columns[index]: column for index, column in enumerate(value)} for value in helper._cursor.fetchall()]

    soar.set_message("Successfully listed all columns")
    return [ListColumnsOutput(**row) for row in result]
