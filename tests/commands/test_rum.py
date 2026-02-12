"""Tests for RUM commands."""

import json
from datetime import datetime
from unittest.mock import Mock, patch
from tests.conftest import create_mock_rum_event

# Events command tests


def test_rum_events_table(mock_client, runner):
    """Test events table output has correct headers and content."""
    from ddogctl.commands.rum import rum

    now = datetime.now()
    mock_events = [
        create_mock_rum_event("evt-001", "view", now, {"url": "/home"}),
        create_mock_rum_event("evt-002", "action", now, {"name": "click"}),
    ]
    mock_response = Mock(data=mock_events)
    mock_client.rum.list_rum_events.return_value = mock_response

    with patch("ddogctl.commands.rum.get_datadog_client", return_value=mock_client):
        result = runner.invoke(rum, ["events"])

        assert result.exit_code == 0
        assert "RUM Events" in result.output
        assert "Time" in result.output
        assert "Type" in result.output
        assert "ID" in result.output
        assert "Total events: 2" in result.output


def test_rum_events_json(mock_client, runner):
    """Test events JSON output has expected fields."""
    from ddogctl.commands.rum import rum

    now = datetime.now()
    mock_events = [
        create_mock_rum_event("evt-001", "view", now, {"url": "/home"}),
    ]
    mock_response = Mock(data=mock_events)
    mock_client.rum.list_rum_events.return_value = mock_response

    with patch("ddogctl.commands.rum.get_datadog_client", return_value=mock_client):
        result = runner.invoke(rum, ["events", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["id"] == "evt-001"
        assert output[0]["type"] == "view"
        assert "timestamp" in output[0]
        assert "attributes" in output[0]


def test_rum_events_empty(mock_client, runner):
    """Test events with no results shows total 0."""
    from ddogctl.commands.rum import rum

    mock_response = Mock(data=[])
    mock_client.rum.list_rum_events.return_value = mock_response

    with patch("ddogctl.commands.rum.get_datadog_client", return_value=mock_client):
        result = runner.invoke(rum, ["events"])

        assert result.exit_code == 0
        assert "Total events: 0" in result.output


def test_rum_events_with_query(mock_client, runner):
    """Test events with --query passes query to API."""
    from ddogctl.commands.rum import rum

    mock_response = Mock(data=[])
    mock_client.rum.list_rum_events.return_value = mock_response

    with patch("ddogctl.commands.rum.get_datadog_client", return_value=mock_client):
        result = runner.invoke(rum, ["events", "--query", "@type:error"])

        assert result.exit_code == 0
        call_kwargs = mock_client.rum.list_rum_events.call_args.kwargs
        assert call_kwargs["filter_query"] == "@type:error"


def test_rum_events_with_time_range(mock_client, runner):
    """Test events with --from 24h is accepted."""
    from ddogctl.commands.rum import rum

    mock_response = Mock(data=[])
    mock_client.rum.list_rum_events.return_value = mock_response

    with patch("ddogctl.commands.rum.get_datadog_client", return_value=mock_client):
        result = runner.invoke(rum, ["events", "--from", "24h"])

        assert result.exit_code == 0
        mock_client.rum.list_rum_events.assert_called_once()


def test_rum_events_with_limit(mock_client, runner):
    """Test events respects --limit parameter."""
    from ddogctl.commands.rum import rum

    mock_response = Mock(data=[])
    mock_client.rum.list_rum_events.return_value = mock_response

    with patch("ddogctl.commands.rum.get_datadog_client", return_value=mock_client):
        result = runner.invoke(rum, ["events", "--limit", "10"])

        assert result.exit_code == 0
        call_kwargs = mock_client.rum.list_rum_events.call_args.kwargs
        assert call_kwargs["page_limit"] == 10


# Analytics command tests


def test_rum_analytics_table(mock_client, runner):
    """Test analytics table output has correct columns."""
    from ddogctl.commands.rum import rum

    class MockBucket:
        def __init__(self, event_type, count):
            self.by = {"@type": event_type}
            self.computes = {"c0": count}

    mock_buckets = [
        MockBucket("view", 1500),
        MockBucket("action", 800),
    ]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.rum.aggregate_rum_events.return_value = mock_response

    with patch("ddogctl.commands.rum.get_datadog_client", return_value=mock_client):
        result = runner.invoke(rum, ["analytics", "--metric", "count", "--group-by", "@type"])

        assert result.exit_code == 0
        assert "RUM Analytics" in result.output
        assert "COUNT" in result.output
        assert "type" in result.output
        assert "view" in result.output
        assert "1500" in result.output
        assert "Total groups: 2" in result.output


def test_rum_analytics_json(mock_client, runner):
    """Test analytics JSON output has expected structure."""
    from ddogctl.commands.rum import rum

    class MockBucket:
        def __init__(self, event_type, count):
            self.by = {"@type": event_type}
            self.computes = {"c0": count}

    mock_buckets = [
        MockBucket("view", 1500),
        MockBucket("action", 800),
    ]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.rum.aggregate_rum_events.return_value = mock_response

    with patch("ddogctl.commands.rum.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            rum,
            ["analytics", "--metric", "count", "--group-by", "@type", "--format", "json"],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 2
        assert output[0]["@type"] == "view"
        assert output[0]["count"] == 1500
        assert output[1]["@type"] == "action"
        assert output[1]["count"] == 800


def test_rum_analytics_p99(mock_client, runner):
    """Test analytics with p99 metric converts ns to ms."""
    from ddogctl.commands.rum import rum

    class MockBucket:
        def __init__(self, url, p99_ns):
            self.by = {"@view.url": url}
            self.computes = {"c0": p99_ns}

    mock_buckets = [
        MockBucket("/home", 2_500_000_000),  # 2500ms
    ]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.rum.aggregate_rum_events.return_value = mock_response

    with patch("ddogctl.commands.rum.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            rum,
            [
                "analytics",
                "--metric",
                "p99",
                "--group-by",
                "@view.url",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["p99"] == 2500.0


def test_rum_analytics_avg(mock_client, runner):
    """Test analytics with avg metric converts ns to ms."""
    from ddogctl.commands.rum import rum

    class MockBucket:
        def __init__(self, country, avg_ns):
            self.by = {"@geo.country": country}
            self.computes = {"c0": avg_ns}

    mock_buckets = [
        MockBucket("US", 500_000_000),  # 500ms
        MockBucket("EU", 800_000_000),  # 800ms
    ]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.rum.aggregate_rum_events.return_value = mock_response

    with patch("ddogctl.commands.rum.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            rum,
            [
                "analytics",
                "--metric",
                "avg",
                "--group-by",
                "@geo.country",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 2
        assert output[0]["avg"] == 500.0
        assert output[1]["avg"] == 800.0


def test_rum_analytics_without_groupby(mock_client, runner):
    """Test analytics without group-by returns single aggregate."""
    from ddogctl.commands.rum import rum

    class MockBucket:
        def __init__(self, count):
            self.by = {}
            self.computes = {"c0": count}

    mock_buckets = [MockBucket(12345)]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.rum.aggregate_rum_events.return_value = mock_response

    with patch("ddogctl.commands.rum.get_datadog_client", return_value=mock_client):
        result = runner.invoke(rum, ["analytics", "--metric", "count", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["count"] == 12345


def test_rum_analytics_empty(mock_client, runner):
    """Test analytics with no results shows total 0."""
    from ddogctl.commands.rum import rum

    mock_response = Mock(data=Mock(buckets=[]))
    mock_client.rum.aggregate_rum_events.return_value = mock_response

    with patch("ddogctl.commands.rum.get_datadog_client", return_value=mock_client):
        result = runner.invoke(rum, ["analytics", "--metric", "count"])

        assert result.exit_code == 0
        assert "Total groups: 0" in result.output
