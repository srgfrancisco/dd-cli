"""Apply and diff commands for declarative resource management."""

import difflib
import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.syntax import Syntax

from ddogctl.client import get_datadog_client
from ddogctl.utils.error import handle_api_error
from ddogctl.utils.file_input import load_json_file
from ddogctl.utils.stdin import read_stdin_json, stdin_option

console = Console()


def detect_resource_type(data: dict) -> str:
    """Detect Datadog resource type from JSON structure.

    Detection priority:
        1. dashboard — has "layout_type" or "widgets"
        2. slo — has "thresholds" and type is "metric" or "monitor"
        3. downtime — has "scope" as a list
        4. monitor — has "query"

    Args:
        data: Parsed JSON dict representing a Datadog resource.

    Returns:
        Resource type string: "monitor", "dashboard", "slo", or "downtime".

    Raises:
        ValueError: If the resource type cannot be determined.
    """
    if "layout_type" in data or "widgets" in data:
        return "dashboard"
    if "thresholds" in data and data.get("type") in ("metric", "monitor"):
        return "slo"
    if isinstance(data.get("scope"), list):
        return "downtime"
    if "query" in data:
        return "monitor"
    raise ValueError("Cannot detect resource type from JSON structure")


def _apply_single_resource(data: dict, dry_run: bool = False) -> None:
    """Apply a single resource (create or update).

    Args:
        data: Parsed JSON dict representing a Datadog resource.
        dry_run: If True, preview without making API calls.
    """
    resource_type = detect_resource_type(data)
    has_id = "id" in data
    action = "update" if has_id else "create"

    if dry_run:
        console.print(f"[yellow]DRY RUN: Would {action} {resource_type}[/yellow]")
        if has_id:
            console.print(f"[dim]  ID: {data['id']}[/dim]")
        console.print(f"[dim]  Data: {json.dumps(data, indent=2, default=str)[:200]}...[/dim]")
        return

    client = get_datadog_client()

    if resource_type == "monitor":
        if action == "create":
            result = client.monitors.create_monitor(body=data)
        else:
            monitor_id = data.pop("id")
            result = client.monitors.update_monitor(monitor_id, body=data)
        console.print(f"[green]{action.title()}d monitor {result.id}[/green]")

    elif resource_type == "dashboard":
        if action == "create":
            result = client.dashboards.create_dashboard(body=data)
        else:
            dashboard_id = data.pop("id")
            result = client.dashboards.update_dashboard(dashboard_id, body=data)
        console.print(f"[green]{action.title()}d dashboard {result.id}[/green]")

    elif resource_type == "slo":
        if action == "create":
            result = client.slos.create_slo(body=data)
            slo_obj = result.data[0] if result.data else None
            slo_id = slo_obj.id if slo_obj else "unknown"
        else:
            slo_id = data.pop("id")
            result = client.slos.update_slo(slo_id, body=data)
        console.print(f"[green]{action.title()}d slo {slo_id}[/green]")

    elif resource_type == "downtime":
        if action == "create":
            result = client.downtimes.create_downtime(body=data)
        else:
            downtime_id = data.pop("id")
            result = client.downtimes.update_downtime(downtime_id, body=data)
        console.print(f"[green]{action.title()}d downtime {result.id}[/green]")


def _fetch_live_state(data: dict, resource_type: str) -> dict:
    """Fetch the live state of a resource from the Datadog API.

    Args:
        data: Local resource data (must contain "id").
        resource_type: The detected resource type.

    Returns:
        Dict representation of the live resource.
    """
    client = get_datadog_client()
    resource_id = data["id"]

    if resource_type == "monitor":
        live = client.monitors.get_monitor(resource_id)
        return live.to_dict()
    elif resource_type == "dashboard":
        live = client.dashboards.get_dashboard(resource_id)
        return live.to_dict()
    elif resource_type == "slo":
        response = client.slos.get_slo(resource_id)
        return response.data.to_dict()
    elif resource_type == "downtime":
        live = client.downtimes.get_downtime(resource_id)
        return live.to_dict()
    else:
        raise ValueError(f"Unknown resource type: {resource_type}")


@click.command(name="apply")
@click.option(
    "-f",
    "--file",
    "file_path",
    required=False,
    default=None,
    help="JSON file or directory to apply",
)
@stdin_option
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview changes without applying",
)
@click.option(
    "--recursive",
    is_flag=True,
    default=False,
    help="Scan directory recursively for JSON files",
)
@handle_api_error
def apply_cmd(file_path, from_stdin, dry_run, recursive):
    """Apply Datadog resources from JSON files or stdin.

    Auto-detects resource type (monitor, dashboard, SLO, downtime) from JSON
    structure. Resources with an 'id' field are updated; without are created.

    Examples:
        ddogctl apply -f monitor.json
        ddogctl apply -f dashboards/ --recursive
        ddogctl apply -f slo.json --dry-run
        echo '{"type":"metric alert","query":"...","name":"CPU"}' | ddogctl apply --from-stdin
    """
    if from_stdin:
        data = read_stdin_json()
        try:
            _apply_single_resource(data, dry_run=dry_run)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        return

    if not file_path:
        raise click.UsageError("Either -f/--file or --from-stdin is required.")

    path = Path(file_path)

    if path.is_dir():
        if not recursive:
            console.print(
                f"[red]Error: '{file_path}' is a directory. Use --recursive to scan it.[/red]"
            )
            sys.exit(1)

        json_files = sorted(path.glob("**/*.json"))
        if not json_files:
            console.print(f"[yellow]No JSON files found in {file_path}[/yellow]")
            sys.exit(1)

        console.print(f"[cyan]Found {len(json_files)} JSON file(s) in {file_path}[/cyan]")
        for jf in json_files:
            console.print(f"\n[bold]Processing {jf.name}...[/bold]")
            try:
                data = load_json_file(str(jf))
                _apply_single_resource(data, dry_run=dry_run)
            except (ValueError, FileNotFoundError) as e:
                console.print(f"[red]Error processing {jf.name}: {e}[/red]")

    elif path.is_file():
        try:
            data = load_json_file(file_path)
        except FileNotFoundError:
            console.print(f"[red]Error: File not found: {file_path}[/red]")
            sys.exit(1)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)

        try:
            _apply_single_resource(data, dry_run=dry_run)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)

    else:
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        sys.exit(1)


@click.command(name="diff")
@click.option(
    "-f",
    "--file",
    "file_path",
    required=True,
    help="JSON file to compare against live state",
)
@handle_api_error
def diff_cmd(file_path):
    """Compare a local JSON file against the live Datadog state.

    The file must contain an 'id' field so the live resource can be fetched.
    Shows a unified diff with color highlighting.

    Examples:
        ddogctl diff -f monitor.json
        ddogctl diff -f dashboard.json
    """
    try:
        local_data = load_json_file(file_path)
    except FileNotFoundError:
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    if "id" not in local_data:
        console.print(
            "[red]Error: File must contain an 'id' field to diff against live state[/red]"
        )
        sys.exit(1)

    try:
        resource_type = detect_resource_type(local_data)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    console.print(f"[cyan]Fetching live {resource_type} {local_data['id']}...[/cyan]")

    live_data = _fetch_live_state(local_data, resource_type)

    # Normalize both to sorted JSON for comparison
    local_json = json.dumps(local_data, indent=2, sort_keys=True, default=str)
    live_json = json.dumps(live_data, indent=2, sort_keys=True, default=str)

    if local_json == live_json:
        console.print("[green]No differences found. Local file is identical to live state.[/green]")
        return

    # Generate unified diff
    diff_lines = list(
        difflib.unified_diff(
            live_json.splitlines(keepends=True),
            local_json.splitlines(keepends=True),
            fromfile=f"live ({resource_type} {local_data['id']})",
            tofile=f"local ({file_path})",
        )
    )

    diff_text = "".join(diff_lines)
    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
    console.print(syntax)
