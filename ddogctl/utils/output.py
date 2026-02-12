"""Output format utilities."""

import json
import sys

# Global output format state
_output_format = "table"


def set_output_format(fmt: str) -> None:
    """Set the global output format."""
    global _output_format
    _output_format = fmt


def get_output_format() -> str:
    """Get the current output format."""
    return _output_format


def emit_error(code: str, status: int, message: str, hint: str = "") -> None:
    """Emit an error in the appropriate format.

    In JSON mode, outputs structured JSON to stderr.
    In table mode, uses Rich console for pretty output.
    """
    if _output_format == "json":
        error_obj = {
            "error": True,
            "code": code,
            "status": status,
            "message": message,
        }
        if hint:
            error_obj["hint"] = hint
        print(json.dumps(error_obj), file=sys.stderr)
    else:
        from rich.console import Console

        console = Console(stderr=True)
        console.print(f"[red]{message}[/red]")
        if hint:
            console.print(f"[dim]{hint}[/dim]")
