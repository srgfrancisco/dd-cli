"""Tests for monitor commands."""

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from datadog_api_client.v1.model.monitor_overall_states import MonitorOverallStates
from ddogctl.commands.monitor import monitor


class MockMonitor:
    """Mock Datadog monitor object."""

    def __init__(self, id, name, overall_state, tags=None):
        self.id = id
        self.name = name
        self.overall_state = overall_state
        self.tags = tags or []
        self.type = "metric alert"
        self.query = "avg:system.cpu.user{*}"
        self.message = "Test monitor"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "overall_state": str(self.overall_state),
            "type": self.type,
            "query": self.query,
            "message": self.message,
            "tags": self.tags,
        }


@pytest.fixture
def mock_client():
    """Create a mock Datadog client."""
    client = Mock()
    client.monitors = Mock()
    return client


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


def test_monitor_list_state_filter(mock_client, runner):
    """Test that monitor list correctly filters by state.

    This test verifies the fix for the bug where state filtering always returned 0 monitors
    because m.overall_state (enum) was compared directly to strings instead of str(m.overall_state).
    """
    # Create monitors with different states
    mock_monitors = [
        MockMonitor(1, "Alert Monitor", MonitorOverallStates.ALERT, tags=["env:prod"]),
        MockMonitor(2, "Warn Monitor", MonitorOverallStates.WARN, tags=["env:staging"]),
        MockMonitor(3, "OK Monitor", MonitorOverallStates.OK, tags=["env:dev"]),
        MockMonitor(4, "Another Alert", MonitorOverallStates.ALERT, tags=["env:prod"]),
    ]

    # Mock the API response
    mock_client.monitors.list_monitors.return_value = mock_monitors

    # Patch get_datadog_client to return our mock
    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        # Test filtering by Alert state only
        result = runner.invoke(monitor, ["list", "--state", "Alert", "--format", "json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Parse JSON output
        import json

        output = json.loads(result.output)

        # Should only return Alert monitors (IDs 1 and 4)
        assert len(output) == 2, f"Expected 2 Alert monitors, got {len(output)}"
        assert output[0]["id"] == 1
        assert output[1]["id"] == 4

        # Test filtering by multiple states (Alert and Warn)
        result = runner.invoke(
            monitor, ["list", "--state", "Alert", "--state", "Warn", "--format", "json"]
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)

        # Should return Alert and Warn monitors (IDs 1, 2, 4)
        assert len(output) == 3, f"Expected 3 Alert/Warn monitors, got {len(output)}"
        monitor_ids = [m["id"] for m in output]
        assert sorted(monitor_ids) == [1, 2, 4]

        # Verify OK monitor (ID 3) was filtered out
        assert 3 not in monitor_ids, "OK monitor should be filtered out"


def test_monitor_list_no_state_filter(mock_client, runner):
    """Test that monitor list without state filter returns all monitors."""
    mock_monitors = [
        MockMonitor(1, "Alert Monitor", MonitorOverallStates.ALERT),
        MockMonitor(2, "OK Monitor", MonitorOverallStates.OK),
    ]

    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["list", "--format", "json"])

        assert result.exit_code == 0

        import json

        output = json.loads(result.output)

        # Should return all monitors
        assert len(output) == 2


# ============================================================================
# Output Format Tests
# ============================================================================


def test_monitor_list_table_format(mock_client, runner):
    """Test monitor list with table format (default)."""
    mock_monitors = [
        MockMonitor(
            1, "Test Monitor", MonitorOverallStates.ALERT, tags=["env:prod", "service:web"]
        ),
    ]

    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["list", "--format", "table"])

        assert result.exit_code == 0
        assert "Datadog Monitors" in result.output
        assert "Test Monitor" in result.output
        assert "Total monitors: 1" in result.output


def test_monitor_list_markdown_format(mock_client, runner):
    """Test monitor list with markdown format."""
    mock_monitors = [
        MockMonitor(1, "Test Monitor", MonitorOverallStates.ALERT),
        MockMonitor(2, "Another Monitor", MonitorOverallStates.OK),
    ]

    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["list", "--format", "markdown"])

        assert result.exit_code == 0
        # Check markdown table structure
        assert "| ID | State | Name |" in result.output
        assert "|---|---|---|" in result.output
        assert "| 1 |" in result.output
        assert "| 2 |" in result.output
        assert "Test Monitor" in result.output


def test_monitor_list_json_format(mock_client, runner):
    """Test monitor list with JSON format."""
    mock_monitors = [
        MockMonitor(1, "Test Monitor", MonitorOverallStates.ALERT, tags=["env:prod"]),
    ]

    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["list", "--format", "json"])

        assert result.exit_code == 0

        import json

        output = json.loads(result.output)

        assert len(output) == 1
        assert output[0]["id"] == 1
        assert output[0]["name"] == "Test Monitor"
        assert output[0]["tags"] == ["env:prod"]


# ============================================================================
# Monitor Get Command Tests
# ============================================================================


def test_monitor_get_table_format(mock_client, runner):
    """Test getting a single monitor with table format."""
    mock_monitor = MockMonitor(
        123, "CPU Alert Monitor", MonitorOverallStates.ALERT, tags=["env:prod", "service:web"]
    )
    mock_monitor.created = "2024-01-01T00:00:00Z"
    mock_monitor.modified = "2024-01-02T00:00:00Z"

    mock_client.monitors.get_monitor.return_value = mock_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["get", "123", "--format", "table"])

        assert result.exit_code == 0
        assert "Monitor #123" in result.output
        assert "CPU Alert Monitor" in result.output
        assert "metric alert" in result.output
        assert "avg:system.cpu.user{*}" in result.output
        assert "env:prod" in result.output
        assert "service:web" in result.output


def test_monitor_get_json_format(mock_client, runner):
    """Test getting a single monitor with JSON format."""
    mock_monitor = MockMonitor(456, "Memory Monitor", MonitorOverallStates.OK, tags=["env:staging"])

    mock_client.monitors.get_monitor.return_value = mock_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["get", "456", "--format", "json"])

        assert result.exit_code == 0

        import json

        output = json.loads(result.output)

        assert output["id"] == 456
        assert output["name"] == "Memory Monitor"
        assert output["type"] == "metric alert"
        assert output["tags"] == ["env:staging"]


def test_monitor_get_without_optional_fields(mock_client, runner):
    """Test getting a monitor that has no created/modified timestamps."""
    mock_monitor = MockMonitor(789, "Simple Monitor", MonitorOverallStates.WARN)

    mock_client.monitors.get_monitor.return_value = mock_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["get", "789"])

        assert result.exit_code == 0
        assert "Simple Monitor" in result.output


# ============================================================================
# Monitor Mute Command Tests
# ============================================================================


def test_monitor_mute_basic(mock_client, runner):
    """Test muting a monitor without additional options."""
    mock_client.monitors.update_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["mute", "123"])

        assert result.exit_code == 0
        assert "Monitor 123 muted" in result.output
        mock_client.monitors.update_monitor.assert_called_once()


def test_monitor_mute_with_duration(mock_client, runner):
    """Test muting a monitor with a duration."""
    mock_client.monitors.update_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["mute", "123", "--duration", "3600"])

        assert result.exit_code == 0
        assert "Monitor 123 muted" in result.output
        assert "Muted for 3600 seconds" in result.output
        mock_client.monitors.update_monitor.assert_called_once()


def test_monitor_mute_with_scope(mock_client, runner):
    """Test muting a monitor with a specific scope."""
    mock_client.monitors.update_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["mute", "456", "--scope", "host:myhost"])

        assert result.exit_code == 0
        assert "Monitor 456 muted" in result.output
        mock_client.monitors.update_monitor.assert_called_once()


def test_monitor_mute_with_duration_and_scope(mock_client, runner):
    """Test muting a monitor with both duration and scope."""
    mock_client.monitors.update_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            monitor, ["mute", "789", "--duration", "1800", "--scope", "env:prod"]
        )

        assert result.exit_code == 0
        assert "Monitor 789 muted" in result.output
        assert "Muted for 1800 seconds" in result.output
        mock_client.monitors.update_monitor.assert_called_once()


# ============================================================================
# Monitor Unmute Command Tests
# ============================================================================


def test_monitor_unmute_basic(mock_client, runner):
    """Test unmuting a monitor without additional options."""
    mock_client.monitors.update_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["unmute", "123"])

        assert result.exit_code == 0
        assert "Monitor 123 unmuted" in result.output
        mock_client.monitors.update_monitor.assert_called_once()


def test_monitor_unmute_with_scope(mock_client, runner):
    """Test unmuting a monitor with a specific scope."""
    mock_client.monitors.update_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["unmute", "456", "--scope", "host:myhost"])

        assert result.exit_code == 0
        assert "Monitor 456 unmuted" in result.output
        mock_client.monitors.update_monitor.assert_called_once()


# ============================================================================
# Monitor Validate Command Tests
# ============================================================================


class MockValidationResult:
    """Mock validation result object."""

    def __init__(self, has_errors=False):
        if has_errors:
            self.errors = ["Invalid query syntax", "Missing required field"]
        else:
            self.errors = None


def test_monitor_validate_valid_definition(mock_client, runner):
    """Test validating a valid monitor definition."""
    mock_client.monitors.validate_monitor.return_value = MockValidationResult(has_errors=False)

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            monitor,
            ["validate", "--type", "metric alert", "--query", "avg:system.cpu.user{*} > 80"],
        )

        assert result.exit_code == 0
        assert "Monitor definition is valid" in result.output
        mock_client.monitors.validate_monitor.assert_called_once()


def test_monitor_validate_invalid_definition(mock_client, runner):
    """Test validating an invalid monitor definition."""
    mock_client.monitors.validate_monitor.return_value = MockValidationResult(has_errors=True)

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            monitor, ["validate", "--type", "metric alert", "--query", "invalid query syntax"]
        )

        assert result.exit_code == 1  # Should exit with error code
        assert "Monitor definition is invalid" in result.output
        assert "Invalid query syntax" in result.output
        assert "Missing required field" in result.output


def test_monitor_validate_missing_required_args(mock_client, runner):
    """Test validate command without required arguments."""
    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        # Missing --query
        result = runner.invoke(monitor, ["validate", "--type", "metric alert"])
        assert result.exit_code != 0

        # Missing --type
        result = runner.invoke(monitor, ["validate", "--query", "avg:system.cpu{*}"])
        assert result.exit_code != 0


# ============================================================================
# Integration Tests (Multiple Commands)
# ============================================================================


def test_monitor_workflow_list_get(mock_client, runner):
    """Test workflow: list monitors, then get details of one."""
    # Setup for list
    mock_monitors = [
        MockMonitor(1, "Monitor A", MonitorOverallStates.ALERT),
        MockMonitor(2, "Monitor B", MonitorOverallStates.OK),
    ]
    mock_client.monitors.list_monitors.return_value = mock_monitors

    # Setup for get
    mock_single = MockMonitor(1, "Monitor A", MonitorOverallStates.ALERT)
    mock_client.monitors.get_monitor.return_value = mock_single

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        # First list all monitors
        result = runner.invoke(monitor, ["list", "--format", "json"])
        assert result.exit_code == 0

        import json

        monitors_list = json.loads(result.output)
        assert len(monitors_list) == 2

        # Then get details of the first one
        result = runner.invoke(monitor, ["get", "1", "--format", "json"])
        assert result.exit_code == 0

        monitor_details = json.loads(result.output)
        assert monitor_details["id"] == 1
        assert monitor_details["name"] == "Monitor A"
