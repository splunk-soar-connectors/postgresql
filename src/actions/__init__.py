# Copyright (c) 2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from soar_sdk.app import App

from .list_columns import list_columns
from .list_tables import LIST_TABLES_VERBOSE, list_tables
from .make_request import MAKE_REQUEST_VERBOSE, make_request
from .run_query import RUN_QUERY_VERBOSE, RunQuerySummary, display_query_results, run_query


def register_actions(app: App) -> App:
    """Register the PostgreSQL actions on the app."""
    app.register_action(
        action=list_columns,
        description="List the columns of a table",
        action_type="investigate",
        read_only=True,
        render_as="table",
    )
    app.register_action(
        action=list_tables,
        description="List the tables in the database",
        action_type="investigate",
        read_only=True,
        verbose=LIST_TABLES_VERBOSE,
        render_as="table",
    )
    registered_make_request = app.make_request()(make_request)
    registered_make_request.meta.verbose = MAKE_REQUEST_VERBOSE
    # The legacy query view needs the raw callback, not the SDK view adapter.
    app.action(
        description="Run a query against a table or tables in the database",
        action_type="investigate",
        read_only=False,
        verbose=RUN_QUERY_VERBOSE,
        summary_type=RunQuerySummary,
        view_handler=display_query_results,
    )(run_query)
    return app
