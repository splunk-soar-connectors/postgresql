"""Database-free regression tests for the PostgreSQL SDK actions."""

import json
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from soar_sdk.exceptions import ActionFailure

from src.actions.list_columns import ListColumnsOutput, ListColumnsParams, list_columns
from src.actions.list_tables import ListTablesOutput, ListTablesParams, list_tables
from src.actions.make_request import PostgresqlMakeRequestParams, make_request
from src.actions.run_query import RunQueryOutput, RunQueryParams, display_query_results, run_query
from src.app import Asset, PostgresqlHelper, app, test_connectivity as connectivity_action


@pytest.fixture
def asset():
    return Asset(host="db.example", username="analyst", password="secret", database="cases")


@pytest.fixture
def database(monkeypatch):
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.description = None
    cursor.rowcount = -1
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr("src.app.psycopg2.connect", connect)
    return connect, connection, cursor


@pytest.fixture
def soar_client():
    state = {"message": "", "summary": None}
    soar = MagicMock()
    soar.set_message.side_effect = lambda value: state.update(message=value)
    soar.get_message.side_effect = lambda: state["message"]
    soar.set_summary.side_effect = lambda value: state.update(summary=value)
    soar.get_summary.side_effect = lambda: state["summary"]
    return soar


def test_connection_options_tls_and_ca_file(asset, database):
    connect, connection, cursor = database
    asset.other = json.dumps({"port": 5433, "sslmode": "disable", "connect_timeout": 5})
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
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


def test_connection_verification_disabled_and_bad_options(asset, database):
    connect, _, _ = database
    asset.verify_server_cert = False
    with PostgresqlHelper(asset):
        pass
    assert connect.call_args.kwargs["sslmode"] == "require"

    asset.other = '{"service": "other"}'
    with pytest.raises(ActionFailure, match="unsupported connection parameter"):
        PostgresqlHelper(asset).connect()
    asset.other = "not-json"
    with pytest.raises(ActionFailure, match="'other' is invalid"):
        PostgresqlHelper(asset).connect()


def test_connection_error_is_generic(asset, database):
    connect, _, _ = database
    connect.side_effect = RuntimeError("secret hostname and password")
    with pytest.raises(ActionFailure, match="Database connection failed") as error:
        PostgresqlHelper(asset).connect()
    assert "secret" not in error.value.message


def test_test_connectivity_runs_version_query(asset, database):
    _, _, cursor = database
    cursor.__iter__.return_value = iter([("PostgreSQL 15",)])
    soar = MagicMock()
    connectivity_action.__wrapped__(soar, asset)
    cursor.execute.assert_called_once_with("SELECT version();")


def test_run_query_csv_duplicate_columns_and_dates(asset, database):
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
    soar.set_message.assert_called_once_with("Successfully ran query")


def test_run_query_no_commit_and_separate_failures(asset, database):
    _, connection, cursor = database
    run_query.__wrapped__(RunQueryParams(query="UPDATE x SET y = 1", no_commit=True), MagicMock(), asset)
    connection.commit.assert_not_called()

    cursor.execute.side_effect = RuntimeError("execute failed")
    result = run_query.__wrapped__(RunQueryParams(query="bad"), MagicMock(), asset)
    assert result.get_message() == "Error running query. Error string: 'execute failed'"
    assert result.get_param()["query"] == "bad"
    cursor.execute.side_effect = None

    connection.commit.side_effect = RuntimeError("commit failed")
    result = run_query.__wrapped__(RunQueryParams(query="UPDATE x SET y = 1"), MagicMock(), asset)
    assert result.get_message() == "Unable to commit changes. Error string: 'commit failed'"
    connection.commit.side_effect = None

    cursor.description = [("x",)]
    cursor.fetchall.side_effect = RuntimeError("fetch failed")
    result = run_query.__wrapped__(RunQueryParams(query="SELECT x FROM y"), MagicMock(), asset)
    assert result.get_message() == "Unable to retrieve results from query. Error string: 'fetch failed'"


def test_run_query_reuses_connection_across_parameter_sets(asset, database, soar_client):
    connect, connection, cursor = database
    parameters = [
        {"query": "UPDATE cases SET state = 'done'", "no_commit": True},
        {"query": "SELECT 1", "no_commit": False},
    ]
    input_data = SimpleNamespace(
        identifier="run_query", model_dump_json=lambda: json.dumps({"identifier": "run_query", "parameters": parameters})
    )
    with patch.object(app, "_build_magic_args", return_value={"soar": soar_client, "asset": asset}):
        app.actions_manager.handle(input_data)

    connect.assert_called_once()
    assert [call.args[0] for call in cursor.execute.call_args_list] == [param["query"] for param in parameters]
    connection.commit.assert_called_once()
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


def test_app_test_run_query_inputs_are_accepted(asset, database):
    _, connection, cursor = database
    params = RunQueryParams.model_validate({"query": "select %s", "format_vars": 21, "no_commit": ""})
    run_query.__wrapped__(params, MagicMock(), asset)
    assert params.format_vars == "21"
    assert params.no_commit is False
    cursor.execute.assert_called_once_with("select %s", ["21"])
    connection.commit.assert_called_once()


def test_sdk_run_query_result_matches_app_test(asset, database, soar_client):
    _, connection, cursor = database
    params = RunQueryParams.model_validate({"query": "CREATE TABLE cases (id int)", "no_commit": "", "format_vars": ""})
    with patch.object(app.actions_manager, "add_result") as add_result:
        assert run_query(params, soar_client, asset=asset) is True
    result = add_result.call_args.args[0]
    assert result.get_message() == "Successfully ran query"
    assert result.get_summary() == {"total_rows": 0}
    assert result.get_data() == []
    assert result.get_param()["no_commit"] is False
    cursor.execute.assert_called_once_with("CREATE TABLE cases (id int)", "")
    connection.commit.assert_called_once()


def test_sdk_run_query_failure_status_matches_app_test(asset, database, soar_client):
    _, _, cursor = database
    cursor.execute.side_effect = RuntimeError("backend syntax detail")
    params = RunQueryParams.model_validate({"query": "select *", "no_commit": ""})
    with patch.object(app.actions_manager, "add_result") as add_result:
        assert run_query(params, soar_client, asset=asset) is False
    result = add_result.call_args.args[0]
    assert result.get_message() == "Error running query. Error string: 'backend syntax detail'"
    assert result.get_param()["query"] == "select *"


def test_list_columns_sql_and_missing_table(asset, database):
    _, _, cursor = database
    cursor.fetchall.side_effect = [[("exists",)], [("name", "text")]]
    cursor.description = [("column_name",), ("data_type",)]
    output = list_columns.__wrapped__(ListColumnsParams(table_name="cases"), MagicMock(), asset)
    assert output[0].model_dump() == {"column_name": "name", "data_type": "text"}
    assert cursor.execute.call_args_list[0].args == (
        "SELECT * FROM information_schema.tables WHERE table_name = %s and table_schema = %s;",
        ("cases", "public"),
    )
    assert cursor.execute.call_args_list[1].args == (
        "SELECT * FROM INFORMATION_SCHEMA.COLUMNS where table_name = %s and table_schema = %s;",
        ("cases", "public"),
    )

    cursor.fetchall.side_effect = None
    cursor.fetchall.return_value = []
    with pytest.raises(ActionFailure, match="The specified table could not be found"):
        list_columns.__wrapped__(ListColumnsParams(table_name="missing"), MagicMock(), asset)


def test_list_tables_sql_and_missing_schema(asset, database):
    _, _, cursor = database
    cursor.fetchall.side_effect = [[("exists",)], [("cases",)]]
    cursor.description = [("table_name",)]
    output = list_tables.__wrapped__(ListTablesParams(), MagicMock(), asset)
    assert output[0].model_dump() == {"table_name": "cases"}
    assert cursor.execute.call_args_list[0].args == (
        "select * from information_schema.schemata where schema_name = %s;",
        ("public",),
    )
    assert cursor.execute.call_args_list[1].args == (
        "select * from information_schema.tables where table_schema = %s;",
        ("public",),
    )

    cursor.fetchall.side_effect = None
    cursor.fetchall.return_value = []
    with pytest.raises(ActionFailure, match="No matching table schemas could be found"):
        list_tables.__wrapped__(ListTablesParams(), MagicMock(), asset)


def test_empty_optional_schema_uses_public_for_app_tests():
    assert ListColumnsParams.model_validate({"table_name": "cases", "table_schema": ""}).table_schema == "public"
    assert ListTablesParams.model_validate({"table_schema": ""}).table_schema == "public"


def test_sdk_list_actions_return_app_test_messages(asset, database, soar_client):
    _, _, cursor = database
    cursor.description = [("table_name",)]
    cursor.fetchall.side_effect = [[("exists",)], [("cases",)]]
    with patch.object(app.actions_manager, "add_result") as add_result:
        assert list_tables(ListTablesParams.model_validate({"table_schema": ""}), soar_client, asset=asset) is True
    result = add_result.call_args.args[0]
    assert result.get_message() == "Successfully listed all tables"
    assert result.get_data() == [{"table_name": "cases"}]
    assert cursor.execute.call_args_list[0].args[1] == ("public",)

    soar_client.set_message("")
    cursor.reset_mock()
    cursor.description = [("column_name",), ("data_type",)]
    cursor.fetchall.side_effect = [[("exists",)], [("id", "integer")]]
    with patch.object(app.actions_manager, "add_result") as add_result:
        assert list_columns(ListColumnsParams.model_validate({"table_name": "cases", "table_schema": ""}), soar_client, asset=asset) is True
    result = add_result.call_args.args[0]
    assert result.get_message() == "Successfully listed all columns"
    assert result.get_data() == [{"column_name": "id", "data_type": "integer"}]
    assert cursor.execute.call_args_list[0].args[1] == ("cases", "public")


def test_list_columns_result_preserves_raw_parameters(asset, database, soar_client):
    _, _, cursor = database
    cursor.description = [("column_name",), ("data_type",)]
    cursor.fetchall.side_effect = [[("exists",)], [("id", "integer")]]
    param = {"table_name": "cases", "table_schema": ""}
    input_data = SimpleNamespace(
        identifier="list_columns", model_dump_json=lambda: json.dumps({"identifier": "list_columns", "parameters": [param]})
    )
    results = app.actions_manager.get_results()
    results.clear()
    with (
        patch.object(app, "_build_magic_args", return_value={"soar": soar_client, "asset": asset}),
        patch.object(app.soar_client, "get_message", side_effect=soar_client.get_message),
    ):
        app.actions_manager.handle(input_data)

    assert results[-1].get_status() is True
    assert results[-1].get_message() == "Successfully listed all columns"
    assert results[-1].get_param() == param
    assert results[-1].get_data() == [{"column_name": "id", "data_type": "integer"}]
    results.clear()


def test_list_action_failures_preserve_legacy_messages_and_parameters(asset, database, soar_client):
    _, _, cursor = database
    results = app.actions_manager.get_results()
    results.clear()
    param = {"table_name": "cases", "table_schema": ""}
    input_data = SimpleNamespace(
        identifier="list_columns", model_dump_json=lambda: json.dumps({"identifier": "list_columns", "parameters": [param]})
    )
    cursor.execute.side_effect = RuntimeError("backend detail")
    with patch.object(app, "_build_magic_args", return_value={"soar": soar_client, "asset": asset}):
        app.actions_manager.handle(input_data)
    assert results[-1].get_status() is False
    assert results[-1].get_message() == "Error listing columns. Error string: 'backend detail'"
    assert results[-1].get_param() == param

    results.clear()
    cursor.execute.side_effect = None
    cursor.fetchall.return_value = []
    param = {"table_schema": "missing"}
    input_data = SimpleNamespace(
        identifier="list_tables", model_dump_json=lambda: json.dumps({"identifier": "list_tables", "parameters": [param]})
    )
    with patch.object(app, "_build_magic_args", return_value={"soar": soar_client, "asset": asset}):
        app.actions_manager.handle(input_data)
    assert results[-1].get_status() is False
    assert results[-1].get_message() == "No matching table schemas could be found"
    assert results[-1].get_param() == param
    results.clear()


def test_sdk_test_connectivity_runs_legacy_sql(asset, database, soar_client):
    _, _, cursor = database
    cursor.__iter__.return_value = iter([("PostgreSQL mocked",)])
    with (
        patch.object(app, "_build_magic_args", return_value={"soar": soar_client, "asset": asset}),
        patch.object(app.actions_manager, "add_result") as add_result,
    ):
        assert connectivity_action(None, soar_client) is True
    cursor.execute.assert_called_once_with("SELECT version();")
    assert add_result.call_args.args[0].get_message() == "Test connectivity successful"


def test_connectivity_result_preserves_legacy_message(asset, database, soar_client):
    _, _, cursor = database
    cursor.__iter__.return_value = iter([("PostgreSQL mocked",)])
    input_data = SimpleNamespace(
        identifier="test_connectivity", model_dump_json=lambda: json.dumps({"identifier": "test_connectivity", "parameters": [{}]})
    )
    results = app.actions_manager.get_results()
    results.clear()
    with patch.object(app, "_build_magic_args", return_value={"soar": soar_client, "asset": asset}):
        app.actions_manager.handle(input_data)
    assert results[-1].get_status() is True
    assert results[-1].get_message() == ""
    assert results[-1].get_param() == {}

    results.clear()
    cursor.execute.side_effect = RuntimeError("version query failed")
    with patch.object(app, "_build_magic_args", return_value={"soar": soar_client, "asset": asset}):
        app.actions_manager.handle(input_data)
    assert results[-1].get_status() is False
    assert results[-1].get_message() == "Test Connectivity Failed. Error string: 'version query failed'"
    results.clear()


def test_make_request_no_commit_bound_values_and_rows(asset, database):
    _, connection, cursor = database
    cursor.description = [("id",), ("id",)]
    cursor.fetchall.return_value = [(1, 2)]
    cursor.rowcount = 1
    output = make_request.__wrapped__(
        PostgresqlMakeRequestParams(http_method="GET", endpoint="SELECT %s, %s", query_parameters="[1, 2]", timeout=3), asset
    )
    connection.set_session.assert_not_called()
    cursor.execute.assert_any_call("SELECT set_config('statement_timeout', %s, true)", ("3000",))
    cursor.execute.assert_any_call("SELECT %s, %s", [1, 2])
    connection.commit.assert_not_called()
    assert output.status_code == 200
    assert json.loads(output.response_body) == {"rows": [{"id": 1, "id__duplicate_1": 2}], "total_rows": 1}


def test_make_request_write_commits_and_returns_affected_count(asset, database):
    _, connection, cursor = database
    cursor.rowcount = 3
    output = make_request.__wrapped__(
        PostgresqlMakeRequestParams(http_method="POST", endpoint="UPDATE cases SET state = %(state)s", body='{"state": "done"}'), asset
    )
    cursor.execute.assert_called_once_with("UPDATE cases SET state = %(state)s", {"state": "done"})
    connection.commit.assert_called_once()
    assert json.loads(output.response_body) == {"affected_rows": 3}


def test_make_request_get_passes_transaction_sql_unchanged(asset, database):
    _, connection, cursor = database
    query = "SET TRANSACTION READ WRITE; UPDATE cases SET state = 'done'; COMMIT;"
    make_request.__wrapped__(PostgresqlMakeRequestParams(http_method="GET", endpoint=query), asset)
    cursor.execute.assert_called_once_with(query, None)
    connection.set_session.assert_not_called()
    connection.commit.assert_not_called()


def test_make_request_reuses_connection_across_parameter_sets(asset, database):
    connect, connection, cursor = database
    parameters = [
        {"http_method": "GET", "endpoint": "UPDATE cases SET state = 'done'"},
        {"http_method": "POST", "endpoint": "SELECT 1"},
    ]
    input_data = SimpleNamespace(
        identifier="make_request", model_dump_json=lambda: json.dumps({"identifier": "make_request", "parameters": parameters})
    )
    with patch.object(app, "_build_magic_args", return_value={"asset": asset}):
        app.actions_manager.handle(input_data)

    connect.assert_called_once()
    assert [call.args[0] for call in cursor.execute.call_args_list] == [param["endpoint"] for param in parameters]
    connection.commit.assert_called_once()
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


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


def test_sdk_make_request_returns_standard_output(asset, database, soar_client):
    _, connection, cursor = database
    cursor.description = [("id",)]
    cursor.fetchall.return_value = [(7,)]
    cursor.rowcount = 1
    params = PostgresqlMakeRequestParams(http_method="GET", endpoint="SELECT %s", query_parameters="[7]")
    with patch.object(app.actions_manager, "add_result") as add_result:
        assert make_request(params, soar_client, asset=asset) is True
    result = add_result.call_args.args[0]
    assert result.get_data()[0]["status_code"] == 200
    assert json.loads(result.get_data()[0]["response_body"]) == {"rows": [{"id": 7}], "total_rows": 1}
    connection.set_session.assert_not_called()
    connection.commit.assert_not_called()


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({"http_method": "GET", "endpoint": "https://example.test"}, "SQL statement, not a URL"),
        ({"http_method": "GET", "endpoint": "SELECT 1", "headers": "{}"}, "Headers are not supported"),
        ({"http_method": "GET", "endpoint": "SELECT 1", "query_parameters": "[1]", "body": "[2]"}, "either query_parameters or body"),
        ({"http_method": "GET", "endpoint": "SELECT 1", "timeout": 0}, "Timeout must be greater than zero"),
        ({"http_method": "GET", "endpoint": "SELECT 1", "body": "[invalid"}, "valid JSON or CSV"),
    ],
)
def test_make_request_invalid_input_does_not_connect(asset, database, params, message):
    connect, _, _ = database
    with pytest.raises(ActionFailure, match=message):
        make_request.__wrapped__(PostgresqlMakeRequestParams(**params), asset)
    connect.assert_not_called()


def test_query_view_sorted_headers_and_empty_state():
    result = SimpleNamespace(get_data=lambda: [{"z": 2, "a": 1}])
    empty_result = SimpleNamespace(get_data=lambda: [])
    context = {}
    html = display_query_results(None, [(None, [result, empty_result])], context)

    assert context["results"] == [
        {"headers": ["a", "z"], "data": [[{"value": 1}, {"value": 2}]]},
        {"headers": [], "data": []},
    ]
    assert context["prerender"] is True
    assert html.index('<th class="widget-th">a</th>') < html.index('<th class="widget-th">z</th>')
    assert "No data found" in html


def test_legacy_parent_output_paths_are_declared():
    for output in (RunQueryOutput, ListColumnsOutput, ListTablesOutput):
        paths = {field["data_path"] for field in output._to_json_schema()}
        assert {"action_result.data", "action_result.summary"} <= paths


def test_query_view_template_renders_table_and_empty_state():
    first_result = SimpleNamespace(get_data=lambda: [{"a": "<safe>"}])
    second_result = SimpleNamespace(get_data=lambda: [{"b": 2}])
    empty_result = SimpleNamespace(get_data=lambda: [])
    context = {}
    html = display_query_results(None, [(None, [first_result, second_result, empty_result])], context)

    assert [result["headers"] for result in context["results"]] == [["a"], ["b"], []]
    assert html.count('<table class="phantom-table dataTable">') == 2
    assert "&lt;safe&gt;" in html
    assert "No data found" in html
