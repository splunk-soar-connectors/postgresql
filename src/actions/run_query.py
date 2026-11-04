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
from soar_sdk.action_results import ActionOutput, PermissiveActionOutput
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger
from soar_sdk.params import Param, Params

from ..asset import Asset
from ..auth import get_session
from ..utils import get_format_vars, get_rows


logger = getLogger()

RUN_QUERY_VERBOSE = (
    'It is recommended to use the <b>format_vars</b> parameter when applicable. For example, if you wanted to find a specific IP, you could set the <b>query</b> to a formatted string, like "select * from my_hosts where ip = %s" (note the use of %s), and set <b>format_vars</b> to the IP address. '
    "This will ensure the inputs are safely sanitized and avoid SQL injection attacks. Regardless of the type of input it's expecting, the only format specifier which should be used is %s.<br>"
    "Setting <b>no_commit</b> will make it so the App does not commit any changes made to the database (so you can ensure it's a read only query).<br><br>"
    "The <b>format_vars</b> parameter accepts a comma seperated list. You can escape commas by surrounding them in double quotes, and escape double quotes with a backslash. Assuming you have a list of values for the format vars, you can employ this code in your playbooks to properly format it into a string:<br> "
    "<code>format_vars_str = ','.join(['\"{}\"'.format(str(x).replace('\\\\', '\\\\\\\\').replace('\"', '\\\\\"')) for x in format_vars_list])</code>."
)


class RunQueryParams(Params):
    query: str = Param(description="Query string", required=True, primary=True, cef_types=["sql query"])
    format_vars: str | None = Param(description="Comma separated list of variables", required=False)
    no_commit: bool = Param(description="Do not commit changes to database", required=False, default=False)


class RunQueryOutput(PermissiveActionOutput):
    pass


class RunQuerySummary(ActionOutput):
    total_rows: int


def run_query(params: RunQueryParams, soar: SOARClient, asset: Asset) -> list[RunQueryOutput]:
    logger.progress("In action handler for: run_query")
    query = params.query
    format_vars = get_format_vars(params.format_vars)

    with get_session(asset) as session:
        try:
            logger.debug("Executing query")
            session._cursor.execute(query, format_vars)
        except Exception as e:
            raise ActionFailure(f"Error running query. Error string: '{e}'") from e

        if not params.no_commit:
            try:
                session._connection.commit()
            except Exception as e:
                raise ActionFailure(f"Unable to commit changes. Error string: '{e}'") from e

        try:
            _, result = get_rows(session._cursor)
        except Exception as e:
            raise ActionFailure(f"Unable to retrieve results from query. Error string: '{e}'") from e

        total_rows = max(session._cursor.rowcount, 0)

    soar.set_summary(RunQuerySummary(total_rows=total_rows))
    soar.set_message("Successfully ran query")
    return [RunQueryOutput(**row) for row in result]
