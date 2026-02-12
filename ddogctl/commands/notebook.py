"""Notebook management commands."""

import click
import json
from rich.console import Console
from rich.table import Table
from ddogctl.client import get_datadog_client
from ddogctl.utils.error import handle_api_error
from ddogctl.utils.confirm import confirm_action

console = Console()


@click.group()
def notebook():
    """Notebook management commands."""
    pass


@notebook.command(name="list")
@click.option(
    "--format", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def list_notebooks(format):
    """List all notebooks."""
    client = get_datadog_client()

    with console.status("[cyan]Fetching notebooks...[/cyan]"):
        response = client.notebooks.list_notebooks()

    notebooks_list = response.data or []

    if format == "json":
        output = []
        for nb in notebooks_list:
            attrs = nb.attributes
            output.append(
                {
                    "id": nb.id,
                    "name": getattr(attrs, "name", ""),
                    "author": (
                        getattr(attrs, "author", {}).get("handle", "")
                        if isinstance(getattr(attrs, "author", None), dict)
                        else str(getattr(attrs, "author", ""))
                    ),
                    "modified": str(getattr(attrs, "modified", "")),
                    "status": str(getattr(attrs, "status", "")),
                }
            )
        print(json.dumps(output, indent=2, default=str))
    else:
        table = Table(title="Notebooks", show_lines=False)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="white", min_width=30)
        table.add_column("Author", style="dim")
        table.add_column("Modified", style="dim")
        table.add_column("Status", style="yellow")

        for nb in notebooks_list:
            attrs = nb.attributes
            author = getattr(attrs, "author", None)
            if isinstance(author, dict):
                author_str = author.get("handle", "")
            else:
                author_str = str(author) if author else ""

            table.add_row(
                str(nb.id),
                str(getattr(attrs, "name", "")),
                author_str,
                str(getattr(attrs, "modified", "")),
                str(getattr(attrs, "status", "")),
            )

        console.print(table)
        console.print(f"\n[dim]Total notebooks: {len(notebooks_list)}[/dim]")


@notebook.command(name="get")
@click.argument("notebook_id", type=int)
@click.option(
    "--format", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def get_notebook(notebook_id, format):
    """Get notebook details."""
    client = get_datadog_client()

    with console.status(f"[cyan]Fetching notebook {notebook_id}...[/cyan]"):
        response = client.notebooks.get_notebook(notebook_id=notebook_id)

    nb = response.data
    attrs = nb.attributes

    if format == "json":
        output = {
            "id": nb.id,
            "name": getattr(attrs, "name", ""),
            "author": (
                getattr(attrs, "author", {}).get("handle", "")
                if isinstance(getattr(attrs, "author", None), dict)
                else str(getattr(attrs, "author", ""))
            ),
            "cells": len(getattr(attrs, "cells", []) or []),
            "created": str(getattr(attrs, "created", "")),
            "modified": str(getattr(attrs, "modified", "")),
            "status": str(getattr(attrs, "status", "")),
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        console.print(f"\n[bold cyan]Notebook {nb.id}[/bold cyan]")
        console.print(f"[bold]Name:[/bold] {getattr(attrs, 'name', '')}")

        author = getattr(attrs, "author", None)
        if author:
            author_str = author.get("handle", "") if isinstance(author, dict) else str(author)
            console.print(f"[bold]Author:[/bold] {author_str}")

        created = getattr(attrs, "created", None)
        if created:
            console.print(f"[bold]Created:[/bold] {created}")

        modified = getattr(attrs, "modified", None)
        if modified:
            console.print(f"[bold]Modified:[/bold] {modified}")

        status = getattr(attrs, "status", None)
        if status:
            console.print(f"[bold]Status:[/bold] {status}")

        cells = getattr(attrs, "cells", []) or []
        console.print(f"[bold]Cells:[/bold] {len(cells)}")


@notebook.command(name="create")
@click.option("--name", required=True, help="Notebook name")
@click.option(
    "--format", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def create_notebook(name, format):
    """Create a notebook."""
    from datadog_api_client.v1.model.notebook_create_request import NotebookCreateRequest
    from datadog_api_client.v1.model.notebook_create_data import NotebookCreateData
    from datadog_api_client.v1.model.notebook_create_data_attributes import (
        NotebookCreateDataAttributes,
    )
    from datadog_api_client.v1.model.notebook_cell_create_request import NotebookCellCreateRequest
    from datadog_api_client.v1.model.notebook_timeseries_cell_attributes import (
        NotebookTimeseriesCellAttributes,
    )
    from datadog_api_client.v1.model.timeseries_widget_definition import (
        TimeseriesWidgetDefinition,
    )
    from datadog_api_client.v1.model.timeseries_widget_definition_type import (
        TimeseriesWidgetDefinitionType,
    )
    from datadog_api_client.v1.model.timeseries_widget_request import TimeseriesWidgetRequest
    from datadog_api_client.v1.model.notebook_cell_resource_type import NotebookCellResourceType
    from datadog_api_client.v1.model.notebook_resource_type import NotebookResourceType
    from datadog_api_client.v1.model.notebook_relative_time import NotebookRelativeTime

    client = get_datadog_client()

    # Build a default timeseries cell
    cell = NotebookCellCreateRequest(
        attributes=NotebookTimeseriesCellAttributes(
            definition=TimeseriesWidgetDefinition(
                type=TimeseriesWidgetDefinitionType.TIMESERIES,
                requests=[
                    TimeseriesWidgetRequest(
                        q="avg:system.cpu.user{*}",
                    )
                ],
            ),
        ),
        type=NotebookCellResourceType.NOTEBOOK_CELLS,
    )

    body = NotebookCreateRequest(
        data=NotebookCreateData(
            attributes=NotebookCreateDataAttributes(
                cells=[cell],
                name=name,
                time=NotebookRelativeTime(live_span="1h"),
            ),
            type=NotebookResourceType.NOTEBOOKS,
        ),
    )

    with console.status("[cyan]Creating notebook...[/cyan]"):
        response = client.notebooks.create_notebook(body=body)

    nb = response.data

    if format == "json":
        output = {
            "id": nb.id,
            "name": getattr(nb.attributes, "name", ""),
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        console.print(f"[green]Notebook {nb.id} created[/green]")
        console.print(f"[bold]Name:[/bold] {getattr(nb.attributes, 'name', '')}")


@notebook.command(name="delete")
@click.argument("notebook_id", type=int)
@click.option("--confirm", "confirmed", is_flag=True, help="Skip confirmation prompt")
@handle_api_error
def delete_notebook(notebook_id, confirmed):
    """Delete a notebook by ID."""
    if not confirm_action(f"Delete notebook {notebook_id}?", confirmed):
        console.print("[yellow]Aborted[/yellow]")
        return

    client = get_datadog_client()

    with console.status(f"[cyan]Deleting notebook {notebook_id}...[/cyan]"):
        client.notebooks.delete_notebook(notebook_id=notebook_id)

    console.print(f"[green]Notebook {notebook_id} deleted[/green]")
