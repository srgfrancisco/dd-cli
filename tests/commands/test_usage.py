"""Tests for usage metering commands."""

import json
from datetime import datetime
from unittest.mock import Mock, patch


def test_usage_summary_table(mock_client, runner):
    """Test usage summary in table format."""
    from ddogctl.commands.usage import usage

    mock_response = Mock()
    mock_response.start_date = "2024-01-01"
    mock_response.end_date = "2024-01-07"
    mock_response.apm_host_top99p = 15
    mock_response.infra_host_top99p = 120
    mock_response.container_avg = 350
    mock_response.custom_ts_avg = 5000
    mock_response.logs_indexed_logs_usage_agg_sum = 1200000
    mock_response.ingested_events_bytes_agg_sum = 9500000

    mock_client.usage.get_usage_summary.return_value = mock_response

    with patch("ddogctl.commands.usage.get_datadog_client", return_value=mock_client):
        result = runner.invoke(usage, ["summary", "--from", "2024-01-01", "--to", "2024-01-07"])

    assert result.exit_code == 0
    assert "Usage Summary" in result.output
    assert "APM Hosts" in result.output
    assert "15" in result.output
    assert "120" in result.output
    assert "350" in result.output
    assert "5,000" in result.output


def test_usage_summary_json(mock_client, runner):
    """Test usage summary in JSON format."""
    from ddogctl.commands.usage import usage

    mock_response = Mock()
    mock_response.start_date = "2024-01-01"
    mock_response.end_date = "2024-01-07"
    mock_response.apm_host_top99p = 15
    mock_response.infra_host_top99p = 120
    mock_response.container_avg = 350
    mock_response.custom_ts_avg = 5000
    mock_response.logs_indexed_logs_usage_agg_sum = 1200000
    mock_response.ingested_events_bytes_agg_sum = 9500000

    mock_client.usage.get_usage_summary.return_value = mock_response

    with patch("ddogctl.commands.usage.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            usage, ["summary", "--from", "2024-01-01", "--to", "2024-01-07", "--format", "json"]
        )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["apm_host_top99p"] == 15
    assert data["infra_host_top99p"] == 120
    assert data["container_avg"] == 350
    assert data["custom_ts_avg"] == 5000
    assert data["logs_indexed_logs_usage_agg_sum"] == 1200000
    assert data["ingested_events_bytes_agg_sum"] == 9500000


def test_usage_summary_empty(mock_client, runner):
    """Test usage summary with no data."""
    from ddogctl.commands.usage import usage

    mock_response = Mock(spec=[])

    mock_client.usage.get_usage_summary.return_value = mock_response

    with patch("ddogctl.commands.usage.get_datadog_client", return_value=mock_client):
        result = runner.invoke(usage, ["summary", "--from", "2024-01-01", "--to", "2024-01-07"])

    assert result.exit_code == 0
    assert "No usage data found" in result.output


def test_usage_hosts_table(mock_client, runner):
    """Test host usage in table format."""
    from ddogctl.commands.usage import usage

    entry1 = Mock()
    entry1.hour = datetime(2024, 1, 7, 10, 0, 0)
    entry1.host_count = 120
    entry1.container_count = 350
    entry1.apm_host_count = 15

    entry2 = Mock()
    entry2.hour = datetime(2024, 1, 7, 11, 0, 0)
    entry2.host_count = 122
    entry2.container_count = 355
    entry2.apm_host_count = 15

    mock_response = Mock()
    mock_response.usage = [entry1, entry2]

    mock_client.usage.get_usage_hosts.return_value = mock_response

    with patch("ddogctl.commands.usage.get_datadog_client", return_value=mock_client):
        result = runner.invoke(usage, ["hosts", "--from", "24h", "--to", "now"])

    assert result.exit_code == 0
    assert "Host Usage" in result.output
    assert "120" in result.output
    assert "122" in result.output
    assert "350" in result.output
    assert "Total entries: 2" in result.output


def test_usage_hosts_json(mock_client, runner):
    """Test host usage in JSON format."""
    from ddogctl.commands.usage import usage

    entry1 = Mock()
    entry1.hour = datetime(2024, 1, 7, 10, 0, 0)
    entry1.host_count = 120
    entry1.container_count = 350
    entry1.apm_host_count = 15

    mock_response = Mock()
    mock_response.usage = [entry1]

    mock_client.usage.get_usage_hosts.return_value = mock_response

    with patch("ddogctl.commands.usage.get_datadog_client", return_value=mock_client):
        result = runner.invoke(usage, ["hosts", "--from", "24h", "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["host_count"] == 120
    assert data[0]["container_count"] == 350
    assert data[0]["apm_host_count"] == 15


def test_usage_logs_table(mock_client, runner):
    """Test log usage in table format."""
    from ddogctl.commands.usage import usage

    entry1 = Mock()
    entry1.hour = datetime(2024, 1, 7, 10, 0, 0)
    entry1.ingested_events_count = 500000
    entry1.indexed_events_count = 125000

    entry2 = Mock()
    entry2.hour = datetime(2024, 1, 7, 11, 0, 0)
    entry2.ingested_events_count = 520000
    entry2.indexed_events_count = 130000

    mock_response = Mock()
    mock_response.usage = [entry1, entry2]

    mock_client.usage.get_usage_logs.return_value = mock_response

    with patch("ddogctl.commands.usage.get_datadog_client", return_value=mock_client):
        result = runner.invoke(usage, ["logs", "--from", "24h", "--to", "now"])

    assert result.exit_code == 0
    assert "Log Usage" in result.output
    assert "500000" in result.output
    assert "125000" in result.output
    assert "Total entries: 2" in result.output


def test_usage_logs_json(mock_client, runner):
    """Test log usage in JSON format."""
    from ddogctl.commands.usage import usage

    entry1 = Mock()
    entry1.hour = datetime(2024, 1, 7, 10, 0, 0)
    entry1.ingested_events_count = 500000
    entry1.indexed_events_count = 125000

    mock_response = Mock()
    mock_response.usage = [entry1]

    mock_client.usage.get_usage_logs.return_value = mock_response

    with patch("ddogctl.commands.usage.get_datadog_client", return_value=mock_client):
        result = runner.invoke(usage, ["logs", "--from", "24h", "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["ingested_events_count"] == 500000
    assert data[0]["indexed_events_count"] == 125000


def test_usage_top_avg_metrics_table(mock_client, runner):
    """Test top average metrics in table format."""
    from ddogctl.commands.usage import usage

    entry1 = Mock()
    entry1.metric_name = "system.cpu.user"
    entry1.avg_metric_hour = 42
    entry1.max_metric_hour = 89
    entry1.metric_category = "custom"

    entry2 = Mock()
    entry2.metric_name = "app.request.count"
    entry2.avg_metric_hour = 120
    entry2.max_metric_hour = 250
    entry2.metric_category = "custom"

    mock_response = Mock()
    mock_response.usage = [entry1, entry2]

    mock_client.usage.get_usage_top_avg_metrics.return_value = mock_response

    with patch("ddogctl.commands.usage.get_datadog_client", return_value=mock_client):
        result = runner.invoke(usage, ["top-avg-metrics", "--month", "2024-01"])

    assert result.exit_code == 0
    assert "Top Average Metrics" in result.output
    assert "2024-01" in result.output
    assert "system.cpu.user" in result.output
    assert "app.request.count" in result.output
    assert "42" in result.output
    assert "120" in result.output
    assert "Total metrics: 2" in result.output


def test_usage_top_avg_metrics_json(mock_client, runner):
    """Test top average metrics in JSON format."""
    from ddogctl.commands.usage import usage

    entry1 = Mock()
    entry1.metric_name = "system.cpu.user"
    entry1.avg_metric_hour = 42
    entry1.max_metric_hour = 89
    entry1.metric_category = "custom"

    mock_response = Mock()
    mock_response.usage = [entry1]

    mock_client.usage.get_usage_top_avg_metrics.return_value = mock_response

    with patch("ddogctl.commands.usage.get_datadog_client", return_value=mock_client):
        result = runner.invoke(usage, ["top-avg-metrics", "--month", "2024-01", "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["metric_name"] == "system.cpu.user"
    assert data[0]["avg_metric_hour"] == 42
    assert data[0]["max_metric_hour"] == 89
    assert data[0]["metric_category"] == "custom"


def test_usage_hosts_empty(mock_client, runner):
    """Test host usage with no data."""
    from ddogctl.commands.usage import usage

    mock_response = Mock()
    mock_response.usage = []

    mock_client.usage.get_usage_hosts.return_value = mock_response

    with patch("ddogctl.commands.usage.get_datadog_client", return_value=mock_client):
        result = runner.invoke(usage, ["hosts", "--from", "24h"])

    assert result.exit_code == 0
    assert "Total entries: 0" in result.output


def test_usage_logs_empty(mock_client, runner):
    """Test log usage with no data."""
    from ddogctl.commands.usage import usage

    mock_response = Mock()
    mock_response.usage = []

    mock_client.usage.get_usage_logs.return_value = mock_response

    with patch("ddogctl.commands.usage.get_datadog_client", return_value=mock_client):
        result = runner.invoke(usage, ["logs", "--from", "24h"])

    assert result.exit_code == 0
    assert "Total entries: 0" in result.output


def test_usage_top_avg_metrics_default_month(mock_client, runner):
    """Test top average metrics defaults to current month."""
    from ddogctl.commands.usage import usage

    mock_response = Mock()
    mock_response.usage = []

    mock_client.usage.get_usage_top_avg_metrics.return_value = mock_response

    with patch("ddogctl.commands.usage.get_datadog_client", return_value=mock_client):
        result = runner.invoke(usage, ["top-avg-metrics"])

    assert result.exit_code == 0
    assert "Total metrics: 0" in result.output

    # Verify the month parameter was set to the first of the current month
    call_kwargs = mock_client.usage.get_usage_top_avg_metrics.call_args.kwargs
    now = datetime.now()
    assert call_kwargs["month"].year == now.year
    assert call_kwargs["month"].month == now.month
    assert call_kwargs["month"].day == 1


def test_usage_summary_relative_dates(mock_client, runner):
    """Test summary command with relative date format (e.g., 30d)."""
    from ddogctl.commands.usage import usage

    mock_response = Mock()
    mock_response.apm_host_top99p = 10
    mock_response.infra_host_top99p = 50
    mock_response.container_avg = None
    mock_response.custom_ts_avg = None
    mock_response.logs_indexed_logs_usage_agg_sum = None
    mock_response.ingested_events_bytes_agg_sum = None

    mock_client.usage.get_usage_summary.return_value = mock_response

    with patch("ddogctl.commands.usage.get_datadog_client", return_value=mock_client):
        result = runner.invoke(usage, ["summary", "--from", "30d"])

    assert result.exit_code == 0
    assert "Usage Summary" in result.output
    assert "10" in result.output
    assert "50" in result.output
