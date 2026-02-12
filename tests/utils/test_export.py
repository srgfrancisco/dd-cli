"""Tests for export output utility (dict → JSON file)."""

import json

from ddogctl.utils.export import export_to_json


class TestExportToJson:
    """Tests for export_to_json()."""

    def test_exports_dict_to_file(self, tmp_path):
        """Export a dict to a JSON file."""
        data = {"id": "abc-123", "title": "My Dashboard", "widgets": []}
        output = tmp_path / "dashboard.json"

        export_to_json(data, str(output))

        loaded = json.loads(output.read_text())
        assert loaded == data

    def test_exports_list_to_file(self, tmp_path):
        """Export a list to a JSON file."""
        data = [{"name": "mon1"}, {"name": "mon2"}]
        output = tmp_path / "monitors.json"

        export_to_json(data, str(output))

        loaded = json.loads(output.read_text())
        assert loaded == data

    def test_output_is_pretty_printed(self, tmp_path):
        """Exported JSON should be indented for readability."""
        data = {"key": "value"}
        output = tmp_path / "out.json"

        export_to_json(data, str(output))

        text = output.read_text()
        assert "  " in text  # indented
        assert text.endswith("\n")  # trailing newline

    def test_creates_parent_directories(self, tmp_path):
        """Create parent dirs if they don't exist."""
        data = {"key": "value"}
        output = tmp_path / "subdir" / "nested" / "out.json"

        export_to_json(data, str(output))

        assert output.exists()
        loaded = json.loads(output.read_text())
        assert loaded == data

    def test_overwrites_existing_file(self, tmp_path):
        """Overwrite an existing file without error."""
        output = tmp_path / "out.json"
        output.write_text('{"old": "data"}')

        new_data = {"new": "data"}
        export_to_json(new_data, str(output))

        loaded = json.loads(output.read_text())
        assert loaded == new_data

    def test_handles_datetime_serialization(self, tmp_path):
        """Handle non-serializable types gracefully using default=str."""
        from datetime import datetime

        data = {"timestamp": datetime(2026, 1, 15, 10, 30, 0)}
        output = tmp_path / "out.json"

        export_to_json(data, str(output))

        loaded = json.loads(output.read_text())
        assert "2026" in loaded["timestamp"]
