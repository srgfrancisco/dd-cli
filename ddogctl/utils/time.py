"""Time parsing utilities."""

from datetime import datetime, timedelta
import re


def parse_time_range(from_str: str, to_str: str = "now") -> tuple[int, int]:
    """Parse time range strings to Unix timestamps.

    Supported formats:
    - "now"
    - "1h" (1 hour ago)
    - "24h" (24 hours ago)
    - "7d" (7 days ago)
    - "2026-02-10T10:00:00" (ISO datetime)

    Returns:
        Tuple of (from_timestamp, to_timestamp)
    """
    now = datetime.now()

    def parse_relative(s: str) -> datetime:
        if s == "now":
            return now

        # Match patterns like "1h", "24h", "7d", "30m"
        match = re.match(r"^(\d+)([hdm])$", s)
        if match:
            value = int(match.group(1))
            unit = match.group(2)

            if unit == "h":
                return now - timedelta(hours=value)
            elif unit == "d":
                return now - timedelta(days=value)
            elif unit == "m":
                return now - timedelta(minutes=value)

        # Try parsing as ISO datetime
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            raise ValueError(f"Invalid time format: {s}")

    from_dt = parse_relative(from_str)
    to_dt = parse_relative(to_str)

    return int(from_dt.timestamp()), int(to_dt.timestamp())
