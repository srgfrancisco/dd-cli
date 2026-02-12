"""Main CLI entry point for Datadog CLI."""

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """A modern CLI for the Datadog API. Like Dogshell, but better.

    Query monitors, metrics, events, hosts, APM traces, logs, and more
    from your terminal with rich output and smart defaults.

    Configuration:
        DD_API_KEY - Datadog API key (required)
        DD_APP_KEY - Datadog Application key (required)
        DD_SITE - Datadog site (default: datadoghq.com)

    Examples:
        ddg monitor list --state Alert
        ddg apm traces my-service --from 1h
        ddg logs search "status:error" --service my-api
    """
    pass


# Import and register all command groups
from ddg.commands.monitor import monitor
from ddg.commands.metric import metric
from ddg.commands.event import event
from ddg.commands.host import host
from ddg.commands.apm import apm

main.add_command(monitor)
main.add_command(metric)
main.add_command(event)
main.add_command(host)
main.add_command(apm)


if __name__ == "__main__":
    main()
