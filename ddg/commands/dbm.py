"""Database monitoring commands."""

import click
import json
from rich.console import Console
from rich.table import Table
from ddg.client import get_datadog_client
from ddg.utils.error import handle_api_error
from ddg.utils.time import parse_time_range

console = Console()


@click.group()
def dbm():
    """Database monitoring commands."""
    pass


@dbm.command(name="hosts")
@click.option("--env", default=None, help="Filter by environment")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def list_hosts(env, format):
    """List database hosts being monitored."""
    client = get_datadog_client()

    kwargs = {}
    if env:
        kwargs["env"] = env

    with console.status("[cyan]Fetching database hosts...[/cyan]"):
        response = client.dbm.list_hosts(**kwargs)

    hosts = response.data if response.data else []

    if format == "json":
        output = []
        for h in hosts:
            output.append(
                {
                    "host": h.host,
                    "engine": h.engine,
                    "version": h.version,
                    "connections": h.connections,
                    "status": h.status,
                }
            )
        print(json.dumps(output, indent=2))
    else:
        table = Table(title="Database Hosts")
        table.add_column("Host", style="cyan")
        table.add_column("Engine", style="white")
        table.add_column("Version", style="white")
        table.add_column("Connections", justify="right", style="yellow")
        table.add_column("Status", style="green")

        for h in hosts:
            table.add_row(
                h.host,
                h.engine,
                h.version,
                str(h.connections),
                h.status,
            )

        console.print(table)
        console.print(f"\n[dim]Total hosts: {len(hosts)}[/dim]")


@dbm.command(name="queries")
@click.option("--from", "from_time", default="1h", help="Start time (e.g., 1h, 24h, 7d)")
@click.option("--to", "to_time", default="now", help="End time")
@click.option("--service", default=None, help="Filter by service")
@click.option("--database", default=None, help="Filter by database")
@click.option(
    "--sort-by", "sort_by", default="avg_latency", help="Sort by field (avg_latency, calls)"
)
@click.option("--limit", default=20, type=int, help="Max queries to return")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def list_queries(from_time, to_time, service, database, sort_by, limit, format):
    """List top database queries."""
    client = get_datadog_client()

    from_ts, to_ts = parse_time_range(from_time, to_time)

    kwargs = {
        "from_ts": from_ts,
        "to_ts": to_ts,
        "sort_by": sort_by,
        "limit": limit,
    }
    if service:
        kwargs["service"] = service
    if database:
        kwargs["database"] = database

    with console.status("[cyan]Fetching database queries...[/cyan]"):
        response = client.dbm.list_queries(**kwargs)

    queries = response.data if response.data else []

    if format == "json":
        output = []
        for q in queries:
            avg_latency_ms = round(q.avg_latency / 1_000_000, 2)
            total_time_ms = round(q.total_time / 1_000_000, 2)
            output.append(
                {
                    "query_id": q.query_id,
                    "normalized_query": q.normalized_query,
                    "avg_latency_ms": avg_latency_ms,
                    "calls": q.calls,
                    "total_time_ms": total_time_ms,
                    "service": q.service,
                    "database": q.database,
                }
            )
        print(json.dumps(output, indent=2))
    else:
        table = Table(title="Database Queries")
        table.add_column("Query ID", style="cyan")
        table.add_column("Query", style="white")
        table.add_column("Avg Latency (ms)", justify="right", style="yellow")
        table.add_column("Calls", justify="right", style="yellow")
        table.add_column("Total Time (ms)", justify="right", style="yellow")

        for q in queries:
            avg_latency_ms = q.avg_latency / 1_000_000
            total_time_ms = q.total_time / 1_000_000

            table.add_row(
                q.query_id,
                q.normalized_query[:50],
                f"{avg_latency_ms:.2f}",
                str(q.calls),
                f"{total_time_ms:.2f}",
            )

        console.print(table)
        console.print(f"\n[dim]Total queries: {len(queries)}[/dim]")


@dbm.command(name="explain")
@click.argument("query_id")
@click.option("--format", type=click.Choice(["json", "text"]), default="text")
@handle_api_error
def explain_query(query_id, format):
    """Show execution plan for a query.

    QUERY_ID is the ID of the query to explain.
    """
    client = get_datadog_client()

    with console.status(f"[cyan]Fetching query plan for {query_id}...[/cyan]"):
        try:
            response = client.dbm.get_query_plan(query_id)
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                console.print(f"[red]Query {query_id} not found[/red]")
                return
            raise

    plan = response.data if response.data else None

    if plan is None:
        console.print(f"[red]Query {query_id} not found[/red]")
        return

    if format == "json":
        output = {
            "query_id": plan.query_id,
            "plan": plan.plan_text,
            "database": plan.database,
            "service": plan.service,
            "cost": plan.cost,
        }
        print(json.dumps(output, indent=2))
    else:
        console.print(f"\n[bold cyan]Query Plan for {plan.query_id}[/bold cyan]")
        console.print(f"[dim]Database: {plan.database}[/dim]")
        console.print(f"[dim]Service: {plan.service}[/dim]")
        console.print(f"[dim]Cost: {plan.cost}[/dim]")
        console.print()
        console.print(plan.plan_text)


@dbm.command(name="samples")
@click.argument("query_id")
@click.option("--from", "from_time", default="1h", help="Start time (e.g., 1h, 24h, 7d)")
@click.option("--to", "to_time", default="now", help="End time")
@click.option("--limit", default=10, type=int, help="Max samples to return")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def list_samples(query_id, from_time, to_time, limit, format):
    """List sample executions for a query.

    QUERY_ID is the ID of the query to get samples for.
    """
    client = get_datadog_client()

    from_ts, to_ts = parse_time_range(from_time, to_time)

    with console.status(f"[cyan]Fetching samples for {query_id}...[/cyan]"):
        response = client.dbm.list_query_samples(
            query_id,
            from_ts=from_ts,
            to_ts=to_ts,
            limit=limit,
        )

    samples = response.data if response.data else []

    if format == "json":
        output = []
        for s in samples:
            duration_ms = round(s.duration / 1_000_000, 2)
            output.append(
                {
                    "timestamp": str(s.timestamp),
                    "duration_ms": duration_ms,
                    "rows_affected": s.rows_affected,
                    "parameters": s.parameters,
                }
            )
        print(json.dumps(output, indent=2))
    else:
        table = Table(title=f"Query Samples for {query_id}")
        table.add_column("Time", style="cyan", width=20)
        table.add_column("Duration (ms)", justify="right", style="yellow", width=15)
        table.add_column("Rows Affected", justify="right", style="white", width=15)
        table.add_column("Parameters", style="dim", min_width=20)

        for s in samples:
            duration_ms = s.duration / 1_000_000
            time_str = str(s.timestamp)

            table.add_row(
                time_str,
                f"{duration_ms:.2f}",
                str(s.rows_affected),
                str(s.parameters),
            )

        console.print(table)
        console.print(f"\n[dim]Total samples: {len(samples)}[/dim]")
