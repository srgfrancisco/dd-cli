"""Tests for user management commands."""

import json
from unittest.mock import Mock, patch


def _create_mock_user(user_id, name, email, handle, status, disabled, created_at):
    """Create a mock user data object matching the UsersApi response shape."""
    attrs = Mock()
    attrs.name = name
    attrs.email = email
    attrs.handle = handle
    attrs.status = status
    attrs.disabled = disabled
    attrs.created_at = created_at

    user = Mock()
    user.id = user_id
    user.type = "users"
    user.attributes = attrs
    return user


def test_list_users_table(mock_client, runner):
    """Test listing users in table format."""
    from ddogctl.commands.user import user

    users_data = [
        _create_mock_user(
            "user-1", "Alice Smith", "alice@example.com", "alice", "Active", False, "2024-01-15"
        ),
        _create_mock_user(
            "user-2", "Bob Jones", "bob@example.com", "bob", "Pending", False, "2024-02-20"
        ),
    ]
    mock_client.users.list_users.return_value = Mock(data=users_data)

    with patch("ddogctl.commands.user.get_datadog_client", return_value=mock_client):
        result = runner.invoke(user, ["list"])

    assert result.exit_code == 0
    assert "Users" in result.output
    assert "Alice Smith" in result.output
    assert "alice@example.com" in result.output
    assert "Bob Jones" in result.output
    assert "bob@example.com" in result.output
    assert "Total users: 2" in result.output


def test_list_users_json(mock_client, runner):
    """Test listing users in JSON format."""
    from ddogctl.commands.user import user

    users_data = [
        _create_mock_user(
            "user-1", "Alice Smith", "alice@example.com", "alice", "Active", False, "2024-01-15"
        ),
        _create_mock_user(
            "user-2", "Bob Jones", "bob@example.com", "bob", "Pending", False, "2024-02-20"
        ),
    ]
    mock_client.users.list_users.return_value = Mock(data=users_data)

    with patch("ddogctl.commands.user.get_datadog_client", return_value=mock_client):
        result = runner.invoke(user, ["list", "--format", "json"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert len(output) == 2
    assert output[0]["id"] == "user-1"
    assert output[0]["name"] == "Alice Smith"
    assert output[0]["email"] == "alice@example.com"
    assert output[0]["status"] == "Active"
    assert output[1]["id"] == "user-2"
    assert output[1]["name"] == "Bob Jones"


def test_get_user_table(mock_client, runner):
    """Test getting a single user in table format."""
    from ddogctl.commands.user import user

    mock_user = _create_mock_user(
        "user-1", "Alice Smith", "alice@example.com", "alice", "Active", False, "2024-01-15"
    )
    mock_client.users.get_user.return_value = Mock(data=mock_user)

    with patch("ddogctl.commands.user.get_datadog_client", return_value=mock_client):
        result = runner.invoke(user, ["get", "user-1"])

    assert result.exit_code == 0
    assert "user-1" in result.output
    assert "Alice Smith" in result.output
    assert "alice@example.com" in result.output
    assert "alice" in result.output
    assert "Active" in result.output
    mock_client.users.get_user.assert_called_once_with(user_id="user-1")


def test_get_user_json(mock_client, runner):
    """Test getting a single user in JSON format."""
    from ddogctl.commands.user import user

    mock_user = _create_mock_user(
        "user-1", "Alice Smith", "alice@example.com", "alice", "Active", False, "2024-01-15"
    )
    mock_client.users.get_user.return_value = Mock(data=mock_user)

    with patch("ddogctl.commands.user.get_datadog_client", return_value=mock_client):
        result = runner.invoke(user, ["get", "user-1", "--format", "json"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["id"] == "user-1"
    assert output["name"] == "Alice Smith"
    assert output["email"] == "alice@example.com"
    assert output["handle"] == "alice"
    assert output["status"] == "Active"
    assert output["disabled"] is False


def test_invite_user(mock_client, runner):
    """Test inviting a user."""
    from ddogctl.commands.user import user

    # Mock the create_user response
    created_user = Mock()
    created_user.id = "new-user-123"
    mock_client.users.create_user.return_value = Mock(data=created_user)

    # Mock the send_invitations response
    mock_client.users.send_invitations.return_value = Mock(data=[Mock()])

    with patch("ddogctl.commands.user.get_datadog_client", return_value=mock_client):
        result = runner.invoke(user, ["invite", "--email", "newuser@example.com"])

    assert result.exit_code == 0
    assert "Invitation sent to newuser@example.com" in result.output
    assert "new-user-123" in result.output
    mock_client.users.create_user.assert_called_once()
    mock_client.users.send_invitations.assert_called_once()


def test_invite_user_json(mock_client, runner):
    """Test inviting a user with JSON output."""
    from ddogctl.commands.user import user

    created_user = Mock()
    created_user.id = "new-user-456"
    mock_client.users.create_user.return_value = Mock(data=created_user)
    mock_client.users.send_invitations.return_value = Mock(data=[Mock()])

    with patch("ddogctl.commands.user.get_datadog_client", return_value=mock_client):
        result = runner.invoke(user, ["invite", "--email", "test@example.com", "--format", "json"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["email"] == "test@example.com"
    assert output["user_id"] == "new-user-456"
    assert output["status"] == "invitation_sent"


def test_disable_user_with_confirm(mock_client, runner):
    """Test disabling a user with --confirm flag."""
    from ddogctl.commands.user import user

    mock_client.users.disable_user.return_value = None

    with patch("ddogctl.commands.user.get_datadog_client", return_value=mock_client):
        result = runner.invoke(user, ["disable", "user-1", "--confirm"])

    assert result.exit_code == 0
    assert "User user-1 disabled" in result.output
    mock_client.users.disable_user.assert_called_once_with(user_id="user-1")


def test_disable_user_without_confirm(mock_client, runner):
    """Test disabling a user without --confirm aborts."""
    from ddogctl.commands.user import user

    with patch("ddogctl.commands.user.get_datadog_client", return_value=mock_client):
        result = runner.invoke(user, ["disable", "user-1"], input="n\n")

    assert result.exit_code == 0
    assert "Aborted" in result.output
    mock_client.users.disable_user.assert_not_called()


def test_list_users_empty(mock_client, runner):
    """Test listing users when no users exist."""
    from ddogctl.commands.user import user

    mock_client.users.list_users.return_value = Mock(data=[])

    with patch("ddogctl.commands.user.get_datadog_client", return_value=mock_client):
        result = runner.invoke(user, ["list"])

    assert result.exit_code == 0
    assert "Total users: 0" in result.output
