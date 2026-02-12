"""Tests for investigation workflow commands."""

import json
from datetime import datetime
from unittest.mock import Mock, patch


# --- Helper mock classes ---

class MockBucket:
    """Mock bucket for aggregate_spans responses."""
    def __init__(self, value, by=None):
        self.by = by or {}
        self.computes = {"c0": value}


class MockEndpointBucket:
    """Mock bucket with resource_name grouping."""
    def __init__(self, resource_name, value):
        self.by = {"resource_name": resource_name}
        self.computes = {"c0": value}


class MockLog:
    """Simplified mock log for investigation tests."""
    def __init__(self, message):
        self.attributes = Mock(message=message)


# ============================================================
# Latency investigation tests
# ============================================================

def test_investigate_latency_basic(mock_client, runner):
    """Test latency investigation runs full workflow and outputs summary."""
    from ddg.commands.investigate import investigate

    # Step 1: p99 response - 250ms in nanoseconds
    p99_response = Mock(data=Mock(buckets=[MockBucket(250_000_000)]))

    # Step 2: slow endpoints response
    endpoints_response = Mock(data=Mock(buckets=[
        MockEndpointBucket("GET /api/users", 300_000_000),
        MockEndpointBucket("POST /api/orders", 450_000_000),
    ]))

    # Step 3: error logs
    logs_response = Mock(data=[
        MockLog("Connection timeout"),
        MockLog("Database error"),
    ])

    mock_client.spans.aggregate_spans.side_effect = [p99_response, endpoints_response]
    mock_client.logs.list_logs.return_value = logs_response

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['latency', 'my-service', '--format', 'json'])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output['service'] == 'my-service'
        assert output['p99_latency_ms'] == 250.0
        assert len(output['slow_endpoints']) == 2
        assert output['error_count'] == 2


def test_investigate_latency_json_format(mock_client, runner):
    """Test latency investigation produces valid JSON with all required fields."""
    from ddg.commands.investigate import investigate

    p99_response = Mock(data=Mock(buckets=[MockBucket(180_000_000)]))
    endpoints_response = Mock(data=Mock(buckets=[
        MockEndpointBucket("GET /api/health", 100_000_000),
    ]))
    logs_response = Mock(data=[MockLog("Timeout error")])

    mock_client.spans.aggregate_spans.side_effect = [p99_response, endpoints_response]
    mock_client.logs.list_logs.return_value = logs_response

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['latency', 'web-api', '--format', 'json'])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert 'p99_latency_ms' in output
        assert 'slow_endpoints' in output
        assert 'error_count' in output
        assert output['p99_latency_ms'] == 180.0
        assert output['slow_endpoints'][0]['resource_name'] == "GET /api/health"
        assert output['slow_endpoints'][0]['p99_ms'] == 100.0
        assert output['error_count'] == 1


def test_investigate_latency_table_format(mock_client, runner):
    """Test latency investigation renders a rich table with investigation results."""
    from ddg.commands.investigate import investigate

    p99_response = Mock(data=Mock(buckets=[MockBucket(350_000_000)]))
    endpoints_response = Mock(data=Mock(buckets=[
        MockEndpointBucket("GET /api/users", 400_000_000),
    ]))
    logs_response = Mock(data=[MockLog("Error occurred")])

    mock_client.spans.aggregate_spans.side_effect = [p99_response, endpoints_response]
    mock_client.logs.list_logs.return_value = logs_response

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['latency', 'my-service'])

        assert result.exit_code == 0
        assert "my-service" in result.output
        assert "350.00" in result.output
        assert "GET /api/users" in result.output
        assert "400.00" in result.output
        assert "1" in result.output  # error count


def test_investigate_latency_no_issues(mock_client, runner):
    """Test latency investigation for a service with healthy latency and no errors."""
    from ddg.commands.investigate import investigate

    # Low p99 latency
    p99_response = Mock(data=Mock(buckets=[MockBucket(50_000_000)]))  # 50ms
    # No slow endpoints
    endpoints_response = Mock(data=Mock(buckets=[]))
    # No error logs
    logs_response = Mock(data=[])

    mock_client.spans.aggregate_spans.side_effect = [p99_response, endpoints_response]
    mock_client.logs.list_logs.return_value = logs_response

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['latency', 'healthy-service', '--format', 'json'])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output['service'] == 'healthy-service'
        assert output['p99_latency_ms'] == 50.0
        assert len(output['slow_endpoints']) == 0
        assert output['error_count'] == 0


def test_investigate_latency_custom_threshold(mock_client, runner):
    """Test latency investigation respects --threshold option."""
    from ddg.commands.investigate import investigate

    p99_response = Mock(data=Mock(buckets=[MockBucket(800_000_000)]))
    endpoints_response = Mock(data=Mock(buckets=[]))
    logs_response = Mock(data=[])

    mock_client.spans.aggregate_spans.side_effect = [p99_response, endpoints_response]
    mock_client.logs.list_logs.return_value = logs_response

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, [
            'latency', 'my-service', '--threshold', '1000', '--format', 'json'
        ])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output['threshold_ms'] == 1000

        # Verify the threshold was passed to the API call
        calls = mock_client.spans.aggregate_spans.call_args_list
        # First call is p99 query - check filter includes threshold
        first_call_body = calls[0].kwargs['body']
        filter_dict = first_call_body['data']['attributes']['filter']
        assert filter_dict['query'] == 'service:my-service @duration:>1000000000'


# ============================================================
# Errors investigation tests
# ============================================================

def test_investigate_errors_basic(mock_client, runner):
    """Test errors investigation finds errors across traces and logs."""
    from ddg.commands.investigate import investigate

    # Step 1: total error count
    error_count_response = Mock(data=Mock(buckets=[MockBucket(42)]))
    # Step 2: errors by endpoint
    by_endpoint_response = Mock(data=Mock(buckets=[
        MockEndpointBucket("GET /api/users", 25),
        MockEndpointBucket("POST /api/orders", 17),
    ]))
    # Step 3: error logs
    logs_response = Mock(data=[
        MockLog("NullPointerException in UserService"),
        MockLog("Connection refused to database"),
    ])

    mock_client.spans.aggregate_spans.side_effect = [error_count_response, by_endpoint_response]
    mock_client.logs.list_logs.return_value = logs_response

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['errors', 'my-service', '--format', 'json'])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output['service'] == 'my-service'
        assert output['error_count'] == 42
        assert len(output['by_endpoint']) == 2
        assert len(output['recent_logs']) == 2


def test_investigate_errors_json_format(mock_client, runner):
    """Test errors investigation produces valid JSON with all required fields."""
    from ddg.commands.investigate import investigate

    error_count_response = Mock(data=Mock(buckets=[MockBucket(10)]))
    by_endpoint_response = Mock(data=Mock(buckets=[
        MockEndpointBucket("GET /api/health", 10),
    ]))
    logs_response = Mock(data=[MockLog("Service unavailable")])

    mock_client.spans.aggregate_spans.side_effect = [error_count_response, by_endpoint_response]
    mock_client.logs.list_logs.return_value = logs_response

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['errors', 'web-api', '--format', 'json'])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert 'error_count' in output
        assert 'by_endpoint' in output
        assert 'recent_logs' in output
        assert output['by_endpoint'][0]['resource_name'] == "GET /api/health"
        assert output['by_endpoint'][0]['count'] == 10
        assert output['recent_logs'][0] == "Service unavailable"


def test_investigate_errors_table_format(mock_client, runner):
    """Test errors investigation renders a table output."""
    from ddg.commands.investigate import investigate

    error_count_response = Mock(data=Mock(buckets=[MockBucket(5)]))
    by_endpoint_response = Mock(data=Mock(buckets=[
        MockEndpointBucket("GET /api/data", 5),
    ]))
    logs_response = Mock(data=[MockLog("Timeout")])

    mock_client.spans.aggregate_spans.side_effect = [error_count_response, by_endpoint_response]
    mock_client.logs.list_logs.return_value = logs_response

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['errors', 'my-service'])

        assert result.exit_code == 0
        assert "my-service" in result.output
        assert "GET /api/data" in result.output
        assert "5" in result.output
        assert "Timeout" in result.output


def test_investigate_errors_no_errors(mock_client, runner):
    """Test errors investigation for a clean service with no errors."""
    from ddg.commands.investigate import investigate

    error_count_response = Mock(data=Mock(buckets=[MockBucket(0)]))
    by_endpoint_response = Mock(data=Mock(buckets=[]))
    logs_response = Mock(data=[])

    mock_client.spans.aggregate_spans.side_effect = [error_count_response, by_endpoint_response]
    mock_client.logs.list_logs.return_value = logs_response

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['errors', 'clean-service', '--format', 'json'])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output['error_count'] == 0
        assert len(output['by_endpoint']) == 0
        assert len(output['recent_logs']) == 0


def test_investigate_errors_with_time_range(mock_client, runner):
    """Test errors investigation respects --from and --to time range."""
    from ddg.commands.investigate import investigate

    error_count_response = Mock(data=Mock(buckets=[MockBucket(3)]))
    by_endpoint_response = Mock(data=Mock(buckets=[]))
    logs_response = Mock(data=[])

    mock_client.spans.aggregate_spans.side_effect = [error_count_response, by_endpoint_response]
    mock_client.logs.list_logs.return_value = logs_response

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, [
            'errors', 'my-service', '--from', '24h', '--to', 'now'
        ])

        assert result.exit_code == 0
        # Verify time range was passed to API calls
        calls = mock_client.spans.aggregate_spans.call_args_list
        first_call_body = calls[0].kwargs['body']
        # The from/to should be ISO strings derived from 24h ago
        filter_dict = first_call_body['data']['attributes']['filter']
        assert 'from' in filter_dict
        assert 'to' in filter_dict


# ============================================================
# Throughput investigation tests
# ============================================================

def test_investigate_throughput_basic(mock_client, runner):
    """Test throughput investigation shows request counts."""
    from ddg.commands.investigate import investigate

    # Step 1: total request count
    total_response = Mock(data=Mock(buckets=[MockBucket(15000)]))
    # Step 2: requests by endpoint
    by_endpoint_response = Mock(data=Mock(buckets=[
        MockEndpointBucket("GET /api/users", 8000),
        MockEndpointBucket("POST /api/orders", 5000),
        MockEndpointBucket("GET /api/health", 2000),
    ]))

    mock_client.spans.aggregate_spans.side_effect = [total_response, by_endpoint_response]

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['throughput', 'my-service', '--format', 'json'])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output['service'] == 'my-service'
        assert output['total_requests'] == 15000
        assert len(output['by_endpoint']) == 3


def test_investigate_throughput_json_format(mock_client, runner):
    """Test throughput investigation produces valid JSON with total_requests and by_endpoint."""
    from ddg.commands.investigate import investigate

    total_response = Mock(data=Mock(buckets=[MockBucket(500)]))
    by_endpoint_response = Mock(data=Mock(buckets=[
        MockEndpointBucket("GET /api/items", 500),
    ]))

    mock_client.spans.aggregate_spans.side_effect = [total_response, by_endpoint_response]

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['throughput', 'web-api', '--format', 'json'])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert 'total_requests' in output
        assert 'by_endpoint' in output
        assert output['total_requests'] == 500
        assert output['by_endpoint'][0]['resource_name'] == "GET /api/items"
        assert output['by_endpoint'][0]['count'] == 500


def test_investigate_throughput_table_format(mock_client, runner):
    """Test throughput investigation renders table with endpoints and counts."""
    from ddg.commands.investigate import investigate

    total_response = Mock(data=Mock(buckets=[MockBucket(3000)]))
    by_endpoint_response = Mock(data=Mock(buckets=[
        MockEndpointBucket("GET /api/users", 2000),
        MockEndpointBucket("GET /api/health", 1000),
    ]))

    mock_client.spans.aggregate_spans.side_effect = [total_response, by_endpoint_response]

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['throughput', 'my-service'])

        assert result.exit_code == 0
        assert "my-service" in result.output
        assert "3000" in result.output
        assert "GET /api/users" in result.output
        assert "2000" in result.output
        assert "GET /api/health" in result.output
        assert "1000" in result.output


def test_investigate_throughput_no_traffic(mock_client, runner):
    """Test throughput investigation for a service with zero requests."""
    from ddg.commands.investigate import investigate

    total_response = Mock(data=Mock(buckets=[MockBucket(0)]))
    by_endpoint_response = Mock(data=Mock(buckets=[]))

    mock_client.spans.aggregate_spans.side_effect = [total_response, by_endpoint_response]

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['throughput', 'idle-service', '--format', 'json'])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output['total_requests'] == 0
        assert len(output['by_endpoint']) == 0


def test_investigate_throughput_with_time_range(mock_client, runner):
    """Test throughput investigation respects --from time range."""
    from ddg.commands.investigate import investigate

    total_response = Mock(data=Mock(buckets=[MockBucket(100)]))
    by_endpoint_response = Mock(data=Mock(buckets=[]))

    mock_client.spans.aggregate_spans.side_effect = [total_response, by_endpoint_response]

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, [
            'throughput', 'my-service', '--from', '7d'
        ])

        assert result.exit_code == 0
        # Verify time range was passed to API calls
        calls = mock_client.spans.aggregate_spans.call_args_list
        first_call_body = calls[0].kwargs['body']
        filter_dict = first_call_body['data']['attributes']['filter']
        assert 'from' in filter_dict
        assert 'to' in filter_dict


# ============================================================
# Compare investigation tests
# ============================================================

def test_investigate_compare_basic(mock_client, runner):
    """Test compare investigation shows current vs baseline."""
    from ddg.commands.investigate import investigate

    # Current period: count=1000, p99=200ms
    current_count = Mock(data=Mock(buckets=[MockBucket(1000)]))
    current_p99 = Mock(data=Mock(buckets=[MockBucket(200_000_000)]))
    # Baseline period: count=800, p99=180ms
    baseline_count = Mock(data=Mock(buckets=[MockBucket(800)]))
    baseline_p99 = Mock(data=Mock(buckets=[MockBucket(180_000_000)]))

    mock_client.spans.aggregate_spans.side_effect = [
        current_count, current_p99, baseline_count, baseline_p99
    ]

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['compare', 'my-service', '--format', 'json'])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output['service'] == 'my-service'
        assert 'current' in output
        assert 'baseline' in output
        assert output['current']['request_count'] == 1000
        assert output['current']['p99_latency_ms'] == 200.0
        assert output['baseline']['request_count'] == 800
        assert output['baseline']['p99_latency_ms'] == 180.0


def test_investigate_compare_json_format(mock_client, runner):
    """Test compare investigation produces JSON with current, baseline, and delta fields."""
    from ddg.commands.investigate import investigate

    current_count = Mock(data=Mock(buckets=[MockBucket(500)]))
    current_p99 = Mock(data=Mock(buckets=[MockBucket(300_000_000)]))
    baseline_count = Mock(data=Mock(buckets=[MockBucket(400)]))
    baseline_p99 = Mock(data=Mock(buckets=[MockBucket(250_000_000)]))

    mock_client.spans.aggregate_spans.side_effect = [
        current_count, current_p99, baseline_count, baseline_p99
    ]

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['compare', 'web-api', '--format', 'json'])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert 'current' in output
        assert 'baseline' in output
        assert 'delta' in output
        assert output['delta']['request_count_change'] == 100
        assert output['delta']['request_count_pct'] == 25.0
        assert output['delta']['p99_latency_change_ms'] == 50.0
        assert output['delta']['p99_latency_pct'] == 20.0


def test_investigate_compare_table_format(mock_client, runner):
    """Test compare investigation renders table with Current, Baseline, Change columns."""
    from ddg.commands.investigate import investigate

    current_count = Mock(data=Mock(buckets=[MockBucket(1200)]))
    current_p99 = Mock(data=Mock(buckets=[MockBucket(250_000_000)]))
    baseline_count = Mock(data=Mock(buckets=[MockBucket(1000)]))
    baseline_p99 = Mock(data=Mock(buckets=[MockBucket(200_000_000)]))

    mock_client.spans.aggregate_spans.side_effect = [
        current_count, current_p99, baseline_count, baseline_p99
    ]

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['compare', 'my-service'])

        assert result.exit_code == 0
        assert "my-service" in result.output
        assert "Current" in result.output
        assert "Baseline" in result.output
        assert "Change" in result.output


def test_investigate_compare_improvement(mock_client, runner):
    """Test compare investigation shows positive improvement (lower latency, same traffic)."""
    from ddg.commands.investigate import investigate

    # Current: lower latency than baseline
    current_count = Mock(data=Mock(buckets=[MockBucket(1000)]))
    current_p99 = Mock(data=Mock(buckets=[MockBucket(100_000_000)]))  # 100ms
    baseline_count = Mock(data=Mock(buckets=[MockBucket(1000)]))
    baseline_p99 = Mock(data=Mock(buckets=[MockBucket(200_000_000)]))  # 200ms

    mock_client.spans.aggregate_spans.side_effect = [
        current_count, current_p99, baseline_count, baseline_p99
    ]

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['compare', 'my-service', '--format', 'json'])

        assert result.exit_code == 0
        output = json.loads(result.output)
        # Latency decreased - negative change is improvement
        assert output['delta']['p99_latency_change_ms'] == -100.0
        assert output['delta']['p99_latency_pct'] == -50.0


def test_investigate_compare_degradation(mock_client, runner):
    """Test compare investigation shows negative degradation (higher latency)."""
    from ddg.commands.investigate import investigate

    # Current: much higher latency than baseline
    current_count = Mock(data=Mock(buckets=[MockBucket(500)]))
    current_p99 = Mock(data=Mock(buckets=[MockBucket(600_000_000)]))  # 600ms
    baseline_count = Mock(data=Mock(buckets=[MockBucket(1000)]))
    baseline_p99 = Mock(data=Mock(buckets=[MockBucket(200_000_000)]))  # 200ms

    mock_client.spans.aggregate_spans.side_effect = [
        current_count, current_p99, baseline_count, baseline_p99
    ]

    with patch('ddg.commands.investigate.get_datadog_client', return_value=mock_client):
        result = runner.invoke(investigate, ['compare', 'my-service', '--format', 'json'])

        assert result.exit_code == 0
        output = json.loads(result.output)
        # Latency increased significantly
        assert output['delta']['p99_latency_change_ms'] == 400.0
        assert output['delta']['p99_latency_pct'] == 200.0
        # Request count dropped
        assert output['delta']['request_count_change'] == -500
        assert output['delta']['request_count_pct'] == -50.0
