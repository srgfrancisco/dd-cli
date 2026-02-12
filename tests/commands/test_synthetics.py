"""Tests for Synthetics commands."""

import json
from unittest.mock import Mock, patch


def _make_test(
    public_id, name, test_type="api", status="live", locations=None, tags=None, message=""
):
    """Factory to create a mock Synthetics test object."""
    test = Mock()
    test.public_id = public_id
    test.name = name
    test.type = test_type
    test.status = status
    test.locations = locations or ["aws:us-east-1"]
    test.tags = tags or []
    test.message = message
    return test


def _make_result(result_id, status, check_time, dc_id):
    """Factory to create a mock Synthetics result object."""
    result = Mock()
    result.result_id = result_id
    result.status = status
    result.check_time = check_time
    result.dc_id = dc_id
    return result


def _make_trigger_result(public_id, result_id):
    """Factory to create a mock trigger result object."""
    triggered = Mock()
    triggered.public_id = public_id
    triggered.result_id = result_id
    return triggered


# --- list tests ---


def test_list_tests_table(mock_client, runner):
    """Test listing Synthetics tests in table format."""
    from ddogctl.commands.synthetics import synthetics

    tests = [
        _make_test("abc-123", "HealthCheck", "api", "live", ["aws:us-east-1"], ["env:prod"]),
        _make_test("def-456", "LoginFlow", "browser", "paused", ["aws:eu-west-1"], ["env:staging"]),
    ]
    mock_client.synthetics.list_tests.return_value = Mock(tests=tests)

    with patch("ddogctl.commands.synthetics.get_datadog_client", return_value=mock_client):
        result = runner.invoke(synthetics, ["list"])

    assert result.exit_code == 0
    assert "Synthetics Tests" in result.output
    assert "abc-123" in result.output
    assert "HealthCheck" in result.output
    assert "def-456" in result.output
    assert "LoginFlow" in result.output
    assert "Total tests: 2" in result.output


def test_list_tests_json(mock_client, runner):
    """Test listing Synthetics tests in JSON format."""
    from ddogctl.commands.synthetics import synthetics

    tests = [
        _make_test("abc-123", "API Health Check", "api", "live", ["aws:us-east-1"], ["env:prod"]),
        _make_test(
            "def-456", "Browser Login Flow", "browser", "paused", ["aws:eu-west-1"], ["env:staging"]
        ),
    ]
    mock_client.synthetics.list_tests.return_value = Mock(tests=tests)

    with patch("ddogctl.commands.synthetics.get_datadog_client", return_value=mock_client):
        result = runner.invoke(synthetics, ["list", "--format", "json"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert len(output) == 2
    assert output[0]["public_id"] == "abc-123"
    assert output[0]["name"] == "API Health Check"
    assert output[0]["type"] == "api"
    assert output[0]["status"] == "live"
    assert output[0]["locations"] == ["aws:us-east-1"]
    assert output[0]["tags"] == ["env:prod"]
    assert output[1]["public_id"] == "def-456"
    assert output[1]["type"] == "browser"
    assert output[1]["status"] == "paused"


def test_list_tests_empty(mock_client, runner):
    """Test listing Synthetics tests when no tests exist."""
    from ddogctl.commands.synthetics import synthetics

    mock_client.synthetics.list_tests.return_value = Mock(tests=[])

    with patch("ddogctl.commands.synthetics.get_datadog_client", return_value=mock_client):
        result = runner.invoke(synthetics, ["list"])

    assert result.exit_code == 0
    assert "Total tests: 0" in result.output


# --- get test ---


def test_get_test_table(mock_client, runner):
    """Test getting a Synthetics test in table format."""
    from ddogctl.commands.synthetics import synthetics

    test = _make_test(
        "abc-123",
        "API Health Check",
        "api",
        "live",
        ["aws:us-east-1", "aws:eu-west-1"],
        ["env:prod", "team:platform"],
        message="Alert: API health check failing",
    )
    mock_client.synthetics.get_test.return_value = test

    with patch("ddogctl.commands.synthetics.get_datadog_client", return_value=mock_client):
        result = runner.invoke(synthetics, ["get", "abc-123"])

    assert result.exit_code == 0
    assert "abc-123" in result.output
    assert "API Health Check" in result.output
    assert "api" in result.output
    assert "live" in result.output
    assert "aws:us-east-1" in result.output
    assert "env:prod" in result.output
    assert "Alert: API health check failing" in result.output


def test_get_test_json(mock_client, runner):
    """Test getting a Synthetics test in JSON format."""
    from ddogctl.commands.synthetics import synthetics

    test = _make_test(
        "abc-123",
        "API Health Check",
        "api",
        "live",
        ["aws:us-east-1"],
        ["env:prod"],
        message="Check is failing",
    )
    mock_client.synthetics.get_test.return_value = test

    with patch("ddogctl.commands.synthetics.get_datadog_client", return_value=mock_client):
        result = runner.invoke(synthetics, ["get", "abc-123", "--format", "json"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["public_id"] == "abc-123"
    assert output["name"] == "API Health Check"
    assert output["type"] == "api"
    assert output["status"] == "live"
    assert output["locations"] == ["aws:us-east-1"]
    assert output["tags"] == ["env:prod"]
    assert output["message"] == "Check is failing"


def test_get_test_not_found(mock_client, runner):
    """Test getting a nonexistent Synthetics test returns error exit code."""
    from ddogctl.commands.synthetics import synthetics
    from datadog_api_client.exceptions import ApiException

    mock_client.synthetics.get_test.side_effect = ApiException(status=404, reason="Not Found")

    with patch("ddogctl.commands.synthetics.get_datadog_client", return_value=mock_client):
        result = runner.invoke(synthetics, ["get", "nonexistent-id"])

    assert result.exit_code != 0


# --- results tests ---


def test_results_table(mock_client, runner):
    """Test getting Synthetics results in table format."""
    from ddogctl.commands.synthetics import synthetics

    results = [
        _make_result("res-001", "0", 1700000000.0, "aws:us-east-1"),
        _make_result("res-002", "1", 1700003600.0, "aws:eu-west-1"),
    ]
    mock_client.synthetics.get_api_test_latest_results.return_value = Mock(results=results)

    with patch("ddogctl.commands.synthetics.get_datadog_client", return_value=mock_client):
        result = runner.invoke(synthetics, ["results", "abc-123"])

    assert result.exit_code == 0
    assert "Latest Results: abc-123" in result.output
    assert "res-001" in result.output
    assert "res-002" in result.output
    assert "Total results: 2" in result.output


def test_results_json(mock_client, runner):
    """Test getting Synthetics results in JSON format."""
    from ddogctl.commands.synthetics import synthetics

    results = [
        _make_result("res-001", "0", 1700000000.0, "aws:us-east-1"),
        _make_result("res-002", "1", 1700003600.0, "aws:eu-west-1"),
    ]
    mock_client.synthetics.get_api_test_latest_results.return_value = Mock(results=results)

    with patch("ddogctl.commands.synthetics.get_datadog_client", return_value=mock_client):
        result = runner.invoke(synthetics, ["results", "abc-123", "--format", "json"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert len(output) == 2
    assert output[0]["result_id"] == "res-001"
    assert output[0]["status"] == "0"
    assert output[0]["check_time"] == 1700000000.0
    assert output[0]["probe_dc"] == "aws:us-east-1"
    assert output[1]["result_id"] == "res-002"
    assert output[1]["status"] == "1"


def test_results_empty(mock_client, runner):
    """Test getting Synthetics results when none exist."""
    from ddogctl.commands.synthetics import synthetics

    mock_client.synthetics.get_api_test_latest_results.return_value = Mock(results=[])

    with patch("ddogctl.commands.synthetics.get_datadog_client", return_value=mock_client):
        result = runner.invoke(synthetics, ["results", "abc-123"])

    assert result.exit_code == 0
    assert "Total results: 0" in result.output


# --- trigger tests ---


def test_trigger_test_table(mock_client, runner):
    """Test triggering a Synthetics test in table format."""
    from ddogctl.commands.synthetics import synthetics

    triggered = [_make_trigger_result("abc-123", "triggered-res-001")]
    mock_response = Mock(results=triggered)
    mock_response.locations = []
    mock_client.synthetics.trigger_tests.return_value = mock_response

    with patch("ddogctl.commands.synthetics.get_datadog_client", return_value=mock_client):
        result = runner.invoke(synthetics, ["trigger", "abc-123"])

    assert result.exit_code == 0
    assert "triggered successfully" in result.output
    assert "abc-123" in result.output
    assert "triggered-res-001" in result.output
    assert "Triggered 1 result(s)" in result.output


def test_trigger_test_json(mock_client, runner):
    """Test triggering a Synthetics test in JSON format."""
    from ddogctl.commands.synthetics import synthetics

    triggered = [_make_trigger_result("abc-123", "triggered-res-001")]
    mock_response = Mock(results=triggered)
    mock_response.locations = []
    mock_client.synthetics.trigger_tests.return_value = mock_response

    with patch("ddogctl.commands.synthetics.get_datadog_client", return_value=mock_client):
        result = runner.invoke(synthetics, ["trigger", "abc-123", "--format", "json"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert len(output["triggered_check_ids"]) == 1
    assert output["triggered_check_ids"][0]["public_id"] == "abc-123"
    assert output["triggered_check_ids"][0]["result_id"] == "triggered-res-001"


def test_trigger_test_calls_api_correctly(mock_client, runner):
    """Test that trigger passes the correct body to the API."""
    from ddogctl.commands.synthetics import synthetics

    triggered = [_make_trigger_result("xyz-789", "res-999")]
    mock_response = Mock(results=triggered)
    mock_response.locations = []
    mock_client.synthetics.trigger_tests.return_value = mock_response

    with patch("ddogctl.commands.synthetics.get_datadog_client", return_value=mock_client):
        result = runner.invoke(synthetics, ["trigger", "xyz-789"])

    assert result.exit_code == 0
    mock_client.synthetics.trigger_tests.assert_called_once()
    call_kwargs = mock_client.synthetics.trigger_tests.call_args
    body = call_kwargs.kwargs["body"]
    assert body.tests[0].public_id == "xyz-789"
