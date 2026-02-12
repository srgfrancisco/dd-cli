"""Synthetics test management commands."""

import click
import json
from rich.console import Console
from rich.table import Table
from ddogctl.client import get_datadog_client
from ddogctl.utils.error import handle_api_error

console = Console()


@click.group()
def synthetics():
    """Synthetics test management commands."""
    pass


@synthetics.command(name="list")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def list_tests(format):
    """List all Synthetics tests."""
    client = get_datadog_client()

    with console.status("[cyan]Fetching Synthetics tests...[/cyan]"):
        response = client.synthetics.list_tests()

    tests = response.tests if response.tests else []

    if format == "json":
        output = []
        for test in tests:
            output.append(
                {
                    "public_id": test.public_id,
                    "name": test.name,
                    "type": str(test.type),
                    "status": str(test.status),
                    "locations": list(test.locations) if test.locations else [],
                    "tags": list(test.tags) if test.tags else [],
                }
            )
        print(json.dumps(output, indent=2))
    else:
        table = Table(title="Synthetics Tests")
        table.add_column("Public ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Type", style="dim")
        table.add_column("Status", style="yellow")
        table.add_column("Locations", style="dim")
        table.add_column("Tags", style="dim")

        for test in tests:
            status_style = "green" if str(test.status) == "live" else "red"
            locations = ", ".join(test.locations) if test.locations else ""
            tags = ", ".join(test.tags) if test.tags else ""
            table.add_row(
                test.public_id,
                test.name,
                str(test.type),
                f"[{status_style}]{test.status}[/{status_style}]",
                locations,
                tags,
            )

        console.print(table)
        console.print(f"\n[dim]Total tests: {len(tests)}[/dim]")


@synthetics.command(name="get")
@click.argument("public_id")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def get_test(public_id, format):
    """Get details for a Synthetics test."""
    client = get_datadog_client()

    with console.status(f"[cyan]Fetching test {public_id}...[/cyan]"):
        test = client.synthetics.get_test(public_id=public_id)

    if format == "json":
        output = {
            "public_id": test.public_id,
            "name": test.name,
            "type": str(test.type),
            "status": str(test.status),
            "locations": list(test.locations) if test.locations else [],
            "tags": list(test.tags) if test.tags else [],
            "message": test.message if hasattr(test, "message") else "",
        }
        print(json.dumps(output, indent=2))
    else:
        table = Table(title=f"Synthetics Test: {public_id}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Public ID", test.public_id)
        table.add_row("Name", test.name)
        table.add_row("Type", str(test.type))
        status_style = "green" if str(test.status) == "live" else "red"
        table.add_row("Status", f"[{status_style}]{test.status}[/{status_style}]")
        locations = ", ".join(test.locations) if test.locations else "None"
        table.add_row("Locations", locations)
        tags = ", ".join(test.tags) if test.tags else "None"
        table.add_row("Tags", tags)
        message = test.message if hasattr(test, "message") else ""
        table.add_row("Message", message or "None")

        console.print(table)


@synthetics.command(name="results")
@click.argument("public_id")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def get_results(public_id, format):
    """Get latest results for a Synthetics test."""
    client = get_datadog_client()

    with console.status(f"[cyan]Fetching results for {public_id}...[/cyan]"):
        response = client.synthetics.get_api_test_latest_results(public_id=public_id)

    results = response.results if response.results else []

    if format == "json":
        output = []
        for result in results:
            output.append(
                {
                    "result_id": getattr(result, "result_id", None),
                    "status": str(getattr(result, "status", "unknown")),
                    "check_time": getattr(result, "check_time", None),
                    "probe_dc": getattr(result, "dc_id", None),
                }
            )
        print(json.dumps(output, indent=2))
    else:
        table = Table(title=f"Latest Results: {public_id}")
        table.add_column("Result ID", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Check Time", style="dim")
        table.add_column("Location", style="dim")

        for result in results:
            result_id = getattr(result, "result_id", "N/A")
            status = str(getattr(result, "status", "unknown"))
            check_time = str(getattr(result, "check_time", "N/A"))
            probe_dc = getattr(result, "dc_id", "N/A")

            status_style = "green" if status == "0" or status == "passed" else "red"
            table.add_row(
                str(result_id),
                f"[{status_style}]{status}[/{status_style}]",
                str(check_time),
                str(probe_dc),
            )

        console.print(table)
        console.print(f"\n[dim]Total results: {len(results)}[/dim]")


@synthetics.command(name="trigger")
@click.argument("public_id")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def trigger_test(public_id, format):
    """Trigger a Synthetics test execution."""
    from datadog_api_client.v1.model.synthetics_trigger_body import SyntheticsTriggerBody
    from datadog_api_client.v1.model.synthetics_trigger_test import SyntheticsTriggerTest

    client = get_datadog_client()

    body = SyntheticsTriggerBody(
        tests=[SyntheticsTriggerTest(public_id=public_id)],
    )

    with console.status(f"[cyan]Triggering test {public_id}...[/cyan]"):
        response = client.synthetics.trigger_tests(body=body)

    triggered = response.results if response.results else []
    locations = response.locations if hasattr(response, "locations") else []

    if format == "json":
        output = {
            "triggered_check_ids": [
                {
                    "public_id": getattr(t, "public_id", None),
                    "result_id": getattr(t, "result_id", None),
                }
                for t in triggered
            ],
            "locations": (
                [
                    {
                        "id": getattr(loc, "id", None),
                        "name": getattr(loc, "name", None),
                    }
                    for loc in locations
                ]
                if locations
                else []
            ),
        }
        print(json.dumps(output, indent=2))
    else:
        console.print(f"[green]Test {public_id} triggered successfully.[/green]")

        if triggered:
            table = Table(title="Triggered Results")
            table.add_column("Public ID", style="cyan")
            table.add_column("Result ID", style="white")

            for t in triggered:
                table.add_row(
                    str(getattr(t, "public_id", "N/A")),
                    str(getattr(t, "result_id", "N/A")),
                )
            console.print(table)

        console.print(f"\n[dim]Triggered {len(triggered)} result(s)[/dim]")
