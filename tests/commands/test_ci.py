"""Tests for CI Visibility commands."""

import json
from unittest.mock import Mock, patch


def _create_mock_pipeline_event(event_id, name, status, duration_ns=None, branch=None):
    """Create a mock CI pipeline event."""
    inner_attrs = {
        "name": name,
        "status": status,
    }
    if duration_ns is not None:
        inner_attrs["duration"] = duration_ns
    if branch is not None:
        inner_attrs["git"] = {"branch": branch}

    attrs = Mock()
    attrs.attributes = inner_attrs

    event = Mock()
    event.id = event_id
    event.type = "cipipeline"
    event.attributes = attrs
    return event


def _create_mock_test_event(event_id, name, suite, status, duration_ns=None):
    """Create a mock CI test event."""
    inner_attrs = {
        "name": name,
        "suite": suite,
        "status": status,
    }
    if duration_ns is not None:
        inner_attrs["duration"] = duration_ns

    attrs = Mock()
    attrs.attributes = inner_attrs

    event = Mock()
    event.id = event_id
    event.type = "citest"
    event.attributes = attrs
    return event


# ============================================================================
# Pipelines command tests
# ============================================================================


def test_pipelines_table(mock_client, runner):
    """Test pipelines command displays table with correct headers and data."""
    from ddogctl.commands.ci import ci

    events = [
        _create_mock_pipeline_event(
            "evt-001", "deploy-prod", "success", duration_ns=30_000_000_000, branch="main"
        ),
        _create_mock_pipeline_event(
            "evt-002", "run-tests", "failed", duration_ns=120_000_000_000, branch="feature/x"
        ),
    ]
    mock_response = Mock(data=events)
    mock_client.ci_pipelines.list_ci_app_pipeline_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["pipelines"])

        assert result.exit_code == 0
        assert "CI Pipeline Events" in result.output
        assert "deploy-prod" in result.output
        assert "run-tests" in result.output
        assert "main" in result.output
        assert "Total pipeline events: 2" in result.output


def test_pipelines_json(mock_client, runner):
    """Test pipelines command outputs valid JSON with expected fields."""
    from ddogctl.commands.ci import ci

    events = [
        _create_mock_pipeline_event(
            "evt-100", "build-app", "success", duration_ns=5_000_000_000, branch="main"
        ),
    ]
    mock_response = Mock(data=events)
    mock_client.ci_pipelines.list_ci_app_pipeline_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["pipelines", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["id"] == "evt-100"
        assert output[0]["name"] == "build-app"
        assert output[0]["status"] == "success"
        assert output[0]["duration"] == 5_000_000_000


def test_pipelines_empty(mock_client, runner):
    """Test pipelines command with no results shows total 0."""
    from ddogctl.commands.ci import ci

    mock_response = Mock(data=[])
    mock_client.ci_pipelines.list_ci_app_pipeline_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["pipelines"])

        assert result.exit_code == 0
        assert "Total pipeline events: 0" in result.output


def test_pipelines_with_query(mock_client, runner):
    """Test pipelines command passes query to API."""
    from ddogctl.commands.ci import ci

    mock_response = Mock(data=[])
    mock_client.ci_pipelines.list_ci_app_pipeline_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["pipelines", "--query", "@ci.status:error"])

        assert result.exit_code == 0
        call_kwargs = mock_client.ci_pipelines.list_ci_app_pipeline_events.call_args.kwargs
        assert call_kwargs["filter_query"] == "@ci.status:error"


def test_pipelines_with_limit(mock_client, runner):
    """Test pipelines command passes limit to API."""
    from ddogctl.commands.ci import ci

    mock_response = Mock(data=[])
    mock_client.ci_pipelines.list_ci_app_pipeline_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["pipelines", "--limit", "10"])

        assert result.exit_code == 0
        call_kwargs = mock_client.ci_pipelines.list_ci_app_pipeline_events.call_args.kwargs
        assert call_kwargs["page_limit"] == 10


def test_pipelines_duration_formatting(mock_client, runner):
    """Test that pipeline durations are formatted correctly in table."""
    from ddogctl.commands.ci import ci

    events = [
        # 30 seconds -> should display as "30.0s"
        _create_mock_pipeline_event("evt-1", "fast-job", "success", duration_ns=30_000_000_000),
        # 500 milliseconds -> should display as "500ms"
        _create_mock_pipeline_event("evt-2", "quick-job", "success", duration_ns=500_000_000),
    ]
    mock_response = Mock(data=events)
    mock_client.ci_pipelines.list_ci_app_pipeline_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["pipelines"])

        assert result.exit_code == 0
        assert "30.0s" in result.output
        assert "500ms" in result.output


# ============================================================================
# Tests command tests
# ============================================================================


def test_tests_table(mock_client, runner):
    """Test tests command displays table with correct headers and data."""
    from ddogctl.commands.ci import ci

    events = [
        _create_mock_test_event(
            "test-001", "test_login", "unit-tests", "pass", duration_ns=250_000_000
        ),
        _create_mock_test_event(
            "test-002", "test_checkout", "integration", "fail", duration_ns=1_500_000_000
        ),
    ]
    mock_response = Mock(data=events)
    mock_client.ci_tests.list_ci_app_test_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["tests"])

        assert result.exit_code == 0
        assert "CI Test Events" in result.output
        assert "test_login" in result.output
        assert "test_checkout" in result.output
        assert "unit-tests" in result.output
        assert "integration" in result.output
        assert "Total test events: 2" in result.output


def test_tests_json(mock_client, runner):
    """Test tests command outputs valid JSON with expected fields."""
    from ddogctl.commands.ci import ci

    events = [
        _create_mock_test_event(
            "test-200", "test_signup", "auth-suite", "pass", duration_ns=100_000_000
        ),
    ]
    mock_response = Mock(data=events)
    mock_client.ci_tests.list_ci_app_test_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["tests", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["id"] == "test-200"
        assert output[0]["name"] == "test_signup"
        assert output[0]["suite"] == "auth-suite"
        assert output[0]["status"] == "pass"


def test_tests_with_query(mock_client, runner):
    """Test tests command passes query to API."""
    from ddogctl.commands.ci import ci

    mock_response = Mock(data=[])
    mock_client.ci_tests.list_ci_app_test_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["tests", "--query", "@test.status:fail"])

        assert result.exit_code == 0
        call_kwargs = mock_client.ci_tests.list_ci_app_test_events.call_args.kwargs
        assert call_kwargs["filter_query"] == "@test.status:fail"


def test_tests_empty(mock_client, runner):
    """Test tests command with no results shows total 0."""
    from ddogctl.commands.ci import ci

    mock_response = Mock(data=[])
    mock_client.ci_tests.list_ci_app_test_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["tests"])

        assert result.exit_code == 0
        assert "Total test events: 0" in result.output


def test_tests_with_limit(mock_client, runner):
    """Test tests command passes limit to API."""
    from ddogctl.commands.ci import ci

    mock_response = Mock(data=[])
    mock_client.ci_tests.list_ci_app_test_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["tests", "--limit", "25"])

        assert result.exit_code == 0
        call_kwargs = mock_client.ci_tests.list_ci_app_test_events.call_args.kwargs
        assert call_kwargs["page_limit"] == 25


# ============================================================================
# Pipeline details command tests
# ============================================================================


def test_pipeline_details_table(mock_client, runner):
    """Test pipeline-details command displays table with event details."""
    from ddogctl.commands.ci import ci

    inner_attrs = {
        "name": "deploy-prod",
        "status": "success",
        "duration": 45_000_000_000,
        "level": "pipeline",
    }
    attrs = Mock()
    attrs.attributes = inner_attrs
    event = Mock()
    event.id = "evt-detail-1"
    event.type = "cipipeline"
    event.attributes = attrs

    mock_response = Mock(data=[event])
    mock_client.ci_pipelines.list_ci_app_pipeline_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["pipeline-details", "pipeline-abc-123"])

        assert result.exit_code == 0
        assert "pipeline-abc-123" in result.output
        assert "deploy-prod" in result.output
        assert "pipeline" in result.output
        assert "Total events:" in result.output


def test_pipeline_details_json(mock_client, runner):
    """Test pipeline-details command outputs valid JSON."""
    from ddogctl.commands.ci import ci

    inner_attrs = {
        "name": "build-app",
        "status": "success",
        "duration": 10_000_000_000,
        "level": "pipeline",
    }
    attrs = Mock()
    attrs.attributes = inner_attrs
    event = Mock()
    event.id = "evt-json-1"
    event.type = "cipipeline"
    event.attributes = attrs

    mock_response = Mock(data=[event])
    mock_client.ci_pipelines.list_ci_app_pipeline_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["pipeline-details", "pipe-xyz", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["id"] == "evt-json-1"
        assert output[0]["name"] == "build-app"
        assert output[0]["status"] == "success"


def test_pipeline_details_not_found(mock_client, runner):
    """Test pipeline-details with no matching events shows message."""
    from ddogctl.commands.ci import ci

    mock_response = Mock(data=[])
    mock_client.ci_pipelines.list_ci_app_pipeline_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["pipeline-details", "nonexistent-pipe"])

        assert result.exit_code == 0
        assert "No events found" in result.output


def test_pipeline_details_query_format(mock_client, runner):
    """Test pipeline-details searches with correct query filter."""
    from ddogctl.commands.ci import ci

    mock_response = Mock(data=[])
    mock_client.ci_pipelines.list_ci_app_pipeline_events.return_value = mock_response

    with patch("ddogctl.commands.ci.get_datadog_client", return_value=mock_client):
        result = runner.invoke(ci, ["pipeline-details", "my-pipeline-id"])

        assert result.exit_code == 0
        call_kwargs = mock_client.ci_pipelines.list_ci_app_pipeline_events.call_args.kwargs
        assert "@ci.pipeline.id:my-pipeline-id" in call_kwargs["filter_query"]
