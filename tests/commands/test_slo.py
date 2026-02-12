"""Tests for SLO management commands."""

import json
import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from ddogctl.commands.slo import slo, parse_thresholds

# ============================================================================
# parse_thresholds Tests
# ============================================================================


class TestParseThresholds:
    """Tests for the parse_thresholds helper function."""

    def test_single_threshold(self):
        """Test parsing a single threshold."""
        result = parse_thresholds("30d:99.9")
        assert result == [{"timeframe": "30d", "target": 99.9}]

    def test_multiple_thresholds(self):
        """Test parsing multiple comma-separated thresholds."""
        result = parse_thresholds("30d:99.9,7d:99.95")
        assert result == [
            {"timeframe": "30d", "target": 99.9},
            {"timeframe": "7d", "target": 99.95},
        ]

    def test_three_thresholds(self):
        """Test parsing three thresholds."""
        result = parse_thresholds("30d:99.9,7d:99.95,90d:99.5")
        assert len(result) == 3
        assert result[0]["timeframe"] == "30d"
        assert result[1]["timeframe"] == "7d"
        assert result[2]["timeframe"] == "90d"

    def test_integer_target(self):
        """Test parsing a threshold with an integer target."""
        result = parse_thresholds("30d:99")
        assert result == [{"timeframe": "30d", "target": 99.0}]

    def test_invalid_format_missing_colon(self):
        """Test that missing colon raises ValueError."""
        with pytest.raises(ValueError, match="Invalid threshold"):
            parse_thresholds("30d99.9")

    def test_invalid_target_not_a_number(self):
        """Test that non-numeric target raises ValueError."""
        with pytest.raises(ValueError, match="Invalid threshold"):
            parse_thresholds("30d:abc")

    def test_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            parse_thresholds("")


# ============================================================================
# SLO List Command Tests
# ============================================================================


@pytest.fixture
def mock_client():
    """Create a mock Datadog client."""
    client = Mock()
    client.slos = Mock()
    return client


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


def _make_mock_slo(slo_id, name, slo_type, tags=None, thresholds=None, description=""):
    """Factory for mock SLO objects."""

    class MockSLO:
        def __init__(self):
            self.id = slo_id
            self.name = name
            self.type = slo_type
            self.tags = tags or []
            self.thresholds = thresholds or []
            self.description = description
            self.creator = Mock(email="test@example.com")
            self.created_at = 1700000000
            self.modified_at = 1700100000

        def to_dict(self):
            return {
                "id": self.id,
                "name": self.name,
                "type": self.type,
                "tags": self.tags,
                "thresholds": [t if isinstance(t, dict) else t for t in self.thresholds],
                "description": self.description,
            }

    return MockSLO()


def test_slo_list_table_format(mock_client, runner):
    """Test listing SLOs with table format."""
    mock_slos = [
        _make_mock_slo("abc123", "API Availability", "metric", tags=["team:platform"]),
        _make_mock_slo("def456", "DB Health", "monitor", tags=["team:infra"]),
    ]
    mock_client.slos.list_slos.return_value = Mock(data=mock_slos)

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["list"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "API Availability" in result.output
        assert "DB Health" in result.output
        assert "Total SLOs: 2" in result.output


def test_slo_list_json_format(mock_client, runner):
    """Test listing SLOs with JSON format."""
    mock_slos = [
        _make_mock_slo("abc123", "API Availability", "metric", tags=["team:platform"]),
    ]
    mock_client.slos.list_slos.return_value = Mock(data=mock_slos)

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["list", "--format", "json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["id"] == "abc123"
        assert output[0]["name"] == "API Availability"


def test_slo_list_with_query(mock_client, runner):
    """Test listing SLOs with a search query."""
    mock_slos = [
        _make_mock_slo("abc123", "API Availability", "metric"),
    ]
    mock_client.slos.list_slos.return_value = Mock(data=mock_slos)

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["list", "--query", "API"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        mock_client.slos.list_slos.assert_called_once()
        call_kwargs = mock_client.slos.list_slos.call_args
        # query should be passed as a keyword arg
        assert "query" in call_kwargs[1] or (call_kwargs[0] and "API" in str(call_kwargs))


def test_slo_list_with_tags_filter(mock_client, runner):
    """Test listing SLOs with tags filter."""
    mock_slos = [
        _make_mock_slo("abc123", "API Availability", "metric", tags=["team:platform"]),
    ]
    mock_client.slos.list_slos.return_value = Mock(data=mock_slos)

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["list", "--tags", "team:platform"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        mock_client.slos.list_slos.assert_called_once()
        call_kwargs = mock_client.slos.list_slos.call_args
        assert "tags_query" in call_kwargs[1]


def test_slo_list_with_limit(mock_client, runner):
    """Test listing SLOs with limit."""
    mock_slos = [
        _make_mock_slo("abc123", "API Availability", "metric"),
    ]
    mock_client.slos.list_slos.return_value = Mock(data=mock_slos)

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["list", "--limit", "5"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        call_kwargs = mock_client.slos.list_slos.call_args
        assert "limit" in call_kwargs[1]
        assert call_kwargs[1]["limit"] == 5


def test_slo_list_empty(mock_client, runner):
    """Test listing SLOs when none exist."""
    mock_client.slos.list_slos.return_value = Mock(data=[])

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["list"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Total SLOs: 0" in result.output


# ============================================================================
# SLO Get Command Tests
# ============================================================================


def test_slo_get_table_format(mock_client, runner):
    """Test getting a single SLO with table format."""
    mock_slo = _make_mock_slo(
        "abc123",
        "API Availability",
        "metric",
        tags=["team:platform"],
        description="API availability SLO",
    )
    mock_client.slos.get_slo.return_value = Mock(data=mock_slo)

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["get", "abc123"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "abc123" in result.output
        assert "API Availability" in result.output
        assert "metric" in result.output


def test_slo_get_json_format(mock_client, runner):
    """Test getting a single SLO with JSON format."""
    mock_slo = _make_mock_slo("abc123", "API Availability", "metric")
    mock_client.slos.get_slo.return_value = Mock(data=mock_slo)

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["get", "abc123", "--format", "json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == "abc123"
        assert output["name"] == "API Availability"


# ============================================================================
# SLO Create Command Tests
# ============================================================================


def test_slo_create_metric_type(mock_client, runner):
    """Test creating a metric-based SLO with inline flags."""
    created_slo = _make_mock_slo("new123", "API Availability", "metric")
    mock_client.slos.create_slo.return_value = Mock(data=[created_slo])

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            slo,
            [
                "create",
                "--type",
                "metric",
                "--name",
                "API Availability",
                "--thresholds",
                "30d:99.9,7d:99.95",
                "--numerator",
                "sum:api.requests.success{*}",
                "--denominator",
                "sum:api.requests.total{*}",
                "--tags",
                "team:platform",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "SLO" in result.output and "created" in result.output
        mock_client.slos.create_slo.assert_called_once()


def test_slo_create_monitor_type(mock_client, runner):
    """Test creating a monitor-based SLO with inline flags."""
    created_slo = _make_mock_slo("new456", "DB Health", "monitor")
    mock_client.slos.create_slo.return_value = Mock(data=[created_slo])

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            slo,
            [
                "create",
                "--type",
                "monitor",
                "--name",
                "DB Health",
                "--monitor-ids",
                "123,456",
                "--thresholds",
                "30d:99.9",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "SLO" in result.output and "created" in result.output
        mock_client.slos.create_slo.assert_called_once()


def test_slo_create_from_file(mock_client, runner, tmp_path):
    """Test creating an SLO from a JSON file."""
    slo_def = {
        "type": "metric",
        "name": "API SLO from file",
        "thresholds": [{"timeframe": "30d", "target": 99.9}],
        "query": {
            "numerator": "sum:api.requests.success{*}",
            "denominator": "sum:api.requests.total{*}",
        },
        "tags": ["team:platform"],
    }
    json_file = tmp_path / "slo.json"
    json_file.write_text(json.dumps(slo_def))

    created_slo = _make_mock_slo("file123", "API SLO from file", "metric")
    mock_client.slos.create_slo.return_value = Mock(data=[created_slo])

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["create", "-f", str(json_file)])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "SLO" in result.output and "created" in result.output
        mock_client.slos.create_slo.assert_called_once()


def test_slo_create_missing_required_metric_fields(mock_client, runner):
    """Test that metric SLO requires numerator and denominator."""
    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            slo,
            [
                "create",
                "--type",
                "metric",
                "--name",
                "Test",
                "--thresholds",
                "30d:99.9",
                # Missing --numerator and --denominator
            ],
        )

        assert result.exit_code != 0


def test_slo_create_missing_required_monitor_fields(mock_client, runner):
    """Test that monitor SLO requires monitor-ids."""
    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            slo,
            [
                "create",
                "--type",
                "monitor",
                "--name",
                "Test",
                "--thresholds",
                "30d:99.9",
                # Missing --monitor-ids
            ],
        )

        assert result.exit_code != 0


def test_slo_create_missing_name(mock_client, runner):
    """Test that create fails when --name is missing without -f."""
    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            slo,
            [
                "create",
                "--type",
                "metric",
                "--thresholds",
                "30d:99.9",
                "--numerator",
                "sum:ok{*}",
                "--denominator",
                "sum:total{*}",
            ],
        )

        assert result.exit_code != 0


def test_slo_create_missing_thresholds(mock_client, runner):
    """Test that create fails when --thresholds is missing without -f."""
    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            slo,
            [
                "create",
                "--type",
                "metric",
                "--name",
                "Test",
                "--numerator",
                "sum:ok{*}",
                "--denominator",
                "sum:total{*}",
            ],
        )

        assert result.exit_code != 0


def test_slo_create_json_output(mock_client, runner):
    """Test creating an SLO with JSON output format."""
    created_slo = _make_mock_slo("json123", "JSON Test SLO", "metric")
    mock_client.slos.create_slo.return_value = Mock(data=[created_slo])

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            slo,
            [
                "create",
                "--type",
                "metric",
                "--name",
                "JSON Test SLO",
                "--thresholds",
                "30d:99.9",
                "--numerator",
                "sum:ok{*}",
                "--denominator",
                "sum:total{*}",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == "json123"


# ============================================================================
# SLO Update Command Tests
# ============================================================================


def test_slo_update_with_inline_flags(mock_client, runner):
    """Test updating an SLO with inline flags."""
    updated_slo = _make_mock_slo("abc123", "Updated SLO", "metric")
    mock_client.slos.update_slo.return_value = Mock(data=[updated_slo])

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            slo,
            [
                "update",
                "abc123",
                "--name",
                "Updated SLO",
                "--thresholds",
                "30d:99.95",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "updated" in result.output
        mock_client.slos.update_slo.assert_called_once()


def test_slo_update_from_file(mock_client, runner, tmp_path):
    """Test updating an SLO from a JSON file."""
    slo_def = {
        "name": "Updated from file",
        "thresholds": [{"timeframe": "30d", "target": 99.95}],
    }
    json_file = tmp_path / "slo_update.json"
    json_file.write_text(json.dumps(slo_def))

    updated_slo = _make_mock_slo("abc123", "Updated from file", "metric")
    mock_client.slos.update_slo.return_value = Mock(data=[updated_slo])

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["update", "abc123", "-f", str(json_file)])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "updated" in result.output
        mock_client.slos.update_slo.assert_called_once()


def test_slo_update_no_fields(mock_client, runner):
    """Test that update fails when no fields are specified."""
    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["update", "abc123"])

        assert result.exit_code != 0


def test_slo_update_json_output(mock_client, runner):
    """Test updating an SLO with JSON output format."""
    updated_slo = _make_mock_slo("abc123", "JSON Update", "metric")
    mock_client.slos.update_slo.return_value = Mock(data=[updated_slo])

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            slo,
            ["update", "abc123", "--name", "JSON Update", "--format", "json"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == "abc123"


# ============================================================================
# SLO Delete Command Tests
# ============================================================================


def test_slo_delete_with_confirm_flag(mock_client, runner):
    """Test deleting an SLO with --confirm flag (no prompt)."""
    mock_client.slos.delete_slo.return_value = Mock()

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["delete", "abc123", "--confirm"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "deleted" in result.output
        mock_client.slos.delete_slo.assert_called_once_with("abc123")


def test_slo_delete_interactive_confirm_yes(mock_client, runner):
    """Test deleting an SLO with interactive confirmation (user says yes)."""
    mock_client.slos.delete_slo.return_value = Mock()

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["delete", "abc123"], input="y\n")

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "deleted" in result.output
        mock_client.slos.delete_slo.assert_called_once_with("abc123")


def test_slo_delete_interactive_confirm_no(mock_client, runner):
    """Test deleting an SLO with interactive confirmation (user says no)."""
    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["delete", "abc123"], input="n\n")

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Aborted" in result.output
        mock_client.slos.delete_slo.assert_not_called()


# ============================================================================
# SLO History Command Tests
# ============================================================================


def test_slo_history_table_format(mock_client, runner):
    """Test SLO history with table format."""
    mock_history = Mock()
    mock_history.data = Mock()
    mock_history.data.overall = Mock()
    mock_history.data.overall.sli_value = 99.95
    mock_history.data.overall.span_precision = 2
    mock_history.data.thresholds = {
        "30d": Mock(
            target=99.9,
            timeframe="30d",
            target_display="99.9",
            sli_value=99.95,
        ),
    }
    mock_history.data.to_dict = lambda: {
        "overall": {"sli_value": 99.95},
        "thresholds": {
            "30d": {"target": 99.9, "timeframe": "30d", "sli_value": 99.95},
        },
    }

    mock_client.slos.get_slo_history.return_value = mock_history

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["history", "abc123", "--from", "30d"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        mock_client.slos.get_slo_history.assert_called_once()


def test_slo_history_json_format(mock_client, runner):
    """Test SLO history with JSON format."""
    mock_history = Mock()
    mock_history.data = Mock()
    mock_history.data.to_dict.return_value = {
        "overall": {"sli_value": 99.95},
        "thresholds": {
            "30d": {"target": 99.9, "timeframe": "30d", "sli_value": 99.95},
        },
    }

    mock_client.slos.get_slo_history.return_value = mock_history

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["history", "abc123", "--from", "30d", "--format", "json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert "overall" in output


# ============================================================================
# SLO Export Command Tests
# ============================================================================


def test_slo_export(mock_client, runner, tmp_path):
    """Test exporting an SLO to JSON file."""
    mock_slo = _make_mock_slo(
        "abc123",
        "API Availability",
        "metric",
        tags=["team:platform"],
    )
    mock_client.slos.get_slo.return_value = Mock(data=mock_slo)

    output_file = tmp_path / "slo_export.json"

    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["export", "abc123", "-o", str(output_file)])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Exported" in result.output

        # Verify the exported file
        exported = json.loads(output_file.read_text())
        assert exported["id"] == "abc123"
        assert exported["name"] == "API Availability"


def test_slo_export_missing_output(mock_client, runner):
    """Test that export fails when -o is not specified."""
    with patch("ddogctl.commands.slo.get_datadog_client", return_value=mock_client):
        result = runner.invoke(slo, ["export", "abc123"])

        assert result.exit_code != 0
