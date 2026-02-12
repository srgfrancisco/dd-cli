"""Tests for output format utilities."""

import json
from io import StringIO
from unittest.mock import patch

import pytest

from ddogctl.utils.output import emit_error, get_output_format, set_output_format


@pytest.fixture(autouse=True)
def reset_output_format():
    """Reset output format to table after each test."""
    yield
    set_output_format("table")


class TestOutputFormat:
    """Test suite for output format state management."""

    def test_default_format_is_table(self):
        """Test that the default output format is table."""
        assert get_output_format() == "table"

    def test_set_json_format(self):
        """Test switching to JSON output format."""
        set_output_format("json")
        assert get_output_format() == "json"

    def test_set_table_format(self):
        """Test explicitly setting table output format."""
        set_output_format("json")
        set_output_format("table")
        assert get_output_format() == "table"


class TestEmitError:
    """Test suite for emit_error function."""

    def test_json_format_outputs_to_stderr(self):
        """Test that JSON mode outputs structured error JSON to stderr."""
        set_output_format("json")
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            emit_error("AUTH_FAILED", 401, "Auth failed", "Check keys")

        output = mock_stderr.getvalue()
        data = json.loads(output)
        assert data["error"] is True
        assert data["code"] == "AUTH_FAILED"
        assert data["status"] == 401
        assert data["message"] == "Auth failed"
        assert data["hint"] == "Check keys"

    def test_json_format_without_hint(self):
        """Test that JSON mode omits hint field when not provided."""
        set_output_format("json")
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            emit_error("API_ERROR", 400, "Bad request")

        output = mock_stderr.getvalue()
        data = json.loads(output)
        assert data["error"] is True
        assert data["code"] == "API_ERROR"
        assert data["status"] == 400
        assert data["message"] == "Bad request"
        assert "hint" not in data

    def test_json_format_with_zero_status(self):
        """Test JSON output with zero status for non-API errors."""
        set_output_format("json")
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            emit_error("UNEXPECTED_ERROR", 0, "Something broke")

        output = mock_stderr.getvalue()
        data = json.loads(output)
        assert data["status"] == 0
        assert data["code"] == "UNEXPECTED_ERROR"

    def test_json_format_all_error_codes(self):
        """Test that all defined error codes produce valid JSON output."""
        set_output_format("json")
        error_codes = [
            ("AUTH_FAILED", 401),
            ("PERMISSION_DENIED", 403),
            ("NOT_FOUND", 404),
            ("RATE_LIMITED", 429),
            ("SERVER_ERROR", 500),
            ("API_ERROR", 400),
            ("UNEXPECTED_ERROR", 0),
        ]
        for code, status in error_codes:
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                emit_error(code, status, f"Test {code}")
            data = json.loads(mock_stderr.getvalue())
            assert data["code"] == code
            assert data["status"] == status

    def test_table_format_uses_rich(self):
        """Test that table mode outputs via Rich console without error."""
        set_output_format("table")
        with patch("rich.console.Console") as mock_console_cls:
            mock_console = mock_console_cls.return_value
            emit_error("AUTH_FAILED", 401, "Auth failed", "Check keys")

        mock_console_cls.assert_called_once_with(stderr=True)
        assert mock_console.print.call_count == 2
        # First call: error message
        error_call = mock_console.print.call_args_list[0][0][0]
        assert "Auth failed" in error_call
        # Second call: hint
        hint_call = mock_console.print.call_args_list[1][0][0]
        assert "Check keys" in hint_call

    def test_table_format_without_hint(self):
        """Test that table mode skips hint line when not provided."""
        set_output_format("table")
        with patch("rich.console.Console") as mock_console_cls:
            mock_console = mock_console_cls.return_value
            emit_error("API_ERROR", 400, "Bad request")

        mock_console.print.assert_called_once()
        call_arg = mock_console.print.call_args[0][0]
        assert "Bad request" in call_arg

    def test_json_output_is_single_line(self):
        """Test that JSON output is a single line (no pretty printing)."""
        set_output_format("json")
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            emit_error("AUTH_FAILED", 401, "Auth failed", "Check keys")

        output = mock_stderr.getvalue().strip()
        assert "\n" not in output
