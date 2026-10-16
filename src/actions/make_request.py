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

import json
from contextlib import contextmanager

from soar_sdk.action_results import MakeRequestOutput
from soar_sdk.exceptions import ActionFailure
from soar_sdk.params import MakeRequestParams, Param

from .. import auth
from ..app import PostgresqlHelper, app, get_format_vars, get_rows
from ..assets import Asset


READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class PostgresqlMakeRequestParams(MakeRequestParams):
    http_method: str = Param(
        description="GET, HEAD, or OPTIONS skips the connector's commit. POST, PUT, PATCH, or DELETE commits after SQL execution.",
        required=True,
        value_list=["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"],
    )
    endpoint: str = Param(description="SQL statement to execute on the configured PostgreSQL database", required=True)
    headers: str | None = Param(description="Unsupported for PostgreSQL; providing headers fails the action", required=False)
    query_parameters: str | None = Param(
        description="SQL bind values as a JSON list or object, or in the run query action's CSV format",
        required=False,
    )
    body: str | None = Param(
        description="SQL bind values as a JSON list or object, or in the run query action's CSV format. Do not provide both body and query_parameters",
        required=False,
    )
    timeout: int | None = Param(description="SQL statement timeout in seconds", required=False)
    verify_ssl: bool | None = Param(
        description="Unused; SSL verification is controlled by the asset's verify_server_cert setting",
        required=False,
        default=None,
    )


def _get_bind_values(value: str | None):
    if not value:
        return None
    if value.lstrip().startswith(("[", "{")):
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise ActionFailure("SQL bind values must be valid JSON or CSV") from e
    return get_format_vars(value)


@contextmanager
def _rollback_on_failure(helper: PostgresqlHelper):
    try:
        yield
    except ActionFailure:
        try:
            helper._connection.rollback()
        finally:
            helper._statement_timeout_set = False
        raise


def make_request(params: PostgresqlMakeRequestParams, asset: Asset) -> MakeRequestOutput:
    """Execute SQL through the configured PostgreSQL connection."""
    http_method = params.http_method.upper()
    if http_method not in READ_METHODS | WRITE_METHODS:
        raise ActionFailure("Unsupported method for PostgreSQL make request")
    if params.endpoint.lstrip().lower().startswith(("http://", "https://")):
        raise ActionFailure("The endpoint must be a SQL statement, not a URL")
    if params.headers:
        raise ActionFailure("Headers are not supported for PostgreSQL requests")
    if params.query_parameters and params.body:
        raise ActionFailure("Provide SQL bind values in either query_parameters or body, not both")
    if params.timeout is not None and params.timeout <= 0:
        raise ActionFailure("Timeout must be greater than zero")

    query = params.endpoint
    format_vars = _get_bind_values(params.query_parameters or params.body)
    with app.actions_manager.helper_context(asset) as helper, _rollback_on_failure(helper):
        if params.timeout is not None:
            try:
                helper._cursor.execute("SELECT set_config('statement_timeout', %s, true)", (str(params.timeout * 1000),))
            except auth.psycopg2.Error as e:
                raise ActionFailure("Unable to set SQL statement timeout") from e
            helper._statement_timeout_set = True
        elif helper._statement_timeout_set:
            try:
                helper._cursor.execute("SET LOCAL statement_timeout TO DEFAULT")
            except auth.psycopg2.Error as e:
                raise ActionFailure("Unable to reset SQL statement timeout") from e
            helper._statement_timeout_set = False

        try:
            helper._cursor.execute(query, format_vars)
        except (auth.psycopg2.Error, IndexError, KeyError, TypeError, ValueError) as e:
            raise ActionFailure("Error running query") from e

        if http_method in WRITE_METHODS:
            try:
                helper._connection.commit()
            except auth.psycopg2.Error as e:
                raise ActionFailure("Unable to commit changes") from e

        try:
            columns, result = get_rows(helper._cursor)
        except auth.psycopg2.Error as e:
            raise ActionFailure("Unable to retrieve results from query") from e

        total_rows = max(helper._cursor.rowcount, 0)

    if columns is not None:
        response_body = json.dumps({"rows": result, "total_rows": total_rows}, default=str)
    else:
        response_body = json.dumps({"affected_rows": total_rows})
    return MakeRequestOutput(status_code=200, response_body=response_body)


MAKE_REQUEST_VERBOSE = (
    "Execute SQL on the configured PostgreSQL asset. GET, HEAD, and OPTIONS skip the connector's commit; "
    "POST, PUT, PATCH, and DELETE commit after execution. SQL transaction commands are passed through unchanged. endpoint is SQL; query_parameters or body "
    "supplies JSON or CSV bind values. response_body contains JSON rows or an affected row count."
)
