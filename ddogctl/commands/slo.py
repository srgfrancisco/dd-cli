"""SLO (Service Level Objective) management commands."""

import click
import json
from rich.console import Console
from rich.table import Table
from ddogctl.client import get_datadog_client
from ddogctl.utils.error import handle_api_error
from ddogctl.utils.file_input import load_json_option
from ddogctl.utils.confirm import confirm_action
from ddogctl.utils.export import export_to_json
from ddogctl.utils.stdin import read_stdin_json, stdin_option
from ddogctl.utils.time import parse_time_range

console = Console()


def parse_thresholds(threshold_str: str) -> list[dict]:
    """Parse compact threshold string into list of threshold dicts.

    Format: "timeframe:target[,timeframe:target,...]"
    Example: "30d:99.9,7d:99.95"

    Returns:
        List of dicts with 'timeframe' and 'target' keys.

    Raises:
        ValueError: If the format is invalid.
    """
    if not threshold_str or not threshold_str.strip():
        raise ValueError("Threshold string cannot be empty")

    thresholds = []
    for part in threshold_str.split(","):
        part = part.strip()
        if ":" not in part:
            raise ValueError(f"Invalid threshold format: '{part}'. Expected 'timeframe:target'")
        pieces = part.split(":", 1)
        timeframe = pieces[0].strip()
        try:
            target = float(pieces[1].strip())
        except ValueError:
            raise ValueError(f"Invalid threshold target in '{part}'. Target must be a number.")
        thresholds.append({"timeframe": timeframe, "target": target})

    return thresholds


@click.group()
def slo():
    """SLO (Service Level Objective) management commands."""
    pass


@slo.command(name="list")
@click.option("--query", help="Search query to filter SLOs")
@click.option("--tags", "tags_filter", help="Filter by tags (comma-separated)")
@click.option("--limit", type=int, default=None, help="Maximum number of SLOs to return")
@click.option(
    "--format", "fmt", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def list_slos(query, tags_filter, limit, fmt):
    """List all SLOs."""
    client = get_datadog_client()

    kwargs = {}
    if query:
        kwargs["query"] = query
    if tags_filter:
        kwargs["tags_query"] = tags_filter
    if limit is not None:
        kwargs["limit"] = limit

    with console.status("[cyan]Fetching SLOs...[/cyan]"):
        response = client.slos.list_slos(**kwargs)

    slos_list = response.data if response.data else []

    if fmt == "json":
        output = [s.to_dict() for s in slos_list]
        print(json.dumps(output, indent=2, default=str))
    else:
        table = Table(title="Service Level Objectives")
        table.add_column("ID", style="cyan", width=14)
        table.add_column("Name", style="white", min_width=30)
        table.add_column("Type", style="dim", width=10)
        table.add_column("Tags", style="dim", width=30)

        for s in slos_list:
            tag_display = ", ".join(s.tags[:3]) if s.tags else ""
            if s.tags and len(s.tags) > 3:
                tag_display += f", +{len(s.tags) - 3} more"

            table.add_row(
                str(s.id),
                s.name,
                str(s.type),
                tag_display,
            )

        console.print(table)
        console.print(f"\n[dim]Total SLOs: {len(slos_list)}[/dim]")


@slo.command(name="get")
@click.argument("slo_id")
@click.option(
    "--format", "fmt", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def get_slo(slo_id, fmt):
    """Get SLO details."""
    client = get_datadog_client()

    with console.status(f"[cyan]Fetching SLO {slo_id}...[/cyan]"):
        response = client.slos.get_slo(slo_id)

    slo_data = response.data

    if fmt == "json":
        print(json.dumps(slo_data.to_dict(), indent=2, default=str))
    else:
        console.print(f"\n[bold cyan]SLO {slo_data.id}[/bold cyan]")
        console.print(f"[bold]Name:[/bold] {slo_data.name}")
        console.print(f"[bold]Type:[/bold] {slo_data.type}")

        if hasattr(slo_data, "description") and slo_data.description:
            console.print(f"[bold]Description:[/bold] {slo_data.description}")

        if hasattr(slo_data, "tags") and slo_data.tags:
            console.print(f"[bold]Tags:[/bold] {', '.join(slo_data.tags)}")

        if hasattr(slo_data, "thresholds") and slo_data.thresholds:
            console.print("[bold]Thresholds:[/bold]")
            for t in slo_data.thresholds:
                if isinstance(t, dict):
                    console.print(f"  {t.get('timeframe', 'N/A')}: {t.get('target', 'N/A')}%")
                else:
                    tf = getattr(t, "timeframe", "N/A")
                    tgt = getattr(t, "target", "N/A")
                    console.print(f"  {tf}: {tgt}%")

        if hasattr(slo_data, "creator") and slo_data.creator:
            email = getattr(slo_data.creator, "email", "N/A")
            console.print(f"[bold]Creator:[/bold] {email}")


@slo.command(name="create")
@click.option(
    "--type",
    "slo_type",
    type=click.Choice(["metric", "monitor"]),
    default=None,
    help="SLO type",
)
@click.option("--name", default=None, help="SLO name")
@click.option("--thresholds", default=None, help="Thresholds (e.g., '30d:99.9,7d:99.95')")
@click.option("--numerator", default=None, help="Numerator query (metric type)")
@click.option("--denominator", default=None, help="Denominator query (metric type)")
@click.option("--monitor-ids", default=None, help="Monitor IDs (comma-separated, monitor type)")
@click.option("--tags", default=None, help="Tags (comma-separated)")
@click.option("--description", default=None, help="SLO description")
@click.option(
    "-f",
    "--file",
    "file_data",
    callback=load_json_option,
    default=None,
    help="JSON file with SLO definition",
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
def create_slo(
    slo_type,
    name,
    thresholds,
    numerator,
    denominator,
    monitor_ids,
    tags,
    description,
    file_data,
    from_stdin,
    fmt,
):
    """Create an SLO from inline flags, a JSON file, or stdin.

    Examples:
        ddogctl slo create --type metric --name "API SLO" --thresholds "30d:99.9" ...
        ddogctl slo create -f slo.json
        ddogctl slo export abc123 | ddogctl slo create --from-stdin
    """
    if from_stdin:
        file_data = read_stdin_json()

    if file_data:
        body = file_data
    else:
        # Validate required fields
        if not slo_type:
            raise click.UsageError("Missing option '--type' (required without -f)")
        if not name:
            raise click.UsageError("Missing option '--name' (required without -f)")
        if not thresholds:
            raise click.UsageError("Missing option '--thresholds' (required without -f)")

        parsed_thresholds = parse_thresholds(thresholds)

        body = {
            "type": slo_type,
            "name": name,
            "thresholds": parsed_thresholds,
        }

        if slo_type == "metric":
            if not numerator:
                raise click.UsageError(
                    "Missing option '--numerator' (required for metric SLO type)"
                )
            if not denominator:
                raise click.UsageError(
                    "Missing option '--denominator' (required for metric SLO type)"
                )
            body["query"] = {
                "numerator": numerator,
                "denominator": denominator,
            }
        elif slo_type == "monitor":
            if not monitor_ids:
                raise click.UsageError(
                    "Missing option '--monitor-ids' (required for monitor SLO type)"
                )
            body["monitor_ids"] = [int(mid.strip()) for mid in monitor_ids.split(",")]

        if tags:
            body["tags"] = [t.strip() for t in tags.split(",")]
        if description:
            body["description"] = description

    client = get_datadog_client()

    with console.status("[cyan]Creating SLO...[/cyan]"):
        result = client.slos.create_slo(body=body)

    # Result.data is a list of created SLOs
    created = result.data[0] if result.data else None

    if fmt == "json":
        if created:
            print(json.dumps(created.to_dict(), indent=2, default=str))
        else:
            print("{}")
    else:
        if created:
            console.print(f"[green]SLO {created.id} created[/green]")
            console.print(f"[bold]Name:[/bold] {created.name}")
        else:
            console.print("[green]SLO created[/green]")


@slo.command(name="update")
@click.argument("slo_id")
@click.option("--name", default=None, help="SLO name")
@click.option("--thresholds", default=None, help="Thresholds (e.g., '30d:99.9,7d:99.95')")
@click.option("--tags", default=None, help="Tags (comma-separated)")
@click.option("--description", default=None, help="SLO description")
@click.option(
    "-f",
    "--file",
    "file_data",
    callback=load_json_option,
    default=None,
    help="JSON file with SLO update definition",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format",
)
@handle_api_error
def update_slo(slo_id, name, thresholds, tags, description, file_data, fmt):
    """Update an SLO by ID from inline flags or a JSON file."""
    if file_data:
        body = file_data
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if thresholds is not None:
            body["thresholds"] = parse_thresholds(thresholds)
        if tags is not None:
            body["tags"] = [t.strip() for t in tags.split(",")]
        if description is not None:
            body["description"] = description

        if not body:
            raise click.UsageError("No update fields specified. Use flags or -f file.json")

    client = get_datadog_client()

    with console.status(f"[cyan]Updating SLO {slo_id}...[/cyan]"):
        result = client.slos.update_slo(slo_id, body=body)

    updated = result.data[0] if result.data else None

    if fmt == "json":
        if updated:
            print(json.dumps(updated.to_dict(), indent=2, default=str))
        else:
            print("{}")
    else:
        if updated:
            console.print(f"[green]SLO {slo_id} updated[/green]")
            console.print(f"[bold]Name:[/bold] {updated.name}")
        else:
            console.print(f"[green]SLO {slo_id} updated[/green]")


@slo.command(name="delete")
@click.argument("slo_id")
@click.option("--confirm", "confirmed", is_flag=True, help="Skip confirmation prompt")
@handle_api_error
def delete_slo(slo_id, confirmed):
    """Delete an SLO by ID."""
    if not confirm_action(f"Delete SLO {slo_id}?", confirmed):
        console.print("[yellow]Aborted[/yellow]")
        return

    client = get_datadog_client()

    with console.status(f"[cyan]Deleting SLO {slo_id}...[/cyan]"):
        client.slos.delete_slo(slo_id)

    console.print(f"[green]SLO {slo_id} deleted[/green]")


@slo.command(name="history")
@click.argument("slo_id")
@click.option("--from", "from_time", required=True, help="Start time (e.g., 30d, 7d, 1h)")
@click.option("--to", "to_time", default="now", help="End time")
@click.option(
    "--format", "fmt", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def slo_history(slo_id, from_time, to_time, fmt):
    """Show SLO history including error budget and burn rate."""
    client = get_datadog_client()

    from_ts, to_ts = parse_time_range(from_time, to_time)

    with console.status(f"[cyan]Fetching SLO history for {slo_id}...[/cyan]"):
        response = client.slos.get_slo_history(slo_id, from_ts=from_ts, to_ts=to_ts)

    history_data = response.data

    if fmt == "json":
        print(json.dumps(history_data.to_dict(), indent=2, default=str))
    else:
        console.print(f"\n[bold cyan]SLO History: {slo_id}[/bold cyan]")

        # Overall SLI value
        if hasattr(history_data, "overall") and history_data.overall:
            sli = getattr(history_data.overall, "sli_value", None)
            if sli is not None:
                console.print(f"[bold]Overall SLI:[/bold] {sli:.4f}%")

        # Threshold details
        if hasattr(history_data, "thresholds") and history_data.thresholds:
            table = Table(title="Threshold Status")
            table.add_column("Timeframe", style="cyan")
            table.add_column("Target", justify="right", style="yellow")
            table.add_column("SLI Value", justify="right", style="white")
            table.add_column("Status", style="bold")

            thresholds = history_data.thresholds
            if isinstance(thresholds, dict):
                for tf, details in thresholds.items():
                    target = getattr(details, "target", None)
                    sli_val = getattr(details, "sli_value", None)

                    target_str = f"{target}%" if target is not None else "N/A"
                    sli_str = f"{sli_val:.4f}%" if sli_val is not None else "N/A"

                    if target is not None and sli_val is not None:
                        status = "[green]OK[/green]" if sli_val >= target else "[red]BREACHED[/red]"
                    else:
                        status = "[dim]N/A[/dim]"

                    table.add_row(tf, target_str, sli_str, status)

            console.print(table)


@slo.command(name="export")
@click.argument("slo_id")
@click.option(
    "-o",
    "--output",
    "output_file",
    required=True,
    help="Output file path",
)
@handle_api_error
def export_slo(slo_id, output_file):
    """Export an SLO definition to a JSON file for GitOps workflows."""
    client = get_datadog_client()

    with console.status(f"[cyan]Fetching SLO {slo_id}...[/cyan]"):
        response = client.slos.get_slo(slo_id)

    slo_data = response.data
    export_to_json(slo_data.to_dict(), output_file)

    console.print(f"[green]Exported SLO {slo_id} to {output_file}[/green]")
