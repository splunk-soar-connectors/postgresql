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

from contextlib import nullcontext

from pydantic import field_validator
from soar_sdk.abstract import SOARClient
from soar_sdk.action_results import ActionOutput, ActionResult
from soar_sdk.logging import getLogger
from soar_sdk.params import Param, Params
from soar_sdk.views.template_renderer import get_template_renderer, get_templates_dir

from ..app import Asset, PostgresqlActionOutput, PostgresqlActionsManager, PostgresqlHelper, app


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

    @field_validator("format_vars", mode="before")
    @classmethod
    def normalize_format_vars(cls, value):
        if isinstance(value, (int, float)):
            return str(value)
        return value

    @field_validator("no_commit", mode="before")
    @classmethod
    def normalize_no_commit(cls, value):
        if value is None or value == "":
            return False
        return value


class RunQueryOutput(PostgresqlActionOutput):
    pass


class RunQuerySummary(ActionOutput):
    total_rows: int


# Keep the raw view callback because the SDK view decorator flattens action results.
def display_query_results(provides, all_results, context):
    context["results"] = results = []

    for summary, action_results in all_results:
        for result in action_results:
            data = result.get_data()
            headers = sorted(data[0].keys()) if data else []
            rows = [[{"value": item.get(header)} for header in headers] for item in data]
            results.append({"headers": headers, "data": rows})

    context["prerender"] = True
    renderer = get_template_renderer("jinja", get_templates_dir(globals()))
    return renderer.render_template("postgresql_run_query.html", context)


@app.action(
    description="Run a query against a table or tables in the database",
    action_type="investigate",
    read_only=False,
    verbose=RUN_QUERY_VERBOSE,
    summary_type=RunQuerySummary,
    view_handler=display_query_results,
)
def run_query(params: RunQueryParams, soar: SOARClient, asset: Asset) -> list[RunQueryOutput]:
    logger.progress("In action handler for: run_query")
    query = params.query
    format_vars = PostgresqlHelper._get_format_vars(params.model_dump())
    actions_manager = app.actions_manager
    helper = None
    failure_params = params.model_dump()
    if isinstance(actions_manager, PostgresqlActionsManager):
        helper = actions_manager.get_action_helper(asset)
        failure_params = actions_manager.get_action_params(params)
    helper_context = nullcontext(helper) if helper is not None else PostgresqlHelper(asset)

    with helper_context as helper:
        try:
            logger.debug("Executing query")
            helper._cursor.execute(query, format_vars)
        except Exception as e:
            return ActionResult(
                False,
                f"Error running query. Error string: '{e}'",
                failure_params,
            )

        if not params.no_commit:
            try:
                helper._connection.commit()
            except Exception as e:
                return ActionResult(
                    False,
                    f"Unable to commit changes. Error string: '{e}'",
                    failure_params,
                )

        try:
            _, result = helper.get_rows()
        except Exception as e:
            return ActionResult(
                False,
                f"Unable to retrieve results from query. Error string: '{e}'",
                failure_params,
            )

        if helper._cursor.rowcount > 0:
            total_rows = helper._cursor.rowcount
        else:
            total_rows = 0

    soar.set_summary(RunQuerySummary(total_rows=total_rows))
    soar.set_message("Successfully ran query")
    return [RunQueryOutput(**row) for row in result]
