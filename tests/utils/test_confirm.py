"""Tests for confirmation utility for destructive operations."""

import click
from click.testing import CliRunner

from ddogctl.utils.confirm import confirm_action


class TestConfirmAction:
    """Tests for confirm_action()."""

    def test_skips_prompt_when_confirm_flag_set(self):
        """When --confirm is passed, skip the prompt and return True."""
        assert confirm_action("Delete monitor 123?", confirmed=True) is True

    def test_prompts_user_when_confirm_flag_not_set(self):
        """When --confirm not passed, prompt user for confirmation."""

        @click.command()
        def cmd():
            result = confirm_action("Delete monitor 123?", confirmed=False)
            if result:
                click.echo("confirmed")
            else:
                click.echo("cancelled")

        runner = CliRunner()
        # User types 'y'
        result = runner.invoke(cmd, input="y\n")
        assert "confirmed" in result.output

    def test_user_declines_confirmation(self):
        """When user types 'n', return False."""

        @click.command()
        def cmd():
            result = confirm_action("Delete monitor 123?", confirmed=False)
            if result:
                click.echo("confirmed")
            else:
                click.echo("cancelled")

        runner = CliRunner()
        result = runner.invoke(cmd, input="n\n")
        assert "cancelled" in result.output

    def test_prompt_message_is_shown(self):
        """The confirmation message should appear in the output."""

        @click.command()
        def cmd():
            confirm_action("Are you sure you want to delete this?", confirmed=False)

        runner = CliRunner()
        result = runner.invoke(cmd, input="n\n")
        assert "Are you sure you want to delete this?" in result.output
