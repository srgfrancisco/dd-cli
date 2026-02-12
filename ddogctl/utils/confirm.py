"""Confirmation utility for destructive operations."""

import click


def confirm_action(message: str, confirmed: bool = False) -> bool:
    """Prompt user for confirmation unless --confirm flag was set.

    Args:
        message: Confirmation message to display.
        confirmed: Whether --confirm flag was passed (skip prompt).

    Returns:
        True if confirmed, False if declined.
    """
    if confirmed:
        return True

    return click.confirm(message)
