"""Usage metering commands."""

import click
import json
from datetime import datetime, date, timedelta
from rich.console import Console
from rich.table import Table
from ddogctl.client import get_datadog_client
from ddogctl.utils.error import handle_api_error

console = Console()


def _parse_date(value: str, default_days_ago: int = 7) -> date:
    """Parse a date string or relative time like '7d' into a date object.

    Args:
        value: Date string in YYYY-MM-DD format, or relative like '7d', '30d'.
        default_days_ago: Default number of days ago if value is None.

    Returns:
        A date object.
    """
    if value is None:
        return date.today() - timedelta(days=default_days_ago)

    if value == "now" or value == "today":
        return date.today()

    # Relative days format: "7d", "30d"
    if value.endswith("d") and value[:-1].isdigit():
        days = int(value[:-1])
        return date.today() - timedelta(days=days)

    # ISO date format: YYYY-MM-DD
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise click.BadParameter(f"Invalid date format: {value}. Use YYYY-MM-DD or Nd (e.g., 7d).")


def _parse_datetime(value: str, default_hours_ago: int = 24) -> datetime:
    """Parse a datetime string or relative time into a datetime object.

    Args:
        value: Datetime string or relative like '24h', '7d'.
        default_hours_ago: Default number of hours ago if value is None.

    Returns:
        A datetime object.
    """
    if value is None:
        return datetime.now() - timedelta(hours=default_hours_ago)

    if value == "now":
        return datetime.now()

    # Relative hours: "1h", "24h"
    if value.endswith("h") and value[:-1].isdigit():
        hours = int(value[:-1])
        return datetime.now() - timedelta(hours=hours)

    # Relative days: "7d", "30d"
    if value.endswith("d") and value[:-1].isdigit():
        days = int(value[:-1])
        return datetime.now() - timedelta(days=days)

    # ISO datetime or date format
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise click.BadParameter(
            f"Invalid datetime format: {value}. Use YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, or Nh/Nd."
        )


@click.group()
def usage():
    """Usage metering and cost visibility commands."""
    pass


@usage.command(name="summary")
@click.option(
    "--from",
    "from_date",
    default="7d",
    help="Start date (YYYY-MM-DD or Nd, e.g., 7d, 30d). Default: 7d.",
)
@click.option(
    "--to",
    "to_date",
    default="today",
    help="End date (YYYY-MM-DD or 'today'). Default: today.",
)
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def summary(from_date, to_date, format):
    """Show usage summary across all product families."""
    client = get_datadog_client()

    start_d = _parse_date(from_date, default_days_ago=7)
    end_d = _parse_date(to_date, default_days_ago=0)

    with console.status("[cyan]Fetching usage summary...[/cyan]"):
        response = client.usage.get_usage_summary(start_d=start_d, end_d=end_d)

    if format == "json":
        data = {
            "start_date": str(getattr(response, "start_date", start_d)),
            "end_date": str(getattr(response, "end_date", end_d)),
            "apm_host_top99p": getattr(response, "apm_host_top99p", None),
            "infra_host_top99p": getattr(response, "infra_host_top99p", None),
            "container_avg": getattr(response, "container_avg", None),
            "custom_ts_avg": getattr(response, "custom_ts_avg", None),
            "logs_indexed_logs_usage_agg_sum": getattr(
                response, "logs_indexed_logs_usage_agg_sum", None
            ),
            "ingested_events_bytes_agg_sum": getattr(
                response, "ingested_events_bytes_agg_sum", None
            ),
        }
        print(json.dumps(data, indent=2, default=str))
    else:
        table = Table(title=f"Usage Summary ({start_d} to {end_d})")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="yellow")

        fields = [
            ("APM Hosts (top 99p)", "apm_host_top99p"),
            ("Infra Hosts (top 99p)", "infra_host_top99p"),
            ("Containers (avg)", "container_avg"),
            ("Custom Metrics (avg)", "custom_ts_avg"),
            ("Indexed Logs (sum)", "logs_indexed_logs_usage_agg_sum"),
            ("Ingested Events Bytes (sum)", "ingested_events_bytes_agg_sum"),
        ]

        has_data = False
        for label, attr in fields:
            value = getattr(response, attr, None)
            if value is not None:
                has_data = True
                table.add_row(
                    label, f"{value:,}" if isinstance(value, (int, float)) else str(value)
                )

        if not has_data:
            console.print("[dim]No usage data found for the specified period.[/dim]")
        else:
            console.print(table)


@usage.command(name="hosts")
@click.option(
    "--from",
    "from_time",
    default="24h",
    help="Start time (YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, or Nh/Nd). Default: 24h.",
)
@click.option(
    "--to",
    "to_time",
    default="now",
    help="End time. Default: now.",
)
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def hosts_usage(from_time, to_time, format):
    """Show host usage hour by hour."""
    client = get_datadog_client()

    start_hr = _parse_datetime(from_time, default_hours_ago=24)
    end_hr = _parse_datetime(to_time, default_hours_ago=0)

    with console.status("[cyan]Fetching host usage...[/cyan]"):
        response = client.usage.get_usage_hosts(start_hr=start_hr, end_hr=end_hr)

    usage_list = response.usage if hasattr(response, "usage") and response.usage else []

    if format == "json":
        output = []
        for entry in usage_list:
            output.append(
                {
                    "hour": str(getattr(entry, "hour", "")),
                    "host_count": getattr(entry, "host_count", None),
                    "container_count": getattr(entry, "container_count", None),
                    "apm_host_count": getattr(entry, "apm_host_count", None),
                }
            )
        print(json.dumps(output, indent=2, default=str))
    else:
        table = Table(title="Host Usage")
        table.add_column("Hour", style="cyan")
        table.add_column("Hosts", justify="right", style="yellow")
        table.add_column("Containers", justify="right", style="white")
        table.add_column("APM Hosts", justify="right", style="green")

        for entry in usage_list:
            hour = str(getattr(entry, "hour", ""))
            host_count = getattr(entry, "host_count", None)
            container_count = getattr(entry, "container_count", None)
            apm_host_count = getattr(entry, "apm_host_count", None)

            table.add_row(
                hour,
                str(host_count) if host_count is not None else "-",
                str(container_count) if container_count is not None else "-",
                str(apm_host_count) if apm_host_count is not None else "-",
            )

        console.print(table)
        console.print(f"\n[dim]Total entries: {len(usage_list)}[/dim]")


@usage.command(name="logs")
@click.option(
    "--from",
    "from_time",
    default="24h",
    help="Start time (YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, or Nh/Nd). Default: 24h.",
)
@click.option(
    "--to",
    "to_time",
    default="now",
    help="End time. Default: now.",
)
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def logs_usage(from_time, to_time, format):
    """Show log usage hour by hour."""
    client = get_datadog_client()

    start_hr = _parse_datetime(from_time, default_hours_ago=24)
    end_hr = _parse_datetime(to_time, default_hours_ago=0)

    with console.status("[cyan]Fetching log usage...[/cyan]"):
        response = client.usage.get_usage_logs(start_hr=start_hr, end_hr=end_hr)

    usage_list = response.usage if hasattr(response, "usage") and response.usage else []

    if format == "json":
        output = []
        for entry in usage_list:
            output.append(
                {
                    "hour": str(getattr(entry, "hour", "")),
                    "ingested_events_count": getattr(entry, "ingested_events_count", None),
                    "indexed_events_count": getattr(entry, "indexed_events_count", None),
                }
            )
        print(json.dumps(output, indent=2, default=str))
    else:
        table = Table(title="Log Usage")
        table.add_column("Hour", style="cyan")
        table.add_column("Ingested Events", justify="right", style="yellow")
        table.add_column("Indexed Events", justify="right", style="white")

        for entry in usage_list:
            hour = str(getattr(entry, "hour", ""))
            ingested = getattr(entry, "ingested_events_count", None)
            indexed = getattr(entry, "indexed_events_count", None)

            table.add_row(
                hour,
                str(ingested) if ingested is not None else "-",
                str(indexed) if indexed is not None else "-",
            )

        console.print(table)
        console.print(f"\n[dim]Total entries: {len(usage_list)}[/dim]")


@usage.command(name="top-avg-metrics")
@click.option(
    "--month",
    "month_str",
    default=None,
    help="Month in YYYY-MM format. Default: current month.",
)
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def top_avg_metrics(month_str, format):
    """Show top custom metrics by average count."""
    client = get_datadog_client()

    if month_str:
        try:
            month_dt = datetime.strptime(month_str, "%Y-%m")
        except ValueError:
            raise click.BadParameter(
                f"Invalid month format: {month_str}. Use YYYY-MM (e.g., 2024-01)."
            )
    else:
        now = datetime.now()
        month_dt = datetime(now.year, now.month, 1)

    with console.status("[cyan]Fetching top average metrics...[/cyan]"):
        response = client.usage.get_usage_top_avg_metrics(month=month_dt)

    usage_list = response.usage if hasattr(response, "usage") and response.usage else []

    if format == "json":
        output = []
        for entry in usage_list:
            output.append(
                {
                    "metric_name": getattr(entry, "metric_name", None),
                    "avg_metric_hour": getattr(entry, "avg_metric_hour", None),
                    "max_metric_hour": getattr(entry, "max_metric_hour", None),
                    "metric_category": getattr(entry, "metric_category", None),
                }
            )
        print(json.dumps(output, indent=2, default=str))
    else:
        table = Table(title=f"Top Average Metrics ({month_dt.strftime('%Y-%m')})")
        table.add_column("Metric Name", style="cyan", min_width=30)
        table.add_column("Avg/Hour", justify="right", style="yellow")
        table.add_column("Max/Hour", justify="right", style="white")
        table.add_column("Category", style="dim")

        for entry in usage_list:
            name = getattr(entry, "metric_name", None) or ""
            avg_hr = getattr(entry, "avg_metric_hour", None)
            max_hr = getattr(entry, "max_metric_hour", None)
            category = getattr(entry, "metric_category", None) or ""

            table.add_row(
                name,
                str(avg_hr) if avg_hr is not None else "-",
                str(max_hr) if max_hr is not None else "-",
                category,
            )

        console.print(table)
        console.print(f"\n[dim]Total metrics: {len(usage_list)}[/dim]")
