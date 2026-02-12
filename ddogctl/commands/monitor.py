"""Monitor management commands."""

import click
import json
import sys
from datetime import datetime
from rich.console import Console
from rich.table import Table
from ddogctl.client import get_datadog_client
from ddogctl.utils.error import handle_api_error
from ddogctl.utils.file_input import load_json_option
from ddogctl.utils.confirm import confirm_action
from ddogctl.utils.stdin import read_stdin_json, stdin_option
from ddogctl.utils.watch import watch_loop

console = Console()


@click.group()
def monitor():
    """Monitor management commands."""
    pass


def _build_monitor_table(monitors):
    """Build a Rich table from a list of monitor objects.

    Args:
        monitors: List of Datadog monitor objects.

    Returns:
        Rich Table renderable.
    """
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

    return table


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
@click.option("--watch", is_flag=True, default=False, help="Auto-refresh at intervals")
@click.option("--interval", type=int, default=30, help="Refresh interval in seconds (default: 30)")
@handle_api_error
def list_monitors(tags, state, format, watch, interval):
    """List all monitors (equivalent to dogshell's show_all)."""
    client = get_datadog_client()

    def fetch_monitors():
        """Fetch and filter monitors from the API."""
        kwargs = {}
        if tags:
            kwargs["tags"] = tags
        monitors = client.monitors.list_monitors(**kwargs)
        if state:
            monitors = [m for m in monitors if str(m.overall_state) in state]
        return monitors

    if watch:

        def render():
            monitors = fetch_monitors()
            table = _build_monitor_table(monitors)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            from rich.console import Group

            return Group(
                table,
                f"\n[dim]Total monitors: {len(monitors)} | Last refresh: {now}[/dim]",
            )

        watch_loop(render, interval=interval, console=console)
    else:
        with console.status("[cyan]Fetching monitors...[/cyan]"):
            monitors = fetch_monitors()

        if format == "table":
            table = _build_monitor_table(monitors)
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
@click.argument("monitor_id", type=int, required=False, default=None)
@click.option("--scope", help="Scope to mute (e.g., host:myhost)")
@click.option("--duration", type=int, help="Mute duration in seconds")
@stdin_option
@handle_api_error
def mute_monitor(monitor_id, scope, duration, from_stdin):
    """Mute a monitor or multiple monitors from stdin.

    Examples:
        ddogctl monitor mute 12345
        ddogctl monitor mute 12345 --duration 3600
        ddogctl monitor list --state Alert --format json | ddogctl monitor mute --from-stdin
    """
    import time

    client = get_datadog_client()

    if from_stdin:
        data = read_stdin_json()
        # Accept a list of objects with 'id' field or a single object
        if isinstance(data, dict):
            data = [data]

        if not data:
            raise click.ClickException("No monitors to mute in stdin input.")

        mute_options = {}
        if scope:
            mute_options["scope"] = scope
        if duration:
            mute_options["end"] = int(time.time()) + duration

        from datadog_api_client.v1.model.monitor_update_request import MonitorUpdateRequest

        muted_count = 0
        for item in data:
            mid = item.get("id") if isinstance(item, dict) else item
            if mid is None:
                console.print("[yellow]Skipping item without 'id' field[/yellow]")
                continue
            with console.status(f"[cyan]Muting monitor {mid}...[/cyan]"):
                client.monitors.update_monitor(int(mid), body=MonitorUpdateRequest(**mute_options))
            console.print(f"[green]Monitor {mid} muted[/green]")
            muted_count += 1

        console.print(f"\n[bold green]{muted_count} monitor(s) muted[/bold green]")
        return

    if monitor_id is None:
        raise click.UsageError("Missing argument 'MONITOR_ID' (required without --from-stdin)")

    mute_options = {}
    if scope:
        mute_options["scope"] = scope
    if duration:
        mute_options["end"] = int(time.time()) + duration

    with console.status(f"[cyan]Muting monitor {monitor_id}...[/cyan]"):
        from datadog_api_client.v1.model.monitor_update_request import MonitorUpdateRequest

        client.monitors.update_monitor(monitor_id, body=MonitorUpdateRequest(**mute_options))

    console.print(f"[green]Monitor {monitor_id} muted[/green]")
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


@monitor.command(name="create")
@click.option("--type", "monitor_type", default=None, help="Monitor type (e.g., metric alert)")
@click.option("--query", default=None, help="Monitor query")
@click.option("--name", default=None, help="Monitor name")
@click.option("--message", default=None, help="Monitor notification message")
@click.option("--tags", default=None, help="Tags (comma-separated)")
@click.option("--priority", type=int, default=None, help="Monitor priority (1-5)")
@click.option(
    "-f",
    "--file",
    "file_data",
    callback=load_json_option,
    default=None,
    help="JSON file with monitor definition",
)
@stdin_option
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format",
)
@handle_api_error
def create_monitor_cmd(
    monitor_type, query, name, message, tags, priority, file_data, from_stdin, fmt
):
    """Create a monitor from inline flags, a JSON file, or stdin.

    Examples:
        ddogctl monitor create --type "metric alert" --query "..." --name "CPU Alert"
        ddogctl monitor create -f monitor.json
        echo '{"type":"metric alert","query":"...","name":"CPU"}' | ddogctl monitor create --from-stdin
    """
    from datadog_api_client.v1.model.monitor import Monitor

    if from_stdin:
        file_data = read_stdin_json()

    if file_data:
        # File takes precedence over inline flags
        monitor_body = Monitor(**file_data)
    else:
        # Validate required inline flags
        if not monitor_type:
            raise click.UsageError("Missing option '--type' (required without -f)")
        if not query:
            raise click.UsageError("Missing option '--query' (required without -f)")
        if not name:
            raise click.UsageError("Missing option '--name' (required without -f)")

        kwargs = {"type": monitor_type, "query": query, "name": name}
        if message:
            kwargs["message"] = message
        if tags:
            kwargs["tags"] = [t.strip() for t in tags.split(",")]
        if priority is not None:
            kwargs["priority"] = priority

        monitor_body = Monitor(**kwargs)

    client = get_datadog_client()

    with console.status("[cyan]Creating monitor...[/cyan]"):
        result = client.monitors.create_monitor(body=monitor_body)

    if fmt == "json":
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        console.print(f"[green]✓ Monitor {result.id} created[/green]")
        console.print(f"[bold]Name:[/bold] {result.name}")


@monitor.command(name="update")
@click.argument("monitor_id", type=int)
@click.option("--name", default=None, help="Monitor name")
@click.option("--query", default=None, help="Monitor query")
@click.option("--message", default=None, help="Monitor notification message")
@click.option("--tags", default=None, help="Tags (comma-separated)")
@click.option("--priority", type=int, default=None, help="Monitor priority (1-5)")
@click.option(
    "-f",
    "--file",
    "file_data",
    callback=load_json_option,
    default=None,
    help="JSON file with monitor update definition",
)
@stdin_option
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format",
)
@handle_api_error
def update_monitor_cmd(
    monitor_id, name, query, message, tags, priority, file_data, from_stdin, fmt
):
    """Update a monitor by ID from inline flags, a JSON file, or stdin.

    Examples:
        ddogctl monitor update 12345 --name "New Name"
        ddogctl monitor update 12345 -f update.json
        echo '{"name":"New Name"}' | ddogctl monitor update 12345 --from-stdin
    """
    from datadog_api_client.v1.model.monitor_update_request import MonitorUpdateRequest

    if from_stdin:
        file_data = read_stdin_json()

    if file_data:
        update_body = MonitorUpdateRequest(**file_data)
    else:
        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if query is not None:
            kwargs["query"] = query
        if message is not None:
            kwargs["message"] = message
        if tags is not None:
            kwargs["tags"] = [t.strip() for t in tags.split(",")]
        if priority is not None:
            kwargs["priority"] = priority

        if not kwargs:
            raise click.UsageError("No update fields specified. Use flags or -f file.json")

        update_body = MonitorUpdateRequest(**kwargs)

    client = get_datadog_client()

    with console.status(f"[cyan]Updating monitor {monitor_id}...[/cyan]"):
        result = client.monitors.update_monitor(monitor_id, body=update_body)

    if fmt == "json":
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        console.print(f"[green]✓ Monitor {monitor_id} updated[/green]")
        console.print(f"[bold]Name:[/bold] {result.name}")


@monitor.command(name="delete")
@click.argument("monitor_id", type=int)
@click.option("--confirm", "confirmed", is_flag=True, help="Skip confirmation prompt")
@handle_api_error
def delete_monitor_cmd(monitor_id, confirmed):
    """Delete a monitor by ID."""
    if not confirm_action(f"Delete monitor {monitor_id}?", confirmed):
        console.print("[yellow]Aborted[/yellow]")
        return

    client = get_datadog_client()

    with console.status(f"[cyan]Deleting monitor {monitor_id}...[/cyan]"):
        client.monitors.delete_monitor(monitor_id)

    console.print(f"[green]✓ Monitor {monitor_id} deleted[/green]")


@monitor.command(name="mute-all")
@click.option("--message", default=None, help="Downtime message")
@handle_api_error
def mute_all_monitors(message):
    """Mute all monitors by creating a global downtime (scope: *)."""
    from datadog_api_client.v1.model.downtime import Downtime

    client = get_datadog_client()

    kwargs = {"scope": ["*"]}
    if message:
        kwargs["message"] = message

    downtime_body = Downtime(**kwargs)

    with console.status("[cyan]Muting all monitors...[/cyan]"):
        result = client.downtimes.create_downtime(body=downtime_body)

    console.print("[green]✓ All monitors muted[/green]")
    console.print(f"[dim]Downtime ID: {result.id}[/dim]")


@monitor.command(name="unmute-all")
@handle_api_error
def unmute_all_monitors():
    """Unmute all monitors by cancelling global downtimes (scope: *)."""
    client = get_datadog_client()

    with console.status("[cyan]Finding global downtimes...[/cyan]"):
        downtimes = client.downtimes.list_downtimes()

    # Filter for active global downtimes (scope: ["*"])
    global_downtimes = [d for d in downtimes if d.scope == ["*"] and not d.disabled]

    if not global_downtimes:
        console.print("[yellow]No global downtimes found[/yellow]")
        return

    for dt in global_downtimes:
        with console.status(f"[cyan]Cancelling downtime {dt.id}...[/cyan]"):
            client.downtimes.cancel_downtime(dt.id)

    console.print(
        f"[green]✓ All monitors unmuted ({len(global_downtimes)} downtime(s) cancelled)[/green]"
    )
