"""Host management commands."""

import click
import json
from rich.console import Console
from rich.table import Table
from ddg.client import get_datadog_client
from ddg.utils.error import handle_api_error

console = Console()


@click.group()
def host():
    """Host management commands."""
    pass


@host.command(name="list")
@click.option("--filter", help="Filter hosts (e.g., service:web)")
@click.option("--limit", default=100, help="Maximum hosts to show")
@click.option(
    "--format", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def list_hosts(filter, limit, format):
    """List hosts."""
    client = get_datadog_client()

    kwargs = {"count": limit}
    if filter:
        kwargs["filter"] = filter

    with console.status("[cyan]Fetching hosts...[/cyan]"):
        result = client.hosts.list_hosts(**kwargs)

    if not result.host_list:
        console.print("[yellow]No hosts found[/yellow]")
        return

    if format == "table":
        table = Table(title="Datadog Hosts", show_lines=False)
        table.add_column("Name", style="cyan", min_width=30)
        table.add_column("Status", style="bold", width=10)
        table.add_column("Apps", style="dim", width=30)
        table.add_column("Last Reported", style="yellow", width=20)

        for h in result.host_list:
            # Status with color
            is_up = getattr(h, "is_up", False)
            status = "[green]UP[/green]" if is_up else "[red]DOWN[/red]"

            # Apps running on host
            apps = ", ".join(getattr(h, "apps", [])[:3]) if hasattr(h, "apps") else ""
            if hasattr(h, "apps") and len(h.apps) > 3:
                apps += f", +{len(h.apps) - 3} more"

            # Last reported time
            from datetime import datetime

            last_reported = ""
            if hasattr(h, "last_reported_time") and h.last_reported_time:
                dt = datetime.fromtimestamp(h.last_reported_time)
                last_reported = dt.strftime("%Y-%m-%d %H:%M")

            table.add_row(h.name, status, apps, last_reported)

        console.print(table)
        console.print(f"\n[dim]Total hosts: {result.total_matching}[/dim]")

    elif format == "json":
        print(json.dumps(result.to_dict(), indent=2, default=str))


@host.command(name="get")
@click.argument("hostname")
@click.option(
    "--format", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def get_host(hostname, format):
    """Get host details."""
    client = get_datadog_client()

    with console.status(f"[cyan]Fetching host {hostname}...[/cyan]"):
        # Use list with filter to get specific host
        result = client.hosts.list_hosts(filter=f"host:{hostname}")

    if not result.host_list:
        console.print(f"[red]Host not found: {hostname}[/red]")
        return

    host = result.host_list[0]

    if format == "table":
        console.print(f"\n[bold cyan]Host: {host.name}[/bold cyan]")

        is_up = getattr(host, "is_up", False)
        status = "[green]UP[/green]" if is_up else "[red]DOWN[/red]"
        console.print(f"[bold]Status:[/bold] {status}")

        if hasattr(host, "apps") and host.apps:
            console.print(f"[bold]Apps:[/bold] {', '.join(host.apps)}")

        if hasattr(host, "host_name"):
            console.print(f"[bold]Hostname:[/bold] {host.host_name}")

        if hasattr(host, "last_reported_time") and host.last_reported_time:
            from datetime import datetime

            dt = datetime.fromtimestamp(host.last_reported_time)
            console.print(f"[bold]Last Reported:[/bold] {dt.strftime('%Y-%m-%d %H:%M:%S')}")

        if hasattr(host, "tags_by_source") and host.tags_by_source:
            console.print("\n[bold]Tags:[/bold]")
            for source, tags in host.tags_by_source.items():
                console.print(f"  [dim]{source}:[/dim] {', '.join(tags[:5])}")

    elif format == "json":
        print(json.dumps(host.to_dict(), indent=2, default=str))


@host.command(name="totals")
@handle_api_error
def host_totals():
    """Get host totals summary."""
    client = get_datadog_client()

    with console.status("[cyan]Fetching host totals...[/cyan]"):
        totals = client.hosts.get_host_totals()

    console.print("\n[bold cyan]Host Totals[/bold cyan]")
    console.print(f"[bold]Total Active:[/bold] {totals.total_active}")
    console.print(f"[bold]Total Up:[/bold] {totals.total_up}")

    if hasattr(totals, "total_down"):
        console.print(f"[bold]Total Down:[/bold] {totals.total_down}")
