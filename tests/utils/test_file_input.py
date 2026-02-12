"""Tests for JSON file input parsing utility."""

import json
import pytest

from ddogctl.utils.file_input import load_json_file, load_json_option


class TestLoadJsonFile:
    """Tests for load_json_file()."""

    def test_loads_valid_json_file(self, tmp_path):
        """Load a valid JSON file and return dict."""
        data = {"type": "metric alert", "query": "avg:system.cpu.user{*} > 90", "name": "CPU High"}
        f = tmp_path / "monitor.json"
        f.write_text(json.dumps(data))

        result = load_json_file(str(f))
        assert result == data

    def test_loads_json_array(self, tmp_path):
        """Load a JSON file with an array at the root."""
        data = [{"name": "mon1"}, {"name": "mon2"}]
        f = tmp_path / "monitors.json"
        f.write_text(json.dumps(data))

        result = load_json_file(str(f))
        assert result == data

    def test_raises_on_missing_file(self):
        """Raise FileNotFoundError for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            load_json_file("/nonexistent/path/monitor.json")

    def test_raises_on_invalid_json(self, tmp_path):
        """Raise ValueError for malformed JSON."""
        f = tmp_path / "bad.json"
        f.write_text("{not valid json}")

        with pytest.raises(ValueError, match="Invalid JSON"):
            load_json_file(str(f))

    def test_raises_on_empty_file(self, tmp_path):
        """Raise ValueError for empty file."""
        f = tmp_path / "empty.json"
        f.write_text("")

        with pytest.raises(ValueError, match="Invalid JSON"):
            load_json_file(str(f))


class TestLoadJsonOption:
    """Tests for load_json_option() Click callback."""

    def test_returns_none_when_no_file(self):
        """Return None when no file path provided."""
        result = load_json_option(None, None, None)
        assert result is None

    def test_loads_file_and_returns_dict(self, tmp_path):
        """Load file via Click callback and return parsed dict."""
        data = {"name": "test monitor"}
        f = tmp_path / "monitor.json"
        f.write_text(json.dumps(data))

        result = load_json_option(None, None, str(f))
        assert result == data

    def test_raises_bad_parameter_on_missing_file(self):
        """Raise click.BadParameter for missing file."""
        import click

        with pytest.raises(click.BadParameter, match="not found"):
            load_json_option(None, None, "/nonexistent/file.json")

    def test_raises_bad_parameter_on_invalid_json(self, tmp_path):
        """Raise click.BadParameter for malformed JSON."""
        import click

        f = tmp_path / "bad.json"
        f.write_text("{bad json}")

        with pytest.raises(click.BadParameter, match="Invalid JSON"):
            load_json_option(None, None, str(f))
