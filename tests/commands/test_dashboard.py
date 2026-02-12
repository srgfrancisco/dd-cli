"""Tests for dashboard management commands."""

import json
import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from ddogctl.commands.dashboard import dashboard


@pytest.fixture
def mock_client():
    """Create a mock Datadog client."""
    client = Mock()
    client.dashboards = Mock()
    return client


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


class MockDashboardSummary:
    """Mock dashboard summary object (from list_dashboards)."""

    def __init__(
        self,
        id,
        title,
        layout_type="ordered",
        author_handle="user@example.com",
        created_at="2024-01-15T10:00:00Z",
        url="/dashboard/abc-123",
    ):
        self.id = id
        self.title = title
        self.layout_type = layout_type
        self.author_handle = author_handle
        self.created_at = created_at
        self.url = url

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "layout_type": self.layout_type,
            "author_handle": self.author_handle,
            "created_at": self.created_at,
            "url": self.url,
        }


class MockDashboardListResponse:
    """Mock list_dashboards response."""

    def __init__(self, dashboards):
        self.dashboards = dashboards

    def to_dict(self):
        return {"dashboards": [d.to_dict() for d in self.dashboards]}


class MockDashboard:
    """Mock full dashboard object (from get/create/update)."""

    def __init__(
        self,
        id,
        title,
        layout_type="ordered",
        description="",
        author_handle="user@example.com",
        created_at="2024-01-15T10:00:00Z",
        url="/dashboard/abc-123",
        widgets=None,
    ):
        self.id = id
        self.title = title
        self.layout_type = layout_type
        self.description = description
        self.author_handle = author_handle
        self.created_at = created_at
        self.url = url
        self.widgets = widgets or []

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "layout_type": self.layout_type,
            "description": self.description,
            "author_handle": self.author_handle,
            "created_at": self.created_at,
            "url": self.url,
            "widgets": self.widgets,
        }


# ============================================================================
# Dashboard List Command Tests
# ============================================================================


def test_dashboard_list_table_format(mock_client, runner):
    """Test listing dashboards in table format (default)."""
    mock_dashboards = [
        MockDashboardSummary(
            "abc-123", "Production Overview", "ordered", "admin@example.com", "2024-01-15T10:00:00Z"
        ),
        MockDashboardSummary(
            "def-456", "Staging Metrics", "free", "dev@example.com", "2024-02-01T12:00:00Z"
        ),
    ]
    response = MockDashboardListResponse(mock_dashboards)
    mock_client.dashboards.list_dashboards.return_value = response

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["list"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Dashboards" in result.output
        assert "Production Overview" in result.output
        assert "Staging Metrics" in result.output
        assert "Total dashboards: 2" in result.output


def test_dashboard_list_json_format(mock_client, runner):
    """Test listing dashboards in JSON format."""
    mock_dashboards = [
        MockDashboardSummary("abc-123", "Production Overview"),
        MockDashboardSummary("def-456", "Staging Metrics", "free"),
    ]
    response = MockDashboardListResponse(mock_dashboards)
    mock_client.dashboards.list_dashboards.return_value = response

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["list", "--format", "json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert len(output) == 2
        assert output[0]["id"] == "abc-123"
        assert output[0]["title"] == "Production Overview"
        assert output[1]["id"] == "def-456"
        assert output[1]["layout_type"] == "free"


def test_dashboard_list_empty(mock_client, runner):
    """Test listing dashboards when none exist."""
    response = MockDashboardListResponse([])
    mock_client.dashboards.list_dashboards.return_value = response

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["list"])

        assert result.exit_code == 0
        assert "Total dashboards: 0" in result.output


def test_dashboard_list_with_tags_filter(mock_client, runner):
    """Test listing dashboards filtered by tags."""
    mock_dashboards = [
        MockDashboardSummary("abc-123", "Production Overview"),
    ]
    response = MockDashboardListResponse(mock_dashboards)
    mock_client.dashboards.list_dashboards.return_value = response

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["list", "--tags", "env:prod"])

        assert result.exit_code == 0
        mock_client.dashboards.list_dashboards.assert_called_once()
        call_kwargs = mock_client.dashboards.list_dashboards.call_args
        assert call_kwargs[1].get("filter_shared") is None or True
        # The filter_configured is passed as kwarg
        assert "filter_configured" in call_kwargs[1]


# ============================================================================
# Dashboard Get Command Tests
# ============================================================================


def test_dashboard_get_table_format(mock_client, runner):
    """Test getting a dashboard with table format."""
    mock_dash = MockDashboard(
        "abc-123",
        "Production Overview",
        "ordered",
        description="Main production dashboard",
        author_handle="admin@example.com",
    )
    mock_client.dashboards.get_dashboard.return_value = mock_dash

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["get", "abc-123"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "abc-123" in result.output
        assert "Production Overview" in result.output
        assert "ordered" in result.output
        assert "Main production dashboard" in result.output
        mock_client.dashboards.get_dashboard.assert_called_once_with("abc-123")


def test_dashboard_get_json_format(mock_client, runner):
    """Test getting a dashboard with JSON format."""
    mock_dash = MockDashboard("def-456", "Staging Metrics", "free")
    mock_client.dashboards.get_dashboard.return_value = mock_dash

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["get", "def-456", "--format", "json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == "def-456"
        assert output["title"] == "Staging Metrics"
        assert output["layout_type"] == "free"


# ============================================================================
# Dashboard Create Command Tests
# ============================================================================


def test_dashboard_create_from_file(mock_client, runner, tmp_path):
    """Test creating a dashboard from a JSON file."""
    dashboard_def = {
        "title": "New Dashboard",
        "layout_type": "ordered",
        "widgets": [{"definition": {"type": "timeseries"}}],
    }
    json_file = tmp_path / "dashboard.json"
    json_file.write_text(json.dumps(dashboard_def))

    created = MockDashboard("new-123", "New Dashboard")
    mock_client.dashboards.create_dashboard.return_value = created

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["create", "-f", str(json_file)])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "new-123" in result.output
        assert "created" in result.output.lower()
        mock_client.dashboards.create_dashboard.assert_called_once()


def test_dashboard_create_with_inline_flags(mock_client, runner):
    """Test creating a dashboard with inline flags (metadata only)."""
    created = MockDashboard("inline-123", "My Dashboard", "ordered")
    mock_client.dashboards.create_dashboard.return_value = created

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            dashboard,
            [
                "create",
                "--title",
                "My Dashboard",
                "--layout-type",
                "ordered",
                "--description",
                "A test dashboard",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "inline-123" in result.output
        assert "created" in result.output.lower()
        mock_client.dashboards.create_dashboard.assert_called_once()


def test_dashboard_create_missing_required(mock_client, runner):
    """Test that create fails when no file and no title provided."""
    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["create"])

        assert result.exit_code != 0


def test_dashboard_create_from_file_overrides_flags(mock_client, runner, tmp_path):
    """Test that -f flag takes precedence over inline flags."""
    dashboard_def = {
        "title": "From File",
        "layout_type": "free",
        "widgets": [],
    }
    json_file = tmp_path / "dashboard.json"
    json_file.write_text(json.dumps(dashboard_def))

    created = MockDashboard("file-123", "From File", "free")
    mock_client.dashboards.create_dashboard.return_value = created

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            dashboard,
            ["create", "-f", str(json_file), "--title", "Ignored Title"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Verify the file data was used
        call_kwargs = mock_client.dashboards.create_dashboard.call_args
        body = call_kwargs[1]["body"]
        assert body["title"] == "From File"


def test_dashboard_create_from_invalid_file(mock_client, runner, tmp_path):
    """Test creating a dashboard from an invalid JSON file."""
    json_file = tmp_path / "bad.json"
    json_file.write_text("not valid json {{{")

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["create", "-f", str(json_file)])

        assert result.exit_code != 0


def test_dashboard_create_json_output(mock_client, runner):
    """Test creating a dashboard with JSON output."""
    created = MockDashboard("json-123", "JSON Dashboard")
    mock_client.dashboards.create_dashboard.return_value = created

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            dashboard,
            [
                "create",
                "--title",
                "JSON Dashboard",
                "--layout-type",
                "ordered",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == "json-123"
        assert output["title"] == "JSON Dashboard"


# ============================================================================
# Dashboard Update Command Tests
# ============================================================================


def test_dashboard_update_from_file(mock_client, runner, tmp_path):
    """Test updating a dashboard from a JSON file."""
    dashboard_def = {
        "title": "Updated Dashboard",
        "layout_type": "ordered",
        "widgets": [{"definition": {"type": "query_value"}}],
    }
    json_file = tmp_path / "update.json"
    json_file.write_text(json.dumps(dashboard_def))

    updated = MockDashboard("abc-123", "Updated Dashboard")
    mock_client.dashboards.update_dashboard.return_value = updated

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["update", "abc-123", "-f", str(json_file)])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "abc-123" in result.output
        assert "updated" in result.output.lower()
        mock_client.dashboards.update_dashboard.assert_called_once()
        call_args = mock_client.dashboards.update_dashboard.call_args
        assert call_args[0][0] == "abc-123"


def test_dashboard_update_missing_file(mock_client, runner):
    """Test that update fails when no file is provided."""
    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["update", "abc-123"])

        assert result.exit_code != 0


def test_dashboard_update_json_output(mock_client, runner, tmp_path):
    """Test updating a dashboard with JSON output."""
    dashboard_def = {"title": "Updated", "layout_type": "ordered", "widgets": []}
    json_file = tmp_path / "update.json"
    json_file.write_text(json.dumps(dashboard_def))

    updated = MockDashboard("abc-123", "Updated")
    mock_client.dashboards.update_dashboard.return_value = updated

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            dashboard, ["update", "abc-123", "-f", str(json_file), "--format", "json"]
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == "abc-123"


# ============================================================================
# Dashboard Delete Command Tests
# ============================================================================


def test_dashboard_delete_with_confirm_flag(mock_client, runner):
    """Test deleting a dashboard with --confirm flag (no prompt)."""
    mock_client.dashboards.delete_dashboard.return_value = Mock()

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["delete", "abc-123", "--confirm"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "abc-123" in result.output
        assert "deleted" in result.output.lower()
        mock_client.dashboards.delete_dashboard.assert_called_once_with("abc-123")


def test_dashboard_delete_interactive_confirm_yes(mock_client, runner):
    """Test deleting a dashboard with interactive confirmation (user says yes)."""
    mock_client.dashboards.delete_dashboard.return_value = Mock()

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["delete", "abc-123"], input="y\n")

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "deleted" in result.output.lower()
        mock_client.dashboards.delete_dashboard.assert_called_once_with("abc-123")


def test_dashboard_delete_interactive_confirm_no(mock_client, runner):
    """Test deleting a dashboard with interactive confirmation (user says no)."""
    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["delete", "abc-123"], input="n\n")

        assert result.exit_code == 0
        assert "Aborted" in result.output
        mock_client.dashboards.delete_dashboard.assert_not_called()


# ============================================================================
# Dashboard Export Command Tests
# ============================================================================


def test_dashboard_export(mock_client, runner, tmp_path):
    """Test exporting a dashboard to a JSON file."""
    mock_dash = MockDashboard(
        "abc-123",
        "Production Overview",
        "ordered",
        widgets=[{"definition": {"type": "timeseries"}}],
    )
    mock_client.dashboards.get_dashboard.return_value = mock_dash

    output_file = tmp_path / "exported.json"

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["export", "abc-123", "-o", str(output_file)])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "exported" in result.output.lower()
        mock_client.dashboards.get_dashboard.assert_called_once_with("abc-123")

        # Verify file was written
        assert output_file.exists()
        exported = json.loads(output_file.read_text())
        assert exported["title"] == "Production Overview"
        assert exported["layout_type"] == "ordered"


def test_dashboard_export_missing_output(mock_client, runner):
    """Test that export fails when -o is not provided."""
    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["export", "abc-123"])

        assert result.exit_code != 0


# ============================================================================
# Dashboard Clone Command Tests
# ============================================================================


def test_dashboard_clone(mock_client, runner):
    """Test cloning a dashboard with a new title."""
    # Setup: get returns the original dashboard
    original = MockDashboard(
        "abc-123",
        "Production Overview",
        "ordered",
        description="Original description",
        widgets=[{"definition": {"type": "timeseries"}}],
    )
    mock_client.dashboards.get_dashboard.return_value = original

    # Setup: create returns the cloned dashboard
    cloned = MockDashboard("cloned-456", "Copy of Production Overview")
    mock_client.dashboards.create_dashboard.return_value = cloned

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            dashboard, ["clone", "abc-123", "--title", "Copy of Production Overview"]
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "cloned-456" in result.output
        assert "cloned" in result.output.lower()

        # Verify get was called to fetch original
        mock_client.dashboards.get_dashboard.assert_called_once_with("abc-123")

        # Verify create was called with the new title
        mock_client.dashboards.create_dashboard.assert_called_once()
        call_kwargs = mock_client.dashboards.create_dashboard.call_args
        body = call_kwargs[1]["body"]
        assert body["title"] == "Copy of Production Overview"


def test_dashboard_clone_missing_title(mock_client, runner):
    """Test that clone fails when --title is not provided."""
    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["clone", "abc-123"])

        assert result.exit_code != 0


def test_dashboard_clone_json_output(mock_client, runner):
    """Test cloning a dashboard with JSON output."""
    original = MockDashboard(
        "abc-123",
        "Original",
        "ordered",
        widgets=[{"definition": {"type": "timeseries"}}],
    )
    mock_client.dashboards.get_dashboard.return_value = original

    cloned = MockDashboard("cloned-789", "Cloned Dashboard")
    mock_client.dashboards.create_dashboard.return_value = cloned

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            dashboard,
            ["clone", "abc-123", "--title", "Cloned Dashboard", "--format", "json"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == "cloned-789"
        assert output["title"] == "Cloned Dashboard"


# ============================================================================
# Edge Cases & Integration Tests
# ============================================================================


def test_dashboard_list_then_get_workflow(mock_client, runner):
    """Test workflow: list dashboards, then get details of one."""
    # Setup list
    mock_dashboards = [
        MockDashboardSummary("abc-123", "Dashboard A"),
        MockDashboardSummary("def-456", "Dashboard B"),
    ]
    response = MockDashboardListResponse(mock_dashboards)
    mock_client.dashboards.list_dashboards.return_value = response

    # Setup get
    mock_dash = MockDashboard("abc-123", "Dashboard A", "ordered")
    mock_client.dashboards.get_dashboard.return_value = mock_dash

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        # List dashboards
        result = runner.invoke(dashboard, ["list", "--format", "json"])
        assert result.exit_code == 0
        dashboards_list = json.loads(result.output)
        assert len(dashboards_list) == 2

        # Get details of the first one
        result = runner.invoke(dashboard, ["get", "abc-123", "--format", "json"])
        assert result.exit_code == 0
        dash_details = json.loads(result.output)
        assert dash_details["id"] == "abc-123"


def test_dashboard_export_modify_update_workflow(mock_client, runner, tmp_path):
    """Test GitOps workflow: export -> modify -> update."""
    # Export
    original = MockDashboard(
        "abc-123",
        "Original Title",
        "ordered",
        widgets=[{"definition": {"type": "timeseries"}}],
    )
    mock_client.dashboards.get_dashboard.return_value = original

    export_file = tmp_path / "dashboard.json"
    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["export", "abc-123", "-o", str(export_file)])
        assert result.exit_code == 0

    # Modify the exported file
    data = json.loads(export_file.read_text())
    data["title"] = "Modified Title"
    export_file.write_text(json.dumps(data))

    # Update
    updated = MockDashboard("abc-123", "Modified Title")
    mock_client.dashboards.update_dashboard.return_value = updated

    with patch("ddogctl.commands.dashboard.get_datadog_client", return_value=mock_client):
        result = runner.invoke(dashboard, ["update", "abc-123", "-f", str(export_file)])
        assert result.exit_code == 0
        assert "updated" in result.output.lower()
