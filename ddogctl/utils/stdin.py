"""Stdin input utilities for composable piping."""

import json
import sys

import click


def read_stdin_json():
    """Read JSON from stdin.

    Returns:
        Parsed JSON data (dict or list of dicts).

    Raises:
        click.ClickException: If stdin is empty or not valid JSON.
    """
    if sys.stdin.isatty():
        raise click.ClickException("No input on stdin. Pipe JSON data or use -f <file>.")

    data = sys.stdin.read().strip()
    if not data:
        raise click.ClickException("Empty stdin input.")

    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON on stdin: {e}")


def stdin_option(func):
    """Decorator that adds --from-stdin option to a Click command."""
    return click.option(
        "--from-stdin",
        "from_stdin",
        is_flag=True,
        default=False,
        help="Read JSON input from stdin (for piping).",
    )(func)
