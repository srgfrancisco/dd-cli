"""Tests for stdin input utilities."""

import json
from io import StringIO
from unittest.mock import patch

import click
import pytest

from ddogctl.utils.stdin import read_stdin_json


class TestReadStdinJson:
    """Tests for the read_stdin_json function."""

    def test_reads_valid_json_object(self):
        """Test that a valid JSON object is parsed correctly."""
        json_data = '{"name": "test", "type": "metric alert"}'
        with patch("sys.stdin", new=StringIO(json_data)):
            with patch("sys.stdin.isatty", return_value=False):
                result = read_stdin_json()
        assert result == {"name": "test", "type": "metric alert"}

    def test_reads_valid_json_array(self):
        """Test that a valid JSON array is parsed correctly."""
        json_data = '[{"id": 1}, {"id": 2}]'
        with patch("sys.stdin", new=StringIO(json_data)):
            with patch("sys.stdin.isatty", return_value=False):
                result = read_stdin_json()
        assert result == [{"id": 1}, {"id": 2}]

    def test_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        json_data = '  \n {"name": "test"} \n '
        with patch("sys.stdin", new=StringIO(json_data)):
            with patch("sys.stdin.isatty", return_value=False):
                result = read_stdin_json()
        assert result == {"name": "test"}

    def test_raises_on_tty_stdin(self):
        """Test that an error is raised when stdin is a TTY (no piped input)."""
        with patch("sys.stdin.isatty", return_value=True):
            with pytest.raises(click.ClickException, match="No input on stdin"):
                read_stdin_json()

    def test_raises_on_empty_stdin(self):
        """Test that an error is raised when stdin is empty."""
        with patch("sys.stdin", new=StringIO("")):
            with patch("sys.stdin.isatty", return_value=False):
                with pytest.raises(click.ClickException, match="Empty stdin"):
                    read_stdin_json()

    def test_raises_on_whitespace_only_stdin(self):
        """Test that an error is raised when stdin contains only whitespace."""
        with patch("sys.stdin", new=StringIO("   \n  ")):
            with patch("sys.stdin.isatty", return_value=False):
                with pytest.raises(click.ClickException, match="Empty stdin"):
                    read_stdin_json()

    def test_raises_on_invalid_json(self):
        """Test that an error is raised for invalid JSON input."""
        with patch("sys.stdin", new=StringIO("not json")):
            with patch("sys.stdin.isatty", return_value=False):
                with pytest.raises(click.ClickException, match="Invalid JSON"):
                    read_stdin_json()

    def test_reads_nested_json(self):
        """Test that deeply nested JSON structures are parsed correctly."""
        data = {
            "name": "test",
            "options": {"thresholds": {"critical": 90}},
            "tags": ["env:prod", "service:web"],
        }
        json_data = json.dumps(data)
        with patch("sys.stdin", new=StringIO(json_data)):
            with patch("sys.stdin.isatty", return_value=False):
                result = read_stdin_json()
        assert result == data
