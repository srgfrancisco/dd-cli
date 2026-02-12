"""Tests for time parsing utilities."""

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
from ddg.utils.time import parse_time_range


class TestParseTimeRange:
    """Test suite for parse_time_range function."""

    @pytest.fixture
    def mock_now(self):
        """Fixed datetime for predictable testing."""
        return datetime(2026, 2, 11, 15, 30, 0)  # 2026-02-11 15:30:00

    def test_now_to_now(self, mock_now):
        """Test 'now' to 'now' returns same timestamp."""
        with patch("ddg.utils.time.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now
            from_ts, to_ts = parse_time_range("now", "now")

            assert from_ts == to_ts
            assert from_ts == int(mock_now.timestamp())

    def test_hours_ago(self, mock_now):
        """Test relative hour parsing (1h, 24h, etc.)."""
        with patch("ddg.utils.time.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            # 1 hour ago
            from_ts, to_ts = parse_time_range("1h", "now")
            expected_from = mock_now - timedelta(hours=1)
            assert from_ts == int(expected_from.timestamp())
            assert to_ts == int(mock_now.timestamp())

            # 24 hours ago
            from_ts, to_ts = parse_time_range("24h", "now")
            expected_from = mock_now - timedelta(hours=24)
            assert from_ts == int(expected_from.timestamp())

    def test_days_ago(self, mock_now):
        """Test relative day parsing (1d, 7d, etc.)."""
        with patch("ddg.utils.time.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            # 7 days ago
            from_ts, to_ts = parse_time_range("7d", "now")
            expected_from = mock_now - timedelta(days=7)
            assert from_ts == int(expected_from.timestamp())
            assert to_ts == int(mock_now.timestamp())

    def test_minutes_ago(self, mock_now):
        """Test relative minute parsing (30m, 60m, etc.)."""
        with patch("ddg.utils.time.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            # 30 minutes ago
            from_ts, to_ts = parse_time_range("30m", "now")
            expected_from = mock_now - timedelta(minutes=30)
            assert from_ts == int(expected_from.timestamp())
            assert to_ts == int(mock_now.timestamp())

    def test_iso_datetime_parsing(self, mock_now):
        """Test ISO datetime format parsing."""
        with patch("ddg.utils.time.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now
            # Need to patch fromisoformat to work correctly
            mock_datetime.fromisoformat = datetime.fromisoformat

            # Specific ISO timestamp
            iso_from = "2026-02-10T10:00:00"
            iso_to = "2026-02-11T10:00:00"

            from_ts, to_ts = parse_time_range(iso_from, iso_to)

            expected_from = datetime.fromisoformat(iso_from)
            expected_to = datetime.fromisoformat(iso_to)

            assert from_ts == int(expected_from.timestamp())
            assert to_ts == int(expected_to.timestamp())

    def test_mixed_formats(self, mock_now):
        """Test mixing relative and ISO formats."""
        with patch("ddg.utils.time.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat

            # From ISO to now
            iso_from = "2026-02-10T10:00:00"
            from_ts, to_ts = parse_time_range(iso_from, "now")

            expected_from = datetime.fromisoformat(iso_from)
            assert from_ts == int(expected_from.timestamp())
            assert to_ts == int(mock_now.timestamp())

            # From relative to ISO
            iso_to = "2026-02-11T10:00:00"
            from_ts, to_ts = parse_time_range("1h", iso_to)

            expected_from = mock_now - timedelta(hours=1)
            expected_to = datetime.fromisoformat(iso_to)
            assert from_ts == int(expected_from.timestamp())
            assert to_ts == int(expected_to.timestamp())

    def test_default_to_parameter(self, mock_now):
        """Test that 'to' parameter defaults to 'now'."""
        with patch("ddg.utils.time.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            # Only provide 'from', 'to' should default to 'now'
            from_ts, to_ts = parse_time_range("1h")

            expected_from = mock_now - timedelta(hours=1)
            assert from_ts == int(expected_from.timestamp())
            assert to_ts == int(mock_now.timestamp())

    def test_large_time_values(self, mock_now):
        """Test edge cases with large time values."""
        with patch("ddg.utils.time.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            # 365 days (1 year)
            from_ts, to_ts = parse_time_range("365d", "now")
            expected_from = mock_now - timedelta(days=365)
            assert from_ts == int(expected_from.timestamp())

            # 8760 hours (1 year)
            from_ts, to_ts = parse_time_range("8760h", "now")
            expected_from = mock_now - timedelta(hours=8760)
            assert from_ts == int(expected_from.timestamp())

    def test_zero_values(self, mock_now):
        """Test edge case with zero time values."""
        with patch("ddg.utils.time.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            # 0 hours ago (equivalent to now)
            from_ts, to_ts = parse_time_range("0h", "now")
            assert from_ts == int(mock_now.timestamp())
            assert to_ts == int(mock_now.timestamp())

    def test_invalid_format_raises_error(self):
        """Test that invalid formats raise ValueError."""
        # Invalid unit
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time_range("1y")  # 'y' for year not supported

        # Invalid pattern
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time_range("abc")

        # Missing unit
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time_range("10")

        # Invalid ISO format
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time_range("2026-99-99")

    def test_malformed_relative_time(self):
        """Test various malformed relative time strings."""
        invalid_inputs = [
            "h1",  # Wrong order
            "1",  # Missing unit
            "1hh",  # Double unit
            "-1h",  # Negative (not supported in regex)
            "1.5h",  # Decimal (not supported in regex)
            "1 h",  # Space not allowed
        ]

        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError, match="Invalid time format"):
                parse_time_range(invalid_input)

    def test_time_range_order(self, mock_now):
        """Test that from_ts can be greater than to_ts (no validation enforced)."""
        with patch("ddg.utils.time.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            # 'from' is in the future relative to 'to' (now vs 1h ago)
            # Function doesn't validate order, just parses
            from_ts, to_ts = parse_time_range("now", "1h")

            expected_from = mock_now
            expected_to = mock_now - timedelta(hours=1)

            assert from_ts == int(expected_from.timestamp())
            assert to_ts == int(expected_to.timestamp())
            # from_ts > to_ts in this case (no error raised)
            assert from_ts > to_ts

    def test_timestamp_precision(self, mock_now):
        """Test that timestamps are returned as integers (no fractional seconds)."""
        with patch("ddg.utils.time.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            from_ts, to_ts = parse_time_range("1h", "now")

            assert isinstance(from_ts, int)
            assert isinstance(to_ts, int)

    def test_multiple_digit_values(self, mock_now):
        """Test parsing of multi-digit time values."""
        with patch("ddg.utils.time.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            # 100 hours
            from_ts, to_ts = parse_time_range("100h", "now")
            expected_from = mock_now - timedelta(hours=100)
            assert from_ts == int(expected_from.timestamp())

            # 999 days
            from_ts, to_ts = parse_time_range("999d", "now")
            expected_from = mock_now - timedelta(days=999)
            assert from_ts == int(expected_from.timestamp())
