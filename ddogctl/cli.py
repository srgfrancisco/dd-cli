"""Main CLI entry point for Datadog CLI."""

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def main():
    """A modern CLI for the Datadog API. Like Dogshell, but better.

    Query monitors, metrics, events, hosts, APM traces, logs, and more
    from your terminal with rich output and smart defaults.

    Configuration:
        DD_API_KEY - Datadog API key (required)
        DD_APP_KEY - Datadog Application key (required)
        DD_SITE - Datadog site (default: datadoghq.com)

    Examples:
        ddogctl monitor list --state Alert
        ddogctl apm traces my-service --from 1h
        ddogctl logs search "status:error" --service my-api
    """
    pass


# Import and register all command groups
# ruff: noqa: E402
from ddogctl.commands.monitor import monitor
from ddogctl.commands.metric import metric
from ddogctl.commands.event import event
from ddogctl.commands.host import host
from ddogctl.commands.apm import apm
from ddogctl.commands.logs import logs
from ddogctl.commands.dbm import dbm
from ddogctl.commands.investigate import investigate
from ddogctl.commands.service_check import service_check

main.add_command(monitor)
main.add_command(metric)
main.add_command(event)
main.add_command(host)
main.add_command(apm)
main.add_command(logs)
main.add_command(dbm)
main.add_command(investigate)
main.add_command(service_check)


if __name__ == "__main__":
    main()
