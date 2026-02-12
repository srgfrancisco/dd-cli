"""Tests for Logs commands."""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from tests.conftest import create_mock_log

# Search command tests


def test_logs_search_basic_query(mock_client, runner):
    """Test basic log search returns correct count."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Request received", "web-api", "info", now),
        create_mock_log("Request completed", "web-api", "info", now),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["search", "*", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 2


def test_logs_search_table_format(mock_client, runner):
    """Test search displays table with correct headers and content."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Connection error", "web-api", "error", now),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["search", "*"])

        assert result.exit_code == 0
        assert "Time" in result.output
        assert "Status" in result.output
        assert "Service" in result.output
        assert "Message" in result.output
        assert "Connection error" in result.output
        assert "web-api" in result.output


def test_logs_search_json_format(mock_client, runner):
    """Test search JSON output has expected fields."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Test message", "my-service", "info", now),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["search", "*", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["message"] == "Test message"
        assert output[0]["service"] == "my-service"
        assert output[0]["status"] == "info"
        assert "timestamp" in output[0]


def test_logs_search_with_time_range(mock_client, runner):
    """Test search with --from 24h is accepted."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["search", "*", "--from", "24h"])

        assert result.exit_code == 0
        mock_client.logs.list_logs.assert_called_once()


def test_logs_search_with_service_filter(mock_client, runner):
    """Test search with --service adds service to query."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["search", "*", "--service", "web-api"])

        assert result.exit_code == 0
        call_kwargs = mock_client.logs.list_logs.call_args.kwargs
        body = call_kwargs["body"]
        assert "service:web-api" in body["filter"]["query"]


def test_logs_search_with_status_filter(mock_client, runner):
    """Test search with --status adds status to query."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["search", "*", "--status", "error"])

        assert result.exit_code == 0
        call_kwargs = mock_client.logs.list_logs.call_args.kwargs
        body = call_kwargs["body"]
        assert "status:error" in body["filter"]["query"]


def test_logs_search_empty_results(mock_client, runner):
    """Test search with no results shows total 0."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["search", "nonexistent"])

        assert result.exit_code == 0
        assert "Total logs: 0" in result.output


def test_logs_search_with_limit(mock_client, runner):
    """Test search respects --limit parameter."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["search", "*", "--limit", "10"])

        assert result.exit_code == 0
        call_kwargs = mock_client.logs.list_logs.call_args.kwargs
        body = call_kwargs["body"]
        assert body["page"]["limit"] == 10


# Tail command tests


def test_logs_tail_basic(mock_client, runner):
    """Test tail returns recent logs."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Recent log entry", "web-api", "info", now),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["tail", "*", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["message"] == "Recent log entry"


def test_logs_tail_with_lines(mock_client, runner):
    """Test tail respects --lines parameter."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["tail", "*", "--lines", "25"])

        assert result.exit_code == 0
        call_kwargs = mock_client.logs.list_logs.call_args.kwargs
        body = call_kwargs["body"]
        assert body["page"]["limit"] == 25


def test_logs_tail_with_service_filter(mock_client, runner):
    """Test tail with --service filter works."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["tail", "*", "--service", "web-api"])

        assert result.exit_code == 0
        call_kwargs = mock_client.logs.list_logs.call_args.kwargs
        body = call_kwargs["body"]
        assert "service:web-api" in body["filter"]["query"]


def test_logs_tail_color_coded(mock_client, runner):
    """Test tail output contains log messages."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Error occurred", "web-api", "error", now),
        create_mock_log("Warning issued", "web-api", "warn", now),
        create_mock_log("Info message", "web-api", "info", now),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["tail", "*"])

        assert result.exit_code == 0
        assert "Error occurred" in result.output
        assert "Warning issued" in result.output
        assert "Info message" in result.output


def test_logs_tail_empty(mock_client, runner):
    """Test tail shows 'No logs found' when empty."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["tail", "*"])

        assert result.exit_code == 0
        assert "No logs found" in result.output


# Query command tests


def test_logs_query_count_by_service(mock_client, runner):
    """Test log query with count aggregation grouped by service."""
    from ddg.commands.logs import logs

    class MockBucket:
        def __init__(self, service, count):
            self.by = {"service": service}
            self.computes = {"c0": count}

    mock_buckets = [
        MockBucket("web-api", 1500),
        MockBucket("worker", 800),
    ]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.logs.aggregate_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            logs,
            [
                "query",
                "--query",
                "*",
                "--metric",
                "count",
                "--group-by",
                "service",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 2
        assert output[0]["service"] == "web-api"
        assert output[0]["count"] == 1500
        assert output[1]["service"] == "worker"
        assert output[1]["count"] == 800


def test_logs_query_count_by_status(mock_client, runner):
    """Test log query grouped by status."""
    from ddg.commands.logs import logs

    class MockBucket:
        def __init__(self, status, count):
            self.by = {"status": status}
            self.computes = {"c0": count}

    mock_buckets = [
        MockBucket("error", 250),
        MockBucket("info", 5000),
    ]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.logs.aggregate_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            logs,
            [
                "query",
                "--query",
                "*",
                "--metric",
                "count",
                "--group-by",
                "status",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 2
        assert output[0]["status"] == "error"
        assert output[0]["count"] == 250


def test_logs_query_json_format(mock_client, runner):
    """Test log query JSON output is valid."""
    from ddg.commands.logs import logs

    class MockBucket:
        def __init__(self, service, count):
            self.by = {"service": service}
            self.computes = {"c0": count}

    mock_buckets = [MockBucket("web-api", 100)]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.logs.aggregate_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            logs, ["query", "--metric", "count", "--group-by", "service", "--format", "json"]
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert isinstance(output, list)
        assert len(output) == 1


def test_logs_query_table_format(mock_client, runner):
    """Test log query table has correct columns."""
    from ddg.commands.logs import logs

    class MockBucket:
        def __init__(self, service, count):
            self.by = {"service": service}
            self.computes = {"c0": count}

    mock_buckets = [
        MockBucket("web-api", 1000),
        MockBucket("worker", 500),
    ]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.logs.aggregate_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["query", "--metric", "count", "--group-by", "service"])

        assert result.exit_code == 0
        assert "Log Analytics" in result.output
        assert "service" in result.output
        assert "COUNT" in result.output
        assert "web-api" in result.output
        assert "1000" in result.output
        assert "Total groups: 2" in result.output


def test_logs_query_without_groupby(mock_client, runner):
    """Test log query without group-by returns single aggregate."""
    from ddg.commands.logs import logs

    class MockBucket:
        def __init__(self, count):
            self.by = {}
            self.computes = {"c0": count}

    mock_buckets = [MockBucket(9876)]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.logs.aggregate_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["query", "--metric", "count", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["count"] == 9876


def test_logs_query_empty_results(mock_client, runner):
    """Test log query with no results shows total 0."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=Mock(buckets=[]))
    mock_client.logs.aggregate_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["query", "--metric", "count"])

        assert result.exit_code == 0
        assert "Total groups: 0" in result.output


# Trace command tests


def test_logs_trace_basic(mock_client, runner):
    """Test finding logs for a trace ID."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Request started", "web-api", "info", now, trace_id="abc123"),
        create_mock_log("Request finished", "web-api", "info", now, trace_id="abc123"),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["trace", "abc123", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 2


def test_logs_trace_json_format(mock_client, runner):
    """Test trace logs JSON output."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Trace log", "web-api", "info", now, trace_id="trace-xyz"),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["trace", "trace-xyz", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["message"] == "Trace log"
        assert output[0]["service"] == "web-api"


def test_logs_trace_table_format(mock_client, runner):
    """Test trace logs table output includes trace ID in title."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Trace entry", "web-api", "info", now, trace_id="trace-456"),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["trace", "trace-456"])

        assert result.exit_code == 0
        assert "trace-456" in result.output
        assert "Trace entry" in result.output


def test_logs_trace_not_found(mock_client, runner):
    """Test trace with no matching logs shows 'No logs found'."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch("ddg.commands.logs.get_datadog_client", return_value=mock_client):
        result = runner.invoke(logs, ["trace", "nonexistent-trace"])

        assert result.exit_code == 0
        assert "No logs found" in result.output
