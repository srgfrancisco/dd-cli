"""Service check commands."""

import click
from rich.console import Console
from ddogctl.client import get_datadog_client
from ddogctl.utils.error import handle_api_error
from ddogctl.utils.tags import parse_tags

console = Console()

STATUS_MAP = {
    "ok": 0,
    "warning": 1,
    "critical": 2,
    "unknown": 3,
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
}

STATUS_NAMES = {0: "OK", 1: "Warning", 2: "Critical", 3: "Unknown"}


@click.group(name="service-check")
def service_check():
    """Service check commands."""
    pass


@service_check.command(name="post")
@click.argument("check_name")
@click.argument("host")
@click.argument("status")
@click.option("--message", default=None, help="Check message/reason")
@click.option("--tags", default=None, help="Tags (comma-separated, e.g. env:prod,service:web)")
@handle_api_error
def post_check(check_name, host, status, message, tags):
    """Post a service check.

    STATUS accepts both named (ok, warning, critical, unknown)
    and numeric (0, 1, 2, 3) values.
    """
    from datadog_api_client.v1.model.service_check import ServiceCheck
    from datadog_api_client.v1.model.service_check_status import ServiceCheckStatus

    status_lower = status.lower()
    if status_lower not in STATUS_MAP:
        valid = ", ".join(sorted(STATUS_MAP.keys()))
        console.print(f"[red]Invalid status '{status}'. Valid values: {valid}[/red]")
        raise SystemExit(1)

    status_int = STATUS_MAP[status_lower]
    status_name = STATUS_NAMES[status_int]
    parsed_tags = parse_tags(tags) if tags else []

    body = [
        ServiceCheck(
            check=check_name,
            host_name=host,
            status=ServiceCheckStatus(status_int),
            message=message or "",
            tags=parsed_tags,
        )
    ]

    client = get_datadog_client()
    client.service_checks.submit_service_check(body=body)

    console.print(f"[green]Service check posted:[/green] {check_name} on {host} = {status_name}")
