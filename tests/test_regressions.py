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
"""Focused regressions that the SOAR app-tests do not cover."""

import json
import sys
from datetime import date, datetime
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from soar_sdk.exceptions import ActionFailure

from src.actions.make_request import PostgresqlMakeRequestParams, make_request
from src.actions.run_query import RunQueryParams, display_query_results, run_query
from src.app import Asset, PostgresqlHelper, app


@pytest.fixture
def asset():
    return Asset(
        host="db.example",
        username="analyst",
        password="secret",  # pragma: allowlist secret
        database="cases",
    )


@pytest.fixture
def database(monkeypatch):
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.description = None
    cursor.rowcount = -1
    connect = MagicMock(return_value=connection)
    psycopg2 = ModuleType("psycopg2")
    psycopg2.connect = connect
    monkeypatch.setitem(sys.modules, "psycopg2", psycopg2)
    return connect, connection, cursor


def test_connection_uses_uploaded_ca_and_verifies_server(asset, database):
    connect, connection, _ = database
    asset.other = json.dumps({"port": 5433, "sslmode": "disable"})
    asset.ssl_root_cert = "-----BEGIN CERTIFICATE-----\nmock\n-----END CERTIFICATE-----"
    seen = {}

    def capture_connect(**kwargs):
        with open(kwargs["sslrootcert"], encoding="utf-8") as pem:
            seen["certificate"] = pem.read()
        seen["options"] = kwargs
        return connection

    connect.side_effect = capture_connect
    with PostgresqlHelper(asset):
        pass

    assert seen["options"]["sslmode"] == "verify-full"
    assert seen["options"]["port"] == 5433
    assert seen["certificate"] == asset.ssl_root_cert


def test_connection_failure_does_not_expose_database_details(asset, database):
    connect, _, _ = database
    connect.side_effect = RuntimeError("secret hostname and password")
    with pytest.raises(ActionFailure, match="Database connection failed") as error:
        PostgresqlHelper(asset).connect()
    assert "secret" not in error.value.message


def test_run_query_keeps_duplicate_columns_dates_and_csv_values(asset, database):
    _, connection, cursor = database
    cursor.description = [("value",), ("value",), ("created",)]
    cursor.fetchall.return_value = [("one", "two", date(2026, 1, 2)), ("three", "four", datetime(2026, 1, 2, 3, 4))]
    cursor.rowcount = 2
    soar = MagicMock()

    output = run_query.__wrapped__(RunQueryParams(query="select %s, %s", format_vars='"a,b", c'), soar, asset)

    cursor.execute.assert_called_once_with("select %s, %s", ["a,b", "c"])
    connection.commit.assert_called_once()
    assert [row.model_dump() for row in output] == [
        {"value": "one", "value__duplicate_1": "two", "created": "2026-01-02"},
        {"value": "three", "value__duplicate_1": "four", "created": "2026-01-02T03:04:00"},
    ]
    assert soar.set_summary.call_args.args[0].total_rows == 2


def test_run_query_reuses_connection_across_parameter_sets(asset, database):
    connect, connection, cursor = database
    parameters = [
        {"query": "UPDATE cases SET state = 'done'", "no_commit": True},
        {"query": "SELECT 1", "no_commit": False},
    ]
    input_data = SimpleNamespace(
        identifier="run_query", model_dump_json=lambda: json.dumps({"identifier": "run_query", "parameters": parameters})
    )
    with patch.object(app, "_build_magic_args", return_value={"soar": MagicMock(), "asset": asset}):
        app.actions_manager.handle(input_data)

    connect.assert_called_once()
    assert [call.args[0] for call in cursor.execute.call_args_list] == [param["query"] for param in parameters]
    connection.commit.assert_called_once()
    connection.close.assert_called_once()


def test_make_request_get_passes_explicit_transaction_sql_unchanged(asset, database):
    _, connection, cursor = database
    query = "SET TRANSACTION READ WRITE; UPDATE cases SET state = 'done'; COMMIT;"

    make_request.__wrapped__(PostgresqlMakeRequestParams(http_method="GET", endpoint=query), asset)

    cursor.execute.assert_called_once_with(query, None)
    connection.set_session.assert_not_called()
    connection.commit.assert_not_called()


def test_make_request_timeout_does_not_carry_to_next_parameter_set(asset, database):
    _, connection, cursor = database
    parameters = [
        {"http_method": "GET", "endpoint": "SELECT 1", "timeout": 3},
        {"http_method": "GET", "endpoint": "SELECT 2"},
    ]
    input_data = SimpleNamespace(
        identifier="make_request", model_dump_json=lambda: json.dumps({"identifier": "make_request", "parameters": parameters})
    )
    with patch.object(app, "_build_magic_args", return_value={"asset": asset}):
        app.actions_manager.handle(input_data)

    assert [call.args[0] for call in cursor.execute.call_args_list] == [
        "SELECT set_config('statement_timeout', %s, true)",
        "SELECT 1",
        "SET LOCAL statement_timeout TO DEFAULT",
        "SELECT 2",
    ]
    connection.commit.assert_not_called()


def test_query_widget_keeps_each_result_and_empty_state():
    first_result = SimpleNamespace(get_data=lambda: [{"z": "<safe>", "a": 1}])
    second_result = SimpleNamespace(get_data=lambda: [{"b": 2}])
    empty_result = SimpleNamespace(get_data=lambda: [])
    context = {}

    html = display_query_results(None, [(None, [first_result, second_result, empty_result])], context)

    assert [result["headers"] for result in context["results"]] == [["a", "z"], ["b"], []]
    assert html.count('<table class="phantom-table dataTable">') == 2
    assert "&lt;safe&gt;" in html
    assert "No data found" in html
