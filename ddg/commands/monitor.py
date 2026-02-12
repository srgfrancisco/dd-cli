"""Monitor management commands."""

import click
import json
import sys
from rich.console import Console
from rich.table import Table
from ddg.client import get_datadog_client
from ddg.utils.error import handle_api_error

console = Console()


@click.group()
def monitor():
    """Monitor management commands."""
    pass


@monitor.command(name="list")
@click.option("--tags", help="Filter by tags (comma-separated)")
@click.option(
    "--state",
    type=click.Choice(["Alert", "Warn", "OK", "No Data"]),
    multiple=True,
    help="Filter by state",
)
@click.option(
    "--format",
    type=click.Choice(["json", "table", "markdown"]),
    default="table",
    help="Output format",
)
@handle_api_error
def list_monitors(tags, state, format):
    """List all monitors (equivalent to dogshell's show_all)."""
    client = get_datadog_client()

    with console.status("[cyan]Fetching monitors...[/cyan]"):
        # Build kwargs only with provided parameters
        kwargs = {}
        if tags:
            kwargs["tags"] = tags

        monitors = client.monitors.list_monitors(**kwargs)

    # Filter by state if specified
    if state:
        monitors = [m for m in monitors if str(m.overall_state) in state]

    if format == "table":
        table = Table(title="Datadog Monitors", show_lines=False)
        table.add_column("ID", style="cyan", width=10)
        table.add_column("State", style="bold", width=10)
        table.add_column("Name", style="white", min_width=30)
        table.add_column("Tags", style="dim", width=30)

        for m in monitors:
            # Convert state to string for comparison
            state_str = str(m.overall_state) if m.overall_state else "Unknown"
            state_color = {
                "Alert": "red",
                "Warn": "yellow",
                "OK": "green",
                "No Data": "dim",
            }.get(state_str, "white")

            # Truncate tags for display
            tag_display = ", ".join(m.tags[:3]) if m.tags else ""
            if m.tags and len(m.tags) > 3:
                tag_display += f", +{len(m.tags) - 3} more"

            table.add_row(
                str(m.id),
                f"[{state_color}]{state_str}[/{state_color}]",
                m.name[:60] if m.name else "",
                tag_display,
            )

        console.print(table)
        console.print(f"\n[dim]Total monitors: {len(monitors)}[/dim]")

    elif format == "json":
        print(json.dumps([m.to_dict() for m in monitors], indent=2, default=str))

    elif format == "markdown":
        print("| ID | State | Name |")
        print("|---|---|---|")
        for m in monitors:
            print(f"| {m.id} | {m.overall_state} | {m.name} |")


@monitor.command(name="get")
@click.argument("monitor_id", type=int)
@click.option(
    "--format", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def get_monitor(monitor_id, format):
    """Get monitor details (equivalent to dogshell's show)."""
    client = get_datadog_client()

    with console.status(f"[cyan]Fetching monitor {monitor_id}...[/cyan]"):
        mon = client.monitors.get_monitor(monitor_id)

    if format == "table":
        console.print(f"\n[bold cyan]Monitor #{mon.id}[/bold cyan]")
        console.print(f"[bold]Name:[/bold] {mon.name}")
        console.print(f"[bold]Type:[/bold] {mon.type}")

        # Convert state to string
        state_str = str(mon.overall_state) if mon.overall_state else "Unknown"
        state_color = {
            "Alert": "red",
            "Warn": "yellow",
            "OK": "green",
            "No Data": "dim",
        }.get(state_str, "white")
        console.print(f"[bold]State:[/bold] [{state_color}]{state_str}[/{state_color}]")

        console.print(f"[bold]Query:[/bold] {mon.query}")

        if mon.message:
            console.print(f"[bold]Message:[/bold]\n{mon.message}")

        if mon.tags:
            console.print(f"[bold]Tags:[/bold] {', '.join(mon.tags)}")

        if hasattr(mon, "created") and mon.created:
            console.print(f"[bold]Created:[/bold] {mon.created}")

        if hasattr(mon, "modified") and mon.modified:
            console.print(f"[bold]Modified:[/bold] {mon.modified}")

    elif format == "json":
        print(json.dumps(mon.to_dict(), indent=2, default=str))


@monitor.command(name="mute")
@click.argument("monitor_id", type=int)
@click.option("--scope", help="Scope to mute (e.g., host:myhost)")
@click.option("--duration", type=int, help="Mute duration in seconds")
@handle_api_error
def mute_monitor(monitor_id, scope, duration):
    """Mute a monitor."""
    import time

    client = get_datadog_client()

    mute_options = {}
    if scope:
        mute_options["scope"] = scope
    if duration:
        mute_options["end"] = int(time.time()) + duration

    with console.status(f"[cyan]Muting monitor {monitor_id}...[/cyan]"):
        from datadog_api_client.v1.model.monitor_update_request import MonitorUpdateRequest

        client.monitors.update_monitor(monitor_id, body=MonitorUpdateRequest(**mute_options))

    console.print(f"[green]✓ Monitor {monitor_id} muted[/green]")
    if duration:
        console.print(f"[dim]Muted for {duration} seconds[/dim]")


@monitor.command(name="unmute")
@click.argument("monitor_id", type=int)
@click.option("--scope", help="Scope to unmute")
@handle_api_error
def unmute_monitor(monitor_id, scope):
    """Unmute a monitor."""
    client = get_datadog_client()

    unmute_options = {}
    if scope:
        unmute_options["scope"] = scope

    with console.status(f"[cyan]Unmuting monitor {monitor_id}...[/cyan]"):
        from datadog_api_client.v1.model.monitor_update_request import MonitorUpdateRequest

        client.monitors.update_monitor(monitor_id, body=MonitorUpdateRequest(**unmute_options))

    console.print(f"[green]✓ Monitor {monitor_id} unmuted[/green]")


@monitor.command(name="validate")
@click.option("--type", "monitor_type", required=True, help="Monitor type (e.g., metric alert)")
@click.option("--query", required=True, help="Monitor query")
@handle_api_error
def validate_monitor(monitor_type, query):
    """Validate a monitor definition (equivalent to dogshell's validate)."""
    client = get_datadog_client()

    with console.status("[cyan]Validating monitor...[/cyan]"):
        from datadog_api_client.v1.model.monitor import Monitor

        monitor_def = Monitor(type=monitor_type, query=query)
        result = client.monitors.validate_monitor(body=monitor_def)

    # Check if result has errors
    if hasattr(result, "errors") and result.errors:
        console.print("[red]✗ Monitor definition is invalid[/red]")
        for error in result.errors:
            console.print(f"  • {error}")
        sys.exit(1)
    else:
        console.print("[green]✓ Monitor definition is valid[/green]")
