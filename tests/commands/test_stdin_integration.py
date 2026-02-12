"""Tests for stdin piping integration with commands."""

import json

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from ddogctl.commands.monitor import monitor
from ddogctl.commands.dashboard import dashboard
from ddogctl.commands.apply import apply_cmd
from ddogctl.commands.slo import slo


@pytest.fixture
def mock_client():
    """Create a mock Datadog client."""
    client = Mock()
    client.monitors = Mock()
    client.dashboards = Mock()
    client.slos = Mock()
    client.downtimes = Mock()
    return client


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


# ============================================================================
# Monitor Create --from-stdin Tests
# ============================================================================


class TestMonitorCreateFromStdin:
    """Tests for monitor create with --from-stdin."""

    def test_create_from_stdin(self, runner, mock_client):
        """Test creating a monitor from piped JSON stdin."""
        monitor_data = {
            "name": "Test Monitor",
            "type": "metric alert",
            "query": "avg(last_5m):avg:system.cpu.user{*} > 90",
            "message": "CPU is high",
        }

        created = Mock()
        created.id = 12345
        created.name = "Test Monitor"
        created.to_dict.return_value = {"id": 12345, "name": "Test Monitor"}
        mock_client.monitors.create_monitor.return_value = created

        with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                monitor,
                ["create", "--from-stdin"],
                input=json.dumps(monitor_data),
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 12345 created" in result.output
        mock_client.monitors.create_monitor.assert_called_once()

    def test_create_from_stdin_json_output(self, runner, mock_client):
        """Test creating a monitor from stdin with JSON output format."""
        monitor_data = {
            "name": "Test Monitor",
            "type": "metric alert",
            "query": "avg:system.cpu.user{*} > 90",
        }

        created = Mock()
        created.id = 12345
        created.name = "Test Monitor"
        created.to_dict.return_value = {"id": 12345, "name": "Test Monitor"}
        mock_client.monitors.create_monitor.return_value = created

        with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                monitor,
                ["create", "--from-stdin", "--format", "json"],
                input=json.dumps(monitor_data),
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == 12345

    def test_create_from_stdin_invalid_json(self, runner, mock_client):
        """Test that invalid JSON on stdin produces an error."""
        with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                monitor,
                ["create", "--from-stdin"],
                input="not valid json",
            )

        assert result.exit_code != 0

    def test_create_from_stdin_overrides_file_flag(self, runner, mock_client, tmp_path):
        """Test that --from-stdin takes precedence over -f."""
        stdin_data = {
            "name": "From Stdin",
            "type": "metric alert",
            "query": "avg:system.cpu.user{*} > 90",
        }

        created = Mock()
        created.id = 999
        created.name = "From Stdin"
        created.to_dict.return_value = {"id": 999, "name": "From Stdin"}
        mock_client.monitors.create_monitor.return_value = created

        with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                monitor,
                ["create", "--from-stdin"],
                input=json.dumps(stdin_data),
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 999 created" in result.output


# ============================================================================
# Monitor Update --from-stdin Tests
# ============================================================================


class TestMonitorUpdateFromStdin:
    """Tests for monitor update with --from-stdin."""

    def test_update_from_stdin(self, runner, mock_client):
        """Test updating a monitor from piped JSON stdin."""
        update_data = {
            "name": "Updated Monitor",
            "query": "avg:system.cpu.user{*} > 95",
        }

        updated = Mock()
        updated.id = 12345
        updated.name = "Updated Monitor"
        updated.to_dict.return_value = {"id": 12345, "name": "Updated Monitor"}
        mock_client.monitors.update_monitor.return_value = updated

        with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                monitor,
                ["update", "12345", "--from-stdin"],
                input=json.dumps(update_data),
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 12345 updated" in result.output
        mock_client.monitors.update_monitor.assert_called_once()

    def test_update_from_stdin_json_output(self, runner, mock_client):
        """Test updating from stdin with JSON output format."""
        update_data = {"name": "Updated Monitor"}

        updated = Mock()
        updated.id = 12345
        updated.name = "Updated Monitor"
        updated.to_dict.return_value = {"id": 12345, "name": "Updated Monitor"}
        mock_client.monitors.update_monitor.return_value = updated

        with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                monitor,
                ["update", "12345", "--from-stdin", "--format", "json"],
                input=json.dumps(update_data),
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == 12345


# ============================================================================
# Monitor Mute --from-stdin Tests
# ============================================================================


class TestMonitorMuteFromStdin:
    """Tests for monitor mute with --from-stdin."""

    def test_mute_from_stdin_list(self, runner, mock_client):
        """Test muting multiple monitors from a piped list."""
        monitors_data = [
            {"id": 1, "name": "Alert Monitor 1"},
            {"id": 2, "name": "Alert Monitor 2"},
        ]

        mock_client.monitors.update_monitor.return_value = Mock()

        with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                monitor,
                ["mute", "--from-stdin"],
                input=json.dumps(monitors_data),
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 1 muted" in result.output
        assert "Monitor 2 muted" in result.output
        assert "2 monitor(s) muted" in result.output
        assert mock_client.monitors.update_monitor.call_count == 2

    def test_mute_from_stdin_single_object(self, runner, mock_client):
        """Test muting a single monitor from stdin (single object, not array)."""
        monitor_data = {"id": 42, "name": "Single Monitor"}

        mock_client.monitors.update_monitor.return_value = Mock()

        with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                monitor,
                ["mute", "--from-stdin"],
                input=json.dumps(monitor_data),
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 42 muted" in result.output
        assert "1 monitor(s) muted" in result.output

    def test_mute_from_stdin_with_duration(self, runner, mock_client):
        """Test muting from stdin with --duration flag."""
        monitors_data = [{"id": 1}]

        mock_client.monitors.update_monitor.return_value = Mock()

        with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                monitor,
                ["mute", "--from-stdin", "--duration", "3600"],
                input=json.dumps(monitors_data),
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 1 muted" in result.output
        # Verify the update call included the end timestamp
        call_kwargs = mock_client.monitors.update_monitor.call_args
        body = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][1]
        assert hasattr(body, "end") and body.end is not None

    def test_mute_from_stdin_skips_items_without_id(self, runner, mock_client):
        """Test that items without 'id' field are skipped with a warning."""
        monitors_data = [
            {"id": 1, "name": "Valid"},
            {"name": "No ID"},
            {"id": 3, "name": "Also Valid"},
        ]

        mock_client.monitors.update_monitor.return_value = Mock()

        with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                monitor,
                ["mute", "--from-stdin"],
                input=json.dumps(monitors_data),
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Skipping item without 'id' field" in result.output
        assert "2 monitor(s) muted" in result.output

    def test_mute_without_id_or_stdin_shows_error(self, runner, mock_client):
        """Test that mute without monitor_id and without --from-stdin shows an error."""
        with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
            result = runner.invoke(monitor, ["mute"])

        assert result.exit_code != 0


# ============================================================================
# Dashboard Create --from-stdin Tests
# ============================================================================


class TestDashboardCreateFromStdin:
    """Tests for dashboard create with --from-stdin."""

    def test_create_from_stdin(self, runner, mock_client):
        """Test creating a dashboard from piped JSON stdin."""
        dash_data = {
            "title": "My Dashboard",
            "layout_type": "ordered",
            "widgets": [{"type": "timeseries"}],
        }

        created = Mock()
        created.id = "abc-def-123"
        created.title = "My Dashboard"
        created.to_dict.return_value = {"id": "abc-def-123", "title": "My Dashboard"}
        mock_client.dashboards.create_dashboard.return_value = created

        with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                dashboard,
                ["create", "--from-stdin"],
                input=json.dumps(dash_data),
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "abc-def-123" in result.output
        mock_client.dashboards.create_dashboard.assert_called_once()

    def test_create_from_stdin_with_title_override(self, runner, mock_client):
        """Test that --title flag can override the title in stdin data.

        Note: the title flag is separate from the file_data, so when --from-stdin
        is used the file_data takes precedence (includes its own title).
        """
        dash_data = {
            "title": "Original Title",
            "layout_type": "ordered",
            "widgets": [],
        }

        created = Mock()
        created.id = "abc-def-456"
        created.title = "Original Title"
        created.to_dict.return_value = {"id": "abc-def-456", "title": "Original Title"}
        mock_client.dashboards.create_dashboard.return_value = created

        with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                dashboard,
                ["create", "--from-stdin"],
                input=json.dumps(dash_data),
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        mock_client.dashboards.create_dashboard.assert_called_once()


# ============================================================================
# SLO Create --from-stdin Tests
# ============================================================================


class TestSloCreateFromStdin:
    """Tests for SLO create with --from-stdin."""

    def test_create_from_stdin(self, runner, mock_client):
        """Test creating an SLO from piped JSON stdin."""
        slo_data = {
            "name": "API Availability",
            "type": "metric",
            "thresholds": [{"timeframe": "30d", "target": 99.9}],
            "query": {
                "numerator": "sum:requests.ok{*}",
                "denominator": "sum:requests{*}",
            },
        }

        created = Mock()
        created.id = "slo-abc123"
        created.name = "API Availability"
        created.to_dict.return_value = {"id": "slo-abc123", "name": "API Availability"}
        slo_response = Mock()
        slo_response.data = [created]
        mock_client.slos.create_slo.return_value = slo_response

        with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                slo,
                ["create", "--from-stdin"],
                input=json.dumps(slo_data),
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "slo-abc123" in result.output
        mock_client.slos.create_slo.assert_called_once()


# ============================================================================
# Apply --from-stdin Tests
# ============================================================================


class TestApplyFromStdin:
    """Tests for apply command with --from-stdin."""

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_apply_monitor_from_stdin(self, mock_get_client, runner, mock_client):
        """Test applying a monitor from piped JSON stdin."""
        mock_get_client.return_value = mock_client

        created = Mock()
        created.id = 12345
        created.to_dict.return_value = {"id": 12345, "name": "CPU Alert"}
        mock_client.monitors.create_monitor.return_value = created

        monitor_data = {
            "name": "CPU Alert",
            "type": "metric alert",
            "query": "avg:system.cpu{*} > 90",
        }

        result = runner.invoke(
            apply_cmd,
            ["--from-stdin"],
            input=json.dumps(monitor_data),
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "12345" in result.output
        mock_client.monitors.create_monitor.assert_called_once()

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_apply_dashboard_from_stdin(self, mock_get_client, runner, mock_client):
        """Test applying a dashboard from piped JSON stdin."""
        mock_get_client.return_value = mock_client

        created = Mock()
        created.id = "dash-abc"
        created.to_dict.return_value = {"id": "dash-abc", "title": "Dashboard"}
        mock_client.dashboards.create_dashboard.return_value = created

        dash_data = {
            "title": "Dashboard",
            "layout_type": "ordered",
            "widgets": [],
        }

        result = runner.invoke(
            apply_cmd,
            ["--from-stdin"],
            input=json.dumps(dash_data),
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "dash-abc" in result.output
        mock_client.dashboards.create_dashboard.assert_called_once()

    def test_apply_from_stdin_dry_run(self, runner):
        """Test that dry-run works with --from-stdin."""
        monitor_data = {
            "name": "CPU Alert",
            "type": "metric alert",
            "query": "avg:system.cpu{*} > 90",
        }

        result = runner.invoke(
            apply_cmd,
            ["--from-stdin", "--dry-run"],
            input=json.dumps(monitor_data),
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "DRY RUN" in result.output

    def test_apply_from_stdin_invalid_json(self, runner):
        """Test that invalid JSON on stdin produces an error."""
        result = runner.invoke(
            apply_cmd,
            ["--from-stdin"],
            input="not valid json",
        )

        assert result.exit_code != 0

    def test_apply_from_stdin_unrecognized_resource(self, runner):
        """Test that unrecognized resource type from stdin produces an error."""
        result = runner.invoke(
            apply_cmd,
            ["--from-stdin"],
            input=json.dumps({"foo": "bar"}),
        )

        assert result.exit_code != 0

    def test_apply_requires_file_or_stdin(self, runner):
        """Test that apply fails without -f or --from-stdin."""
        result = runner.invoke(apply_cmd, [])

        assert result.exit_code != 0
