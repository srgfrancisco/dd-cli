"""Tests for APM commands."""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from tests.conftest import create_mock_service_list, create_mock_span


def test_apm_services_list_json_format(mock_client, runner):
    """Test listing APM services in JSON format."""
    from ddogctl.commands.apm import apm

    mock_services = create_mock_service_list(
        ["web-prod-blue", "web-prod-green", "marketplace-prod"]
    )
    mock_client.service_definitions.list_service_definitions.return_value = mock_services

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(apm, ["services", "--format", "json"])

        assert result.exit_code == 0
        services = json.loads(result.output)
        assert len(services) == 3
        names = [s["name"] for s in services]
        assert "web-prod-blue" in names
        assert "web-prod-green" in names
        assert "marketplace-prod" in names


def test_apm_services_list_table_format(mock_client, runner):
    """Test listing APM services in table format."""
    from ddogctl.commands.apm import apm

    mock_services = create_mock_service_list(["service-a", "service-b"])
    mock_client.service_definitions.list_service_definitions.return_value = mock_services

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(apm, ["services"])
        assert result.exit_code == 0
        assert "APM Services" in result.output
        assert "service-a" in result.output
        assert "service-b" in result.output
        assert "Total services: 2" in result.output


def test_apm_services_empty(mock_client, runner):
    """Test listing APM services when no services exist."""
    from ddogctl.commands.apm import apm

    mock_services = create_mock_service_list([])
    mock_client.service_definitions.list_service_definitions.return_value = mock_services

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(apm, ["services"])
        assert result.exit_code == 0
        assert "Total services: 0" in result.output


def test_apm_services_sorted(mock_client, runner):
    """Test APM services are sorted alphabetically."""
    from ddogctl.commands.apm import apm

    mock_services = create_mock_service_list(["zebra-service", "alpha-service", "beta-service"])
    mock_client.service_definitions.list_service_definitions.return_value = mock_services

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(apm, ["services", "--format", "json"])
        assert result.exit_code == 0
        services = json.loads(result.output)
        names = [s["name"] for s in services]
        assert "zebra-service" in names
        assert "alpha-service" in names
        assert "beta-service" in names

        # Table format should be sorted
        result = runner.invoke(apm, ["services"])
        assert result.exit_code == 0
        # Check that alpha appears before beta in output
        alpha_pos = result.output.find("alpha-service")
        beta_pos = result.output.find("beta-service")
        zebra_pos = result.output.find("zebra-service")
        assert alpha_pos < beta_pos < zebra_pos


def test_apm_services_includes_both_web_fleets(mock_client, runner):
    """Test that both web-prod-blue and web-prod-green are visible."""
    from ddogctl.commands.apm import apm

    mock_services = create_mock_service_list(["web-prod-blue", "web-prod-green", "other-service"])
    mock_client.service_definitions.list_service_definitions.return_value = mock_services

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(apm, ["services", "--format", "json"])
        assert result.exit_code == 0
        services = json.loads(result.output)
        names = [s["name"] for s in services]
        # Both blue and green fleets should be present
        assert "web-prod-blue" in names
        assert "web-prod-green" in names


# Traces command tests


def test_apm_traces_basic_search(mock_client, runner):
    """Test basic trace search with default parameters."""
    from ddogctl.commands.apm import apm

    now = datetime.now()
    start = now - timedelta(seconds=5)

    mock_spans = [
        create_mock_span(
            "span1",
            "web-prod-blue",
            "GET /api/users",
            "trace123",
            start,
            start + timedelta(milliseconds=250),
        )
    ]
    mock_response = Mock(data=mock_spans, meta=Mock(page=Mock(after=None)))
    mock_client.spans.list_spans_get.return_value = mock_response

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(apm, ["traces", "web-prod-blue", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["trace_id"] == "trace123"
        assert output[0]["resource"] == "GET /api/users"
        assert output[0]["service"] == "web-prod-blue"
        assert output[0]["duration_ms"] == 250.0


def test_apm_traces_table_format(mock_client, runner):
    """Test traces display in table format."""
    from ddogctl.commands.apm import apm

    now = datetime.now()
    start = now - timedelta(seconds=5)

    mock_spans = [
        create_mock_span(
            "span1",
            "web-prod-blue",
            "GET /api/users",
            "trace123",
            start,
            start + timedelta(milliseconds=150),
        )
    ]
    mock_response = Mock(data=mock_spans, meta=Mock(page=Mock(after=None)))
    mock_client.spans.list_spans_get.return_value = mock_response

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(apm, ["traces", "web-prod-blue"])
        assert result.exit_code == 0
        assert "Traces for web-prod-blue" in result.output
        assert "trace123" in result.output
        assert "GET /api/users" in result.output
        assert "150.00" in result.output
        assert "Total traces: 1" in result.output


def test_apm_traces_empty_results(mock_client, runner):
    """Test traces command with no results."""
    from ddogctl.commands.apm import apm

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.spans.list_spans_get.return_value = mock_response

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(apm, ["traces", "nonexistent-service"])
        assert result.exit_code == 0
        assert "Total traces: 0" in result.output


def test_apm_traces_duration_conversion(mock_client, runner):
    """Test that nanoseconds are correctly converted to milliseconds."""
    from ddogctl.commands.apm import apm

    now = datetime.now()
    start = now - timedelta(seconds=5)

    # Create span with 500ms duration
    mock_spans = [
        create_mock_span(
            "span1",
            "test-service",
            "GET /test",
            "trace1",
            start,
            start + timedelta(milliseconds=500),
        )
    ]
    mock_response = Mock(data=mock_spans, meta=Mock(page=Mock(after=None)))
    mock_client.spans.list_spans_get.return_value = mock_response

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(apm, ["traces", "test-service", "--format", "json"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        # Duration should be 500ms (500,000,000 ns / 1,000,000 = 500ms)
        assert output[0]["duration_ms"] == 500.0


def test_apm_traces_with_limit(mock_client, runner):
    """Test traces command respects limit parameter."""
    from ddogctl.commands.apm import apm

    now = datetime.now()
    start = now - timedelta(seconds=5)

    mock_spans = [
        create_mock_span(
            f"span{i}",
            "test-service",
            f"GET /endpoint{i}",
            f"trace{i}",
            start,
            start + timedelta(milliseconds=100),
        )
        for i in range(5)
    ]
    mock_response = Mock(data=mock_spans, meta=Mock(page=Mock(after=None)))
    mock_client.spans.list_spans_get.return_value = mock_response

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(apm, ["traces", "test-service", "--limit", "3"])
        # Mock will return all 5, but API would respect limit in real scenario
        # Just verify the command accepts the parameter
        assert result.exit_code == 0
        mock_client.spans.list_spans_get.assert_called_once()
        call_kwargs = mock_client.spans.list_spans_get.call_args.kwargs
        assert call_kwargs["page_limit"] == 3


# Analytics command tests


def test_apm_analytics_count_metric(mock_client, runner):
    """Test analytics with count aggregation."""
    from ddogctl.commands.apm import apm

    class MockBucket:
        def __init__(self, resource, count):
            self.by = {"resource_name": resource}
            self.computes = {"c0": count}

    mock_buckets = [MockBucket("GET /api/users", 1250), MockBucket("POST /api/orders", 890)]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.spans.aggregate_spans.return_value = mock_response

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            apm,
            [
                "analytics",
                "web-prod-blue",
                "--metric",
                "count",
                "--group-by",
                "resource_name",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 2
        assert output[0]["resource_name"] == "GET /api/users"
        assert output[0]["count"] == 1250
        assert output[1]["resource_name"] == "POST /api/orders"
        assert output[1]["count"] == 890


def test_apm_analytics_p99_metric(mock_client, runner):
    """Test analytics with p99 latency aggregation."""
    from ddogctl.commands.apm import apm

    class MockBucket:
        def __init__(self, resource, p99_ns):
            self.by = {"resource_name": resource}
            self.computes = {"c0": p99_ns}

    # P99 values in nanoseconds: 250ms = 250,000,000 ns
    mock_buckets = [
        MockBucket("GET /api/users", 250_000_000),  # 250ms
        MockBucket("POST /api/orders", 500_000_000),  # 500ms
    ]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.spans.aggregate_spans.return_value = mock_response

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            apm,
            [
                "analytics",
                "web-prod-blue",
                "--metric",
                "p99",
                "--group-by",
                "resource_name",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 2
        # P99 values should be converted from ns to ms
        assert output[0]["p99"] == 250.0
        assert output[1]["p99"] == 500.0


def test_apm_analytics_without_groupby(mock_client, runner):
    """Test analytics without group-by (single aggregate value)."""
    from ddogctl.commands.apm import apm

    class MockBucket:
        def __init__(self, count):
            self.by = {}
            self.computes = {"c0": count}

    mock_buckets = [MockBucket(5432)]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.spans.aggregate_spans.return_value = mock_response

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            apm, ["analytics", "web-prod-blue", "--metric", "count", "--format", "json"]
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["count"] == 5432


def test_apm_analytics_table_format(mock_client, runner):
    """Test analytics display in table format."""
    from ddogctl.commands.apm import apm

    class MockBucket:
        def __init__(self, resource, count):
            self.by = {"resource_name": resource}
            self.computes = {"c0": count}

    mock_buckets = [MockBucket("GET /api/users", 1000), MockBucket("POST /api/orders", 500)]
    mock_response = Mock(data=Mock(buckets=mock_buckets))
    mock_client.spans.aggregate_spans.return_value = mock_response

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            apm, ["analytics", "web-prod-blue", "--metric", "count", "--group-by", "resource_name"]
        )

        assert result.exit_code == 0
        # Table title may have line breaks, check components
        assert "Analytics for web-prod-blue" in result.output
        assert "(count)" in result.output
        assert "resource_name" in result.output
        assert "GET /api/users" in result.output
        assert "1000" in result.output
        assert "Total groups: 2" in result.output


def test_apm_analytics_empty_results(mock_client, runner):
    """Test analytics with no results."""
    from ddogctl.commands.apm import apm

    mock_response = Mock(data=Mock(buckets=[]))
    mock_client.spans.aggregate_spans.return_value = mock_response

    with patch("ddogctl.commands.apm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(apm, ["analytics", "nonexistent-service", "--metric", "count"])

        assert result.exit_code == 0
        assert "Total groups: 0" in result.output
