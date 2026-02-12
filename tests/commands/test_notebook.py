"""Tests for notebook commands."""

import json
import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from ddogctl.commands.notebook import notebook


class TestListNotebooks:
    """Tests for notebook list command."""

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.notebooks = Mock()
        return client

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def _make_notebook(
        self, id, name, author="user@example.com", modified="2025-01-15", status="published"
    ):
        """Create a mock notebook data item."""
        attrs = Mock()
        attrs.name = name
        attrs.author = {"handle": author}
        attrs.cells = [Mock(), Mock()]
        attrs.created = "2025-01-01"
        attrs.modified = modified
        attrs.status = status

        nb = Mock()
        nb.id = id
        nb.type = "notebooks"
        nb.attributes = attrs
        return nb

    def test_list_notebooks_table(self, mock_client, runner):
        """Test listing notebooks in table format."""
        nb1 = self._make_notebook(1, "Investigation Notebook", modified="2025-01-15")
        nb2 = self._make_notebook(
            2, "Performance Analysis", author="admin@example.com", modified="2025-01-20"
        )

        response = Mock()
        response.data = [nb1, nb2]
        mock_client.notebooks.list_notebooks.return_value = response

        with patch("ddogctl.commands.notebook.get_datadog_client", return_value=mock_client):
            result = runner.invoke(notebook, ["list"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Investigation Notebook" in result.output
        assert "Performance Analysis" in result.output
        assert "Total notebooks: 2" in result.output

    def test_list_notebooks_json(self, mock_client, runner):
        """Test listing notebooks in JSON format."""
        nb1 = self._make_notebook(1, "Investigation Notebook")

        response = Mock()
        response.data = [nb1]
        mock_client.notebooks.list_notebooks.return_value = response

        with patch("ddogctl.commands.notebook.get_datadog_client", return_value=mock_client):
            result = runner.invoke(notebook, ["list", "--format", "json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["id"] == 1
        assert output[0]["name"] == "Investigation Notebook"
        assert output[0]["author"] == "user@example.com"

    def test_list_notebooks_empty(self, mock_client, runner):
        """Test listing notebooks when none exist."""
        response = Mock()
        response.data = []
        mock_client.notebooks.list_notebooks.return_value = response

        with patch("ddogctl.commands.notebook.get_datadog_client", return_value=mock_client):
            result = runner.invoke(notebook, ["list"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Total notebooks: 0" in result.output


class TestGetNotebook:
    """Tests for notebook get command."""

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.notebooks = Mock()
        return client

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def _make_notebook_detail(
        self,
        id=1,
        name="Test Notebook",
        author="user@example.com",
        cells=None,
        created="2025-01-01",
        modified="2025-01-15",
        status="published",
    ):
        """Create a mock notebook response for get."""
        attrs = Mock()
        attrs.name = name
        attrs.author = {"handle": author}
        attrs.cells = cells or [Mock(), Mock(), Mock()]
        attrs.created = created
        attrs.modified = modified
        attrs.status = status

        nb = Mock()
        nb.id = id
        nb.type = "notebooks"
        nb.attributes = attrs

        response = Mock()
        response.data = nb
        return response

    def test_get_notebook_table(self, mock_client, runner):
        """Test getting notebook details in table format."""
        response = self._make_notebook_detail(
            id=42, name="Latency Investigation", author="ops@example.com"
        )
        mock_client.notebooks.get_notebook.return_value = response

        with patch("ddogctl.commands.notebook.get_datadog_client", return_value=mock_client):
            result = runner.invoke(notebook, ["get", "42"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Notebook 42" in result.output
        assert "Latency Investigation" in result.output
        assert "ops@example.com" in result.output
        assert "Cells:" in result.output
        mock_client.notebooks.get_notebook.assert_called_once_with(notebook_id=42)

    def test_get_notebook_json(self, mock_client, runner):
        """Test getting notebook details in JSON format."""
        response = self._make_notebook_detail(id=42, name="Latency Investigation")
        mock_client.notebooks.get_notebook.return_value = response

        with patch("ddogctl.commands.notebook.get_datadog_client", return_value=mock_client):
            result = runner.invoke(notebook, ["get", "42", "--format", "json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == 42
        assert output["name"] == "Latency Investigation"
        assert output["cells"] == 3


class TestCreateNotebook:
    """Tests for notebook create command."""

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.notebooks = Mock()
        return client

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_create_notebook(self, mock_client, runner):
        """Test creating a notebook."""
        nb_attrs = Mock()
        nb_attrs.name = "New Notebook"

        nb = Mock()
        nb.id = 99
        nb.attributes = nb_attrs

        response = Mock()
        response.data = nb
        mock_client.notebooks.create_notebook.return_value = response

        with patch("ddogctl.commands.notebook.get_datadog_client", return_value=mock_client):
            result = runner.invoke(notebook, ["create", "--name", "New Notebook"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Notebook 99 created" in result.output
        assert "New Notebook" in result.output
        mock_client.notebooks.create_notebook.assert_called_once()

    def test_create_notebook_json(self, mock_client, runner):
        """Test creating a notebook with JSON output."""
        nb_attrs = Mock()
        nb_attrs.name = "New Notebook"

        nb = Mock()
        nb.id = 99
        nb.attributes = nb_attrs

        response = Mock()
        response.data = nb
        mock_client.notebooks.create_notebook.return_value = response

        with patch("ddogctl.commands.notebook.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                notebook, ["create", "--name", "New Notebook", "--format", "json"]
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == 99
        assert output["name"] == "New Notebook"

    def test_create_notebook_requires_name(self, mock_client, runner):
        """Test that --name is required."""
        with patch("ddogctl.commands.notebook.get_datadog_client", return_value=mock_client):
            result = runner.invoke(notebook, ["create"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()


class TestDeleteNotebook:
    """Tests for notebook delete command."""

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.notebooks = Mock()
        return client

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_delete_notebook_with_confirm(self, mock_client, runner):
        """Test deleting a notebook with --confirm flag (no prompt)."""
        mock_client.notebooks.delete_notebook.return_value = None

        with patch("ddogctl.commands.notebook.get_datadog_client", return_value=mock_client):
            result = runner.invoke(notebook, ["delete", "42", "--confirm"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Notebook 42 deleted" in result.output
        mock_client.notebooks.delete_notebook.assert_called_once_with(notebook_id=42)

    def test_delete_notebook_interactive_yes(self, mock_client, runner):
        """Test deleting a notebook with interactive confirmation (user says yes)."""
        mock_client.notebooks.delete_notebook.return_value = None

        with patch("ddogctl.commands.notebook.get_datadog_client", return_value=mock_client):
            result = runner.invoke(notebook, ["delete", "42"], input="y\n")

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Notebook 42 deleted" in result.output
        mock_client.notebooks.delete_notebook.assert_called_once_with(notebook_id=42)

    def test_delete_notebook_without_confirm(self, mock_client, runner):
        """Test deleting a notebook with interactive confirmation (user says no)."""
        with patch("ddogctl.commands.notebook.get_datadog_client", return_value=mock_client):
            result = runner.invoke(notebook, ["delete", "42"], input="n\n")

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Aborted" in result.output
        mock_client.notebooks.delete_notebook.assert_not_called()
