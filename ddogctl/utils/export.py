"""Export utility for writing data to JSON files."""

import json
from pathlib import Path


def export_to_json(data: dict | list, file_path: str) -> None:
    """Export data to a pretty-printed JSON file.

    Creates parent directories if they don't exist.

    Args:
        data: Data to export (dict or list).
        file_path: Output file path.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n")
