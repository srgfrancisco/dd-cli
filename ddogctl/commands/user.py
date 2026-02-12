"""User management commands."""

import click
import json
from rich.console import Console
from rich.table import Table
from ddogctl.client import get_datadog_client
from ddogctl.utils.error import handle_api_error
from ddogctl.utils.confirm import confirm_action

console = Console()


@click.group()
def user():
    """User management commands."""
    pass


@user.command(name="list")
@click.option(
    "--format", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def list_users(format):
    """List all users in the organization."""
    client = get_datadog_client()

    with console.status("[cyan]Fetching users...[/cyan]"):
        response = client.users.list_users()

    users_data = response.data if response.data else []

    if format == "json":
        output = []
        for u in users_data:
            attrs = u.attributes
            output.append(
                {
                    "id": u.id,
                    "name": getattr(attrs, "name", None),
                    "email": getattr(attrs, "email", None),
                    "handle": getattr(attrs, "handle", None),
                    "status": getattr(attrs, "status", None),
                    "disabled": getattr(attrs, "disabled", None),
                    "created_at": str(getattr(attrs, "created_at", None)),
                }
            )
        print(json.dumps(output, indent=2))
    else:
        table = Table(title="Users")
        table.add_column("Name", style="cyan")
        table.add_column("Email", style="white")
        table.add_column("Status", style="yellow")
        table.add_column("Created At", style="dim")

        for u in users_data:
            attrs = u.attributes
            name = getattr(attrs, "name", "") or ""
            email = getattr(attrs, "email", "") or ""
            status = getattr(attrs, "status", "") or ""
            created_at = str(getattr(attrs, "created_at", "")) or ""

            table.add_row(name, email, status, created_at)

        console.print(table)
        console.print(f"\n[dim]Total users: {len(users_data)}[/dim]")


@user.command(name="get")
@click.argument("user_id")
@click.option(
    "--format", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def get_user(user_id, format):
    """Get user details by ID."""
    client = get_datadog_client()

    with console.status(f"[cyan]Fetching user {user_id}...[/cyan]"):
        response = client.users.get_user(user_id=user_id)

    u = response.data
    attrs = u.attributes

    if format == "json":
        output = {
            "id": u.id,
            "name": getattr(attrs, "name", None),
            "email": getattr(attrs, "email", None),
            "handle": getattr(attrs, "handle", None),
            "status": getattr(attrs, "status", None),
            "disabled": getattr(attrs, "disabled", None),
            "created_at": str(getattr(attrs, "created_at", None)),
        }
        print(json.dumps(output, indent=2))
    else:
        console.print(f"\n[bold cyan]User {u.id}[/bold cyan]")
        console.print(f"[bold]Name:[/bold] {getattr(attrs, 'name', 'N/A')}")
        console.print(f"[bold]Email:[/bold] {getattr(attrs, 'email', 'N/A')}")
        console.print(f"[bold]Handle:[/bold] {getattr(attrs, 'handle', 'N/A')}")
        console.print(f"[bold]Status:[/bold] {getattr(attrs, 'status', 'N/A')}")
        console.print(f"[bold]Disabled:[/bold] {getattr(attrs, 'disabled', 'N/A')}")
        console.print(f"[bold]Created At:[/bold] {getattr(attrs, 'created_at', 'N/A')}")


@user.command(name="invite")
@click.option("--email", required=True, help="Email address to invite")
@click.option("--role", default=None, help="Role to assign to the invited user")
@click.option(
    "--format", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def invite_user(email, role, format):
    """Send a user invitation."""
    from datadog_api_client.v2.model.user_invitation_data import UserInvitationData
    from datadog_api_client.v2.model.user_invitation_relationships import (
        UserInvitationRelationships,
    )
    from datadog_api_client.v2.model.user_invitations_request import UserInvitationsRequest
    from datadog_api_client.v2.model.relationship_to_user import RelationshipToUser
    from datadog_api_client.v2.model.relationship_to_user_data import RelationshipToUserData
    from datadog_api_client.v2.model.user_create_request import UserCreateRequest
    from datadog_api_client.v2.model.user_create_data import UserCreateData
    from datadog_api_client.v2.model.user_create_attributes import UserCreateAttributes
    from datadog_api_client.v2.model.users_type import UsersType

    client = get_datadog_client()

    # First create the user
    user_attributes = UserCreateAttributes(email=email)
    user_data = UserCreateData(
        type=UsersType("users"),
        attributes=user_attributes,
    )
    user_request = UserCreateRequest(data=user_data)

    with console.status(f"[cyan]Creating user and sending invitation to {email}...[/cyan]"):
        create_response = client.users.create_user(body=user_request)
        new_user = create_response.data

        # Now send invitation
        invitation_data = UserInvitationData(
            type="user_invitations",
            relationships=UserInvitationRelationships(
                user=RelationshipToUser(
                    data=RelationshipToUserData(
                        id=new_user.id,
                        type=UsersType("users"),
                    )
                )
            ),
        )
        body = UserInvitationsRequest(data=[invitation_data])
        client.users.send_invitations(body=body)

    if format == "json":
        output = {
            "email": email,
            "user_id": new_user.id,
            "status": "invitation_sent",
        }
        print(json.dumps(output, indent=2))
    else:
        console.print(f"[green]Invitation sent to {email}[/green]")
        console.print(f"[dim]User ID: {new_user.id}[/dim]")


@user.command(name="disable")
@click.argument("user_id")
@click.option("--confirm", "confirmed", is_flag=True, help="Skip confirmation prompt")
@handle_api_error
def disable_user(user_id, confirmed):
    """Disable a user by ID."""
    if not confirm_action(f"Disable user {user_id}?", confirmed):
        console.print("[yellow]Aborted[/yellow]")
        return

    client = get_datadog_client()

    with console.status(f"[cyan]Disabling user {user_id}...[/cyan]"):
        client.users.disable_user(user_id=user_id)

    console.print(f"[green]User {user_id} disabled[/green]")
