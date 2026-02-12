"""Tests for host commands."""

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from ddg.commands.host import host


class MockHost:
    """Mock Datadog host object."""

    def __init__(
        self,
        name,
        is_up=True,
        apps=None,
        last_reported_time=None,
        host_name=None,
        tags_by_source=None,
    ):
        self.name = name
        self.is_up = is_up
        self.apps = apps or []
        self.last_reported_time = last_reported_time
        self.host_name = host_name or name
        self.tags_by_source = tags_by_source or {}

    def to_dict(self):
        return {
            "name": self.name,
            "is_up": self.is_up,
            "apps": self.apps,
            "last_reported_time": self.last_reported_time,
            "host_name": self.host_name,
            "tags_by_source": self.tags_by_source,
        }


class MockHostListResponse:
    """Mock response for hosts.list_hosts()."""

    def __init__(self, host_list, total_matching):
        self.host_list = host_list
        self.total_matching = total_matching

    def to_dict(self):
        return {
            "host_list": [h.to_dict() for h in self.host_list],
            "total_matching": self.total_matching,
        }


class MockHostTotals:
    """Mock response for hosts.get_host_totals()."""

    def __init__(self, total_active, total_up, total_down=0):
        self.total_active = total_active
        self.total_up = total_up
        self.total_down = total_down


@pytest.fixture
def mock_client():
    """Create a mock Datadog client."""
    client = Mock()
    client.hosts = Mock()
    return client


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


def test_host_list_with_filter(mock_client, runner):
    """Test host list with filter parameter."""
    mock_hosts = [
        MockHost("web-prod-01", is_up=True, apps=["nginx", "app"], last_reported_time=1644000000),
        MockHost("web-prod-02", is_up=True, apps=["nginx", "app"], last_reported_time=1644000100),
    ]
    mock_response = MockHostListResponse(mock_hosts, total_matching=2)
    mock_client.hosts.list_hosts.return_value = mock_response

    with patch("ddg.commands.host.get_datadog_client", return_value=mock_client):
        result = runner.invoke(host, ["list", "--filter", "service:web", "--format", "json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify API was called with filter
        mock_client.hosts.list_hosts.assert_called_once_with(filter="service:web", count=100)

        # Parse JSON output
        import json

        output = json.loads(result.output)

        assert output["total_matching"] == 2
        assert len(output["host_list"]) == 2
        assert output["host_list"][0]["name"] == "web-prod-01"


def test_host_list_no_hosts_found(mock_client, runner):
    """Test host list when no hosts match filter."""
    mock_response = MockHostListResponse([], total_matching=0)
    mock_client.hosts.list_hosts.return_value = mock_response

    with patch("ddg.commands.host.get_datadog_client", return_value=mock_client):
        result = runner.invoke(host, ["list", "--filter", "service:nonexistent"])

        assert result.exit_code == 0
        assert "No hosts found" in result.output


def test_host_list_table_format(mock_client, runner):
    """Test host list with table format (default)."""
    mock_hosts = [
        MockHost(
            "web-prod-01",
            is_up=True,
            apps=["nginx", "app", "monitoring", "extra"],
            last_reported_time=1644000000,
        ),
        MockHost("web-prod-02", is_up=False, apps=["nginx"], last_reported_time=1644001000),
    ]
    mock_response = MockHostListResponse(mock_hosts, total_matching=2)
    mock_client.hosts.list_hosts.return_value = mock_response

    with patch("ddg.commands.host.get_datadog_client", return_value=mock_client):
        result = runner.invoke(host, ["list"])

        assert result.exit_code == 0
        assert "Datadog Hosts" in result.output
        assert "web-prod-01" in result.output
        assert "web-prod-02" in result.output
        assert "UP" in result.output
        assert "DOWN" in result.output
        assert "Total hosts: 2" in result.output
        # Check that apps are truncated with +N (may be wrapped across lines in table)
        assert "+1" in result.output and "more" in result.output


def test_host_list_limit_parameter(mock_client, runner):
    """Test host list respects limit parameter."""
    mock_hosts = [MockHost(f"host-{i}") for i in range(50)]
    mock_response = MockHostListResponse(mock_hosts, total_matching=50)
    mock_client.hosts.list_hosts.return_value = mock_response

    with patch("ddg.commands.host.get_datadog_client", return_value=mock_client):
        result = runner.invoke(host, ["list", "--limit", "25", "--format", "json"])

        assert result.exit_code == 0

        # Verify API was called with correct limit
        mock_client.hosts.list_hosts.assert_called_once_with(count=25)


def test_host_get_found(mock_client, runner):
    """Test getting details for a specific host."""
    mock_host = MockHost(
        "web-prod-01",
        is_up=True,
        apps=["nginx", "app"],
        last_reported_time=1644000000,
        host_name="ip-10-0-1-100.ec2.internal",
        tags_by_source={
            "Datadog": ["env:prod", "service:web", "region:us-west-2"],
            "AWS": ["instance-id:i-1234567890"],
        },
    )
    mock_response = MockHostListResponse([mock_host], total_matching=1)
    mock_client.hosts.list_hosts.return_value = mock_response

    with patch("ddg.commands.host.get_datadog_client", return_value=mock_client):
        result = runner.invoke(host, ["get", "web-prod-01", "--format", "json"])

        assert result.exit_code == 0

        # Verify API was called with host filter
        mock_client.hosts.list_hosts.assert_called_once_with(filter="host:web-prod-01")

        # Parse JSON output
        import json

        output = json.loads(result.output)

        assert output["name"] == "web-prod-01"
        assert output["is_up"] is True
        assert "nginx" in output["apps"]


def test_host_get_not_found(mock_client, runner):
    """Test getting details for a non-existent host."""
    mock_response = MockHostListResponse([], total_matching=0)
    mock_client.hosts.list_hosts.return_value = mock_response

    with patch("ddg.commands.host.get_datadog_client", return_value=mock_client):
        result = runner.invoke(host, ["get", "nonexistent-host"])

        assert result.exit_code == 0
        assert "Host not found: nonexistent-host" in result.output


def test_host_get_table_format(mock_client, runner):
    """Test host get with table format (default)."""
    mock_host = MockHost(
        "web-prod-01",
        is_up=True,
        apps=["nginx", "app"],
        last_reported_time=1644000000,
        host_name="ip-10-0-1-100.ec2.internal",
        tags_by_source={
            "Datadog": [
                "env:prod",
                "service:web",
                "region:us-west-2",
                "extra1",
                "extra2",
                "extra3",
            ],
            "AWS": ["instance-id:i-1234567890"],
        },
    )
    mock_response = MockHostListResponse([mock_host], total_matching=1)
    mock_client.hosts.list_hosts.return_value = mock_response

    with patch("ddg.commands.host.get_datadog_client", return_value=mock_client):
        result = runner.invoke(host, ["get", "web-prod-01"])

        assert result.exit_code == 0
        assert "Host: web-prod-01" in result.output
        assert "Status:" in result.output
        assert "UP" in result.output
        assert "Apps:" in result.output
        assert "nginx" in result.output
        assert "Hostname:" in result.output
        assert "ip-10-0-1-100.ec2.internal" in result.output
        assert "Last Reported:" in result.output
        assert "Tags:" in result.output
        assert "Datadog:" in result.output
        # Should only show first 5 tags
        assert "env:prod" in result.output


def test_host_totals(mock_client, runner):
    """Test host totals command."""
    mock_totals = MockHostTotals(total_active=150, total_up=145, total_down=5)
    mock_client.hosts.get_host_totals.return_value = mock_totals

    with patch("ddg.commands.host.get_datadog_client", return_value=mock_client):
        result = runner.invoke(host, ["totals"])

        assert result.exit_code == 0
        assert "Host Totals" in result.output
        assert "Total Active: 150" in result.output
        assert "Total Up: 145" in result.output
        assert "Total Down: 5" in result.output


def test_host_totals_without_down_attribute(mock_client, runner):
    """Test host totals when total_down attribute is missing."""
    mock_totals = MockHostTotals(total_active=100, total_up=100)
    # Remove total_down to simulate API response without it
    del mock_totals.total_down
    mock_client.hosts.get_host_totals.return_value = mock_totals

    with patch("ddg.commands.host.get_datadog_client", return_value=mock_client):
        result = runner.invoke(host, ["totals"])

        assert result.exit_code == 0
        assert "Total Active: 100" in result.output
        assert "Total Up: 100" in result.output
        # Should not show Total Down if attribute is missing
        assert "Total Down:" not in result.output
