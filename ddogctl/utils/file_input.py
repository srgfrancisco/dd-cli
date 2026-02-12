"""JSON file input parsing utility for -f/--file options."""

import json
from pathlib import Path

import click


def load_json_file(file_path: str) -> dict | list:
    """Load and parse a JSON file.

    Args:
        file_path: Path to JSON file.

    Returns:
        Parsed JSON data (dict or list).

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file contains invalid JSON.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    text = path.read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")


def load_json_option(ctx, param, value) -> dict | list | None:
    """Click callback for -f/--file option that loads JSON.

    Usage:
        @click.option("-f", "--file", callback=load_json_option, expose_value=True)

    Returns:
        Parsed JSON data, or None if no file specified.

    Raises:
        click.BadParameter: If file not found or contains invalid JSON.
    """
    if value is None:
        return None

    try:
        return load_json_file(value)
    except FileNotFoundError:
        raise click.BadParameter(f"File not found: {value}")
    except ValueError as e:
        raise click.BadParameter(str(e))
