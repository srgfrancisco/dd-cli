"""Tests for DBM (Database Monitoring) commands."""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from click.testing import CliRunner
from rich.console import Console
from tests.conftest import create_mock_dbm_host, create_mock_dbm_query, create_mock_dbm_sample

# ---- hosts command tests ----


def test_dbm_hosts_list_all(mock_client, runner):
    """Test listing all database hosts and verifying count."""
    from ddg.commands.dbm import dbm

    mock_hosts = [
        create_mock_dbm_host("db-prod-01", "postgresql", "15.4", 42, "running"),
        create_mock_dbm_host("db-prod-02", "postgresql", "15.4", 38, "running"),
        create_mock_dbm_host("db-staging-01", "mysql", "8.0", 10, "running"),
    ]
    mock_response = Mock(data=mock_hosts)
    mock_client.dbm.list_hosts.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["hosts", "--format", "json"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 3


def test_dbm_hosts_filter_by_env(mock_client, runner):
    """Test that env filter is passed to the API."""
    from ddg.commands.dbm import dbm

    mock_hosts = [
        create_mock_dbm_host("db-prod-01", "postgresql", "15.4", 42, "running"),
    ]
    mock_response = Mock(data=mock_hosts)
    mock_client.dbm.list_hosts.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["hosts", "--env", "production", "--format", "json"])
        assert result.exit_code == 0
        mock_client.dbm.list_hosts.assert_called_once_with(env="production")


def test_dbm_hosts_json_format(mock_client, runner):
    """Test JSON output contains host, engine, version, connections, status."""
    from ddg.commands.dbm import dbm

    mock_hosts = [
        create_mock_dbm_host("db-prod-01", "postgresql", "15.4", 42, "running"),
    ]
    mock_response = Mock(data=mock_hosts)
    mock_client.dbm.list_hosts.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["hosts", "--format", "json"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        host = output[0]
        assert host["host"] == "db-prod-01"
        assert host["engine"] == "postgresql"
        assert host["version"] == "15.4"
        assert host["connections"] == 42
        assert host["status"] == "running"


def test_dbm_hosts_table_format(mock_client, runner):
    """Test table output contains Host, Engine, Version, Connections, Status columns."""
    from ddg.commands.dbm import dbm

    mock_hosts = [
        create_mock_dbm_host("db-prod-01", "postgresql", "15.4", 42, "running"),
        create_mock_dbm_host("db-prod-02", "mysql", "8.0", 20, "stopped"),
    ]
    mock_response = Mock(data=mock_hosts)
    mock_client.dbm.list_hosts.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["hosts"])
        assert result.exit_code == 0
        assert "Database Hosts" in result.output
        assert "db-prod-01" in result.output
        assert "db-prod-02" in result.output
        assert "postgresql" in result.output
        assert "mysql" in result.output
        assert "15.4" in result.output
        assert "42" in result.output
        assert "running" in result.output
        assert "Total hosts: 2" in result.output


def test_dbm_hosts_empty(mock_client, runner):
    """Test hosts command when no hosts are found."""
    from ddg.commands.dbm import dbm

    mock_response = Mock(data=[])
    mock_client.dbm.list_hosts.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["hosts"])
        assert result.exit_code == 0
        assert "Total hosts: 0" in result.output


# ---- queries command tests ----


def test_dbm_queries_top_by_latency(mock_client, runner):
    """Test queries sorted by average latency (default)."""
    from ddg.commands.dbm import dbm

    mock_queries = [
        create_mock_dbm_query(
            "q1", "SELECT * FROM users", 50.0, 1000, 50000.0, "web-api", "users_db"
        ),
        create_mock_dbm_query(
            "q2", "SELECT * FROM orders", 30.0, 500, 15000.0, "web-api", "orders_db"
        ),
    ]
    mock_response = Mock(data=mock_queries)
    mock_client.dbm.list_queries.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["queries", "--format", "json"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 2
        # Default sort is avg_latency
        call_kwargs = mock_client.dbm.list_queries.call_args.kwargs
        assert call_kwargs["sort_by"] == "avg_latency"


def test_dbm_queries_top_by_calls(mock_client, runner):
    """Test queries sorted by number of calls."""
    from ddg.commands.dbm import dbm

    mock_queries = [
        create_mock_dbm_query(
            "q1", "SELECT * FROM users", 50.0, 1000, 50000.0, "web-api", "users_db"
        ),
    ]
    mock_response = Mock(data=mock_queries)
    mock_client.dbm.list_queries.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["queries", "--sort-by", "calls", "--format", "json"])
        assert result.exit_code == 0
        call_kwargs = mock_client.dbm.list_queries.call_args.kwargs
        assert call_kwargs["sort_by"] == "calls"


def test_dbm_queries_filter_by_service(mock_client, runner):
    """Test queries filtered by service."""
    from ddg.commands.dbm import dbm

    mock_queries = [
        create_mock_dbm_query(
            "q1", "SELECT * FROM users", 50.0, 1000, 50000.0, "web-api", "users_db"
        ),
    ]
    mock_response = Mock(data=mock_queries)
    mock_client.dbm.list_queries.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["queries", "--service", "web-api", "--format", "json"])
        assert result.exit_code == 0
        call_kwargs = mock_client.dbm.list_queries.call_args.kwargs
        assert call_kwargs["service"] == "web-api"


def test_dbm_queries_filter_by_database(mock_client, runner):
    """Test queries filtered by database."""
    from ddg.commands.dbm import dbm

    mock_queries = [
        create_mock_dbm_query(
            "q1", "SELECT * FROM users", 50.0, 1000, 50000.0, "web-api", "users_db"
        ),
    ]
    mock_response = Mock(data=mock_queries)
    mock_client.dbm.list_queries.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["queries", "--database", "users_db", "--format", "json"])
        assert result.exit_code == 0
        call_kwargs = mock_client.dbm.list_queries.call_args.kwargs
        assert call_kwargs["database"] == "users_db"


def test_dbm_queries_json_format(mock_client, runner):
    """Test JSON output contains query_id, normalized_query, avg_latency, calls."""
    from ddg.commands.dbm import dbm

    mock_queries = [
        create_mock_dbm_query(
            "q1", "SELECT * FROM users WHERE id = ?", 25.5, 1200, 30600.0, "web-api", "users_db"
        ),
    ]
    mock_response = Mock(data=mock_queries)
    mock_client.dbm.list_queries.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["queries", "--format", "json"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        q = output[0]
        assert q["query_id"] == "q1"
        assert q["normalized_query"] == "SELECT * FROM users WHERE id = ?"
        assert q["avg_latency_ms"] == 25.5
        assert q["calls"] == 1200
        assert q["total_time_ms"] == 30600.0
        assert q["service"] == "web-api"
        assert q["database"] == "users_db"


def test_dbm_queries_table_format(mock_client, runner):
    """Test table output contains Query ID, Query, Avg Latency (ms), Calls, Total Time columns."""
    from ddg.commands.dbm import dbm

    mock_queries = [
        create_mock_dbm_query(
            "q1", "SELECT * FROM users", 50.0, 1000, 50000.0, "web-api", "users_db"
        ),
        create_mock_dbm_query(
            "q2", "INSERT INTO orders", 10.0, 200, 2000.0, "web-api", "orders_db"
        ),
    ]
    mock_response = Mock(data=mock_queries)
    mock_client.dbm.list_queries.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        with patch("ddg.commands.dbm.console", Console(width=200)):
            result = runner.invoke(dbm, ["queries"])
            assert result.exit_code == 0
            assert "Database Queries" in result.output
            assert "q1" in result.output
            assert "q2" in result.output
            assert "SELECT * FROM users" in result.output
            assert "50.00" in result.output
            assert "1000" in result.output
            assert "Total queries: 2" in result.output


def test_dbm_queries_with_limit(mock_client, runner):
    """Test queries command respects limit parameter."""
    from ddg.commands.dbm import dbm

    mock_queries = [
        create_mock_dbm_query(
            f"q{i}", f"SELECT {i}", float(i), i * 100, float(i * 1000), "svc", "db"
        )
        for i in range(5)
    ]
    mock_response = Mock(data=mock_queries)
    mock_client.dbm.list_queries.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["queries", "--limit", "3"])
        assert result.exit_code == 0
        mock_client.dbm.list_queries.assert_called_once()
        call_kwargs = mock_client.dbm.list_queries.call_args.kwargs
        assert call_kwargs["limit"] == 3


def test_dbm_queries_empty(mock_client, runner):
    """Test queries command when no queries are found."""
    from ddg.commands.dbm import dbm

    mock_response = Mock(data=[])
    mock_client.dbm.list_queries.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["queries"])
        assert result.exit_code == 0
        assert "Total queries: 0" in result.output


# ---- explain command tests ----


def test_dbm_explain_query_plan(mock_client, runner):
    """Test explain command displays execution plan text."""
    from ddg.commands.dbm import dbm

    plan = Mock(
        query_id="q1",
        plan_text="Seq Scan on users  (cost=0.00..35.50 rows=2550 width=4)",
        database="users_db",
        service="web-api",
        cost=35.50,
    )
    mock_response = Mock(data=plan)
    mock_client.dbm.get_query_plan.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["explain", "q1"])
        assert result.exit_code == 0
        assert "Seq Scan on users" in result.output


def test_dbm_explain_json_format(mock_client, runner):
    """Test explain JSON output contains plan details."""
    from ddg.commands.dbm import dbm

    plan = Mock(
        query_id="q1",
        plan_text="Index Scan using idx_users_id on users",
        database="users_db",
        service="web-api",
        cost=5.25,
    )
    mock_response = Mock(data=plan)
    mock_client.dbm.get_query_plan.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["explain", "q1", "--format", "json"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["query_id"] == "q1"
        assert output["plan"] == "Index Scan using idx_users_id on users"
        assert output["database"] == "users_db"
        assert output["service"] == "web-api"
        assert output["cost"] == 5.25


def test_dbm_explain_text_format(mock_client, runner):
    """Test explain text output is formatted properly."""
    from ddg.commands.dbm import dbm

    plan = Mock(
        query_id="q1",
        plan_text="Seq Scan on users\n  Filter: (active = true)\n  Rows: 500",
        database="users_db",
        service="web-api",
        cost=35.50,
    )
    mock_response = Mock(data=plan)
    mock_client.dbm.get_query_plan.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["explain", "q1", "--format", "text"])
        assert result.exit_code == 0
        assert "Query Plan for q1" in result.output
        assert "Seq Scan on users" in result.output
        assert "Filter: (active = true)" in result.output


def test_dbm_explain_with_metadata(mock_client, runner):
    """Test explain shows query metadata (database, service)."""
    from ddg.commands.dbm import dbm

    plan = Mock(
        query_id="q42",
        plan_text="Hash Join",
        database="analytics_db",
        service="analytics-api",
        cost=120.0,
    )
    mock_response = Mock(data=plan)
    mock_client.dbm.get_query_plan.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["explain", "q42"])
        assert result.exit_code == 0
        assert "analytics_db" in result.output
        assert "analytics-api" in result.output


def test_dbm_explain_not_found(mock_client, runner):
    """Test explain handles missing query gracefully."""
    from ddg.commands.dbm import dbm

    mock_response = Mock(data=None)
    mock_client.dbm.get_query_plan.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["explain", "nonexistent-query"])
        assert result.exit_code == 0
        assert "not found" in result.output


# ---- samples command tests ----


def test_dbm_samples_list(mock_client, runner):
    """Test listing sample executions for a query."""
    from ddg.commands.dbm import dbm

    now = datetime.now()
    mock_samples = [
        create_mock_dbm_sample(now - timedelta(minutes=5), 25.0, 10, {"id": 1}),
        create_mock_dbm_sample(now - timedelta(minutes=3), 30.0, 15, {"id": 2}),
        create_mock_dbm_sample(now - timedelta(minutes=1), 20.0, 8, {"id": 3}),
    ]
    mock_response = Mock(data=mock_samples)
    mock_client.dbm.list_query_samples.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["samples", "q1", "--format", "json"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 3


def test_dbm_samples_json_format(mock_client, runner):
    """Test JSON output contains timestamp, duration_ms, rows_affected."""
    from ddg.commands.dbm import dbm

    now = datetime.now()
    mock_samples = [
        create_mock_dbm_sample(now, 45.5, 25, {"user_id": 42}),
    ]
    mock_response = Mock(data=mock_samples)
    mock_client.dbm.list_query_samples.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["samples", "q1", "--format", "json"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        sample = output[0]
        assert "timestamp" in sample
        assert sample["duration_ms"] == 45.5
        assert sample["rows_affected"] == 25
        assert sample["parameters"] == {"user_id": 42}


def test_dbm_samples_table_format(mock_client, runner):
    """Test table output with Time, Duration (ms), Rows Affected, Parameters columns."""
    from ddg.commands.dbm import dbm

    now = datetime.now()
    mock_samples = [
        create_mock_dbm_sample(now, 45.5, 25, {"user_id": 42}),
        create_mock_dbm_sample(now - timedelta(minutes=1), 30.0, 10, {"user_id": 7}),
    ]
    mock_response = Mock(data=mock_samples)
    mock_client.dbm.list_query_samples.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["samples", "q1"])
        assert result.exit_code == 0
        assert "Query Samples for q1" in result.output
        assert "45.50" in result.output
        assert "25" in result.output
        assert "Total samples: 2" in result.output


def test_dbm_samples_with_limit(mock_client, runner):
    """Test samples command respects limit parameter."""
    from ddg.commands.dbm import dbm

    now = datetime.now()
    mock_samples = [
        create_mock_dbm_sample(now - timedelta(minutes=i), 10.0 + i, i, {}) for i in range(5)
    ]
    mock_response = Mock(data=mock_samples)
    mock_client.dbm.list_query_samples.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["samples", "q1", "--limit", "3"])
        assert result.exit_code == 0
        mock_client.dbm.list_query_samples.assert_called_once()
        call_kwargs = mock_client.dbm.list_query_samples.call_args.kwargs
        assert call_kwargs["limit"] == 3


def test_dbm_samples_time_range(mock_client, runner):
    """Test samples command passes time range filters."""
    from ddg.commands.dbm import dbm

    mock_response = Mock(data=[])
    mock_client.dbm.list_query_samples.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["samples", "q1", "--from", "24h", "--to", "now"])
        assert result.exit_code == 0
        mock_client.dbm.list_query_samples.assert_called_once()
        call_kwargs = mock_client.dbm.list_query_samples.call_args.kwargs
        assert "from_ts" in call_kwargs
        assert "to_ts" in call_kwargs
        # from_ts should be roughly 24h ago (less than to_ts)
        assert call_kwargs["from_ts"] < call_kwargs["to_ts"]


def test_dbm_samples_empty(mock_client, runner):
    """Test samples command when no samples are found."""
    from ddg.commands.dbm import dbm

    mock_response = Mock(data=[])
    mock_client.dbm.list_query_samples.return_value = mock_response

    with patch("ddg.commands.dbm.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dbm, ["samples", "q1"])
        assert result.exit_code == 0
        assert "Total samples: 0" in result.output
