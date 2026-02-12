"""Dashboard management commands."""

import click
import json
from rich.console import Console
from rich.table import Table
from ddogctl.client import get_datadog_client
from ddogctl.utils.error import handle_api_error
from ddogctl.utils.file_input import load_json_option
from ddogctl.utils.confirm import confirm_action
from ddogctl.utils.export import export_to_json

console = Console()


@click.group()
def dashboard():
    """Dashboard management commands."""
    pass


@dashboard.command(name="list")
@click.option("--tags", help="Filter by tags (comma-separated)")
@click.option(
    "--format", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def list_dashboards(tags, format):
    """List all dashboards."""
    client = get_datadog_client()

    kwargs = {}
    if tags:
        kwargs["filter_configured"] = tags

    with console.status("[cyan]Fetching dashboards...[/cyan]"):
        response = client.dashboards.list_dashboards(**kwargs)

    dashboards_list = response.dashboards or []

    if format == "json":
        output = []
        for d in dashboards_list:
            output.append(
                {
                    "id": d.id,
                    "title": d.title,
                    "layout_type": str(d.layout_type),
                    "author_handle": getattr(d, "author_handle", ""),
                    "created_at": str(getattr(d, "created_at", "")),
                    "url": getattr(d, "url", ""),
                }
            )
        print(json.dumps(output, indent=2, default=str))
    else:
        table = Table(title="Dashboards", show_lines=False)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="white", min_width=30)
        table.add_column("Layout", style="dim", width=10)
        table.add_column("Author", style="dim")

        for d in dashboards_list:
            table.add_row(
                str(d.id),
                str(d.title),
                str(getattr(d, "layout_type", "")),
                str(getattr(d, "author_handle", "")),
            )

        console.print(table)
        console.print(f"\n[dim]Total dashboards: {len(dashboards_list)}[/dim]")


@dashboard.command(name="get")
@click.argument("dashboard_id")
@click.option(
    "--format", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def get_dashboard(dashboard_id, format):
    """Get dashboard details."""
    client = get_datadog_client()

    with console.status(f"[cyan]Fetching dashboard {dashboard_id}...[/cyan]"):
        dash = client.dashboards.get_dashboard(dashboard_id)

    if format == "json":
        print(json.dumps(dash.to_dict(), indent=2, default=str))
    else:
        console.print(f"\n[bold cyan]Dashboard {dash.id}[/bold cyan]")
        console.print(f"[bold]Title:[/bold] {dash.title}")
        console.print(f"[bold]Layout:[/bold] {dash.layout_type}")

        if hasattr(dash, "description") and dash.description:
            console.print(f"[bold]Description:[/bold] {dash.description}")

        if hasattr(dash, "author_handle") and dash.author_handle:
            console.print(f"[bold]Author:[/bold] {dash.author_handle}")

        if hasattr(dash, "created_at") and dash.created_at:
            console.print(f"[bold]Created:[/bold] {dash.created_at}")

        if hasattr(dash, "url") and dash.url:
            console.print(f"[bold]URL:[/bold] {dash.url}")

        widget_count = len(dash.widgets) if hasattr(dash, "widgets") and dash.widgets else 0
        console.print(f"[bold]Widgets:[/bold] {widget_count}")


@dashboard.command(name="create")
@click.option("--title", default=None, help="Dashboard title")
@click.option(
    "--layout-type",
    type=click.Choice(["ordered", "free"]),
    default=None,
    help="Layout type (ordered=grid, free=freeform)",
)
@click.option("--description", default=None, help="Dashboard description")
@click.option(
    "-f",
    "--file",
    "file_data",
    callback=load_json_option,
    default=None,
    help="JSON file with dashboard definition",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format",
)
@handle_api_error
def create_dashboard_cmd(title, layout_type, description, file_data, fmt):
    """Create a dashboard from a JSON file or inline flags.

    From file (primary workflow):
        ddogctl dashboard create -f dashboard.json

    With inline flags (metadata only, no widgets):
        ddogctl dashboard create --title "My Dashboard" --layout-type ordered
    """
    if file_data:
        body = file_data
    else:
        if not title:
            raise click.UsageError("Missing option '--title' (required without -f)")
        if not layout_type:
            raise click.UsageError("Missing option '--layout-type' (required without -f)")

        body = {
            "title": title,
            "layout_type": layout_type,
            "widgets": [],
        }
        if description:
            body["description"] = description

    client = get_datadog_client()

    with console.status("[cyan]Creating dashboard...[/cyan]"):
        result = client.dashboards.create_dashboard(body=body)

    if fmt == "json":
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        console.print(f"[green]Dashboard {result.id} created[/green]")
        console.print(f"[bold]Title:[/bold] {result.title}")


@dashboard.command(name="update")
@click.argument("dashboard_id")
@click.option(
    "-f",
    "--file",
    "file_data",
    callback=load_json_option,
    default=None,
    help="JSON file with dashboard definition",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format",
)
@handle_api_error
def update_dashboard_cmd(dashboard_id, file_data, fmt):
    """Update a dashboard by ID from a JSON file.

    Usage:
        ddogctl dashboard update <dashboard_id> -f dashboard.json
    """
    if not file_data:
        raise click.UsageError("Missing option '-f' / '--file' (required for update)")

    client = get_datadog_client()

    with console.status(f"[cyan]Updating dashboard {dashboard_id}...[/cyan]"):
        result = client.dashboards.update_dashboard(dashboard_id, body=file_data)

    if fmt == "json":
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        console.print(f"[green]Dashboard {dashboard_id} updated[/green]")
        console.print(f"[bold]Title:[/bold] {result.title}")


@dashboard.command(name="delete")
@click.argument("dashboard_id")
@click.option("--confirm", "confirmed", is_flag=True, help="Skip confirmation prompt")
@handle_api_error
def delete_dashboard_cmd(dashboard_id, confirmed):
    """Delete a dashboard by ID."""
    if not confirm_action(f"Delete dashboard {dashboard_id}?", confirmed):
        console.print("[yellow]Aborted[/yellow]")
        return

    client = get_datadog_client()

    with console.status(f"[cyan]Deleting dashboard {dashboard_id}...[/cyan]"):
        client.dashboards.delete_dashboard(dashboard_id)

    console.print(f"[green]Dashboard {dashboard_id} deleted[/green]")


@dashboard.command(name="export")
@click.argument("dashboard_id")
@click.option(
    "-o",
    "--output",
    "output_file",
    required=True,
    help="Output JSON file path",
)
@handle_api_error
def export_dashboard_cmd(dashboard_id, output_file):
    """Export a dashboard to a JSON file.

    Useful for the export -> modify -> apply GitOps workflow.
    """
    client = get_datadog_client()

    with console.status(f"[cyan]Fetching dashboard {dashboard_id}...[/cyan]"):
        dash = client.dashboards.get_dashboard(dashboard_id)

    data = dash.to_dict()
    export_to_json(data, output_file)
    console.print(f"[green]Dashboard {dashboard_id} exported to {output_file}[/green]")


@dashboard.command(name="clone")
@click.argument("dashboard_id")
@click.option("--title", required=True, help="Title for the cloned dashboard")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format",
)
@handle_api_error
def clone_dashboard_cmd(dashboard_id, title, fmt):
    """Clone a dashboard with a new title.

    Fetches the source dashboard definition, then creates a new dashboard
    with the same widgets and the specified title.
    """
    client = get_datadog_client()

    with console.status(f"[cyan]Fetching dashboard {dashboard_id}...[/cyan]"):
        original = client.dashboards.get_dashboard(dashboard_id)

    # Build the clone body from the original
    clone_body = original.to_dict()
    clone_body["title"] = title

    # Remove fields that shouldn't be copied to the clone
    for field in ["id", "author_handle", "created_at", "modified_at", "url"]:
        clone_body.pop(field, None)

    with console.status("[cyan]Creating cloned dashboard...[/cyan]"):
        result = client.dashboards.create_dashboard(body=clone_body)

    if fmt == "json":
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        console.print(f"[green]Dashboard {dashboard_id} cloned as {result.id}[/green]")
        console.print(f"[bold]Title:[/bold] {result.title}")
