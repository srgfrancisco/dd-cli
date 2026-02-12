"""Tests for service-check commands."""

from unittest.mock import Mock, patch
from click.testing import CliRunner
from ddogctl.commands.service_check import service_check


class TestServiceCheckPost:
    """Tests for service-check post command."""

    def setup_method(self):
        self.runner = CliRunner()
        self.mock_client = Mock()
        self.mock_client.service_checks = Mock()

    def _invoke(self, args):
        with patch(
            "ddogctl.commands.service_check.get_datadog_client",
            return_value=self.mock_client,
        ):
            return self.runner.invoke(service_check, args)

    # --- Named status tests ---

    def test_post_named_status_ok(self):
        """Post with named status 'ok' succeeds and shows confirmation."""
        result = self._invoke(["post", "my.check", "myhost", "ok"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "my.check" in result.output
        assert "myhost" in result.output
        assert "ok" in result.output.lower()
        self.mock_client.service_checks.submit_service_check.assert_called_once()

    def test_post_named_status_warning(self):
        """Post with named status 'warning' succeeds."""
        result = self._invoke(["post", "my.check", "myhost", "warning"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "warning" in result.output.lower()
        self.mock_client.service_checks.submit_service_check.assert_called_once()

    def test_post_named_status_critical(self):
        """Post with named status 'critical' succeeds."""
        result = self._invoke(["post", "my.check", "myhost", "critical"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "critical" in result.output.lower()
        self.mock_client.service_checks.submit_service_check.assert_called_once()

    def test_post_named_status_unknown(self):
        """Post with named status 'unknown' succeeds."""
        result = self._invoke(["post", "my.check", "myhost", "unknown"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "unknown" in result.output.lower()
        self.mock_client.service_checks.submit_service_check.assert_called_once()

    # --- Numeric status tests ---

    def test_post_numeric_status_0(self):
        """Post with numeric status '0' maps to ok."""
        result = self._invoke(["post", "my.check", "myhost", "0"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "ok" in result.output.lower()
        self.mock_client.service_checks.submit_service_check.assert_called_once()

    def test_post_numeric_status_1(self):
        """Post with numeric status '1' maps to warning."""
        result = self._invoke(["post", "my.check", "myhost", "1"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "warning" in result.output.lower()
        self.mock_client.service_checks.submit_service_check.assert_called_once()

    def test_post_numeric_status_2(self):
        """Post with numeric status '2' maps to critical."""
        result = self._invoke(["post", "my.check", "myhost", "2"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "critical" in result.output.lower()
        self.mock_client.service_checks.submit_service_check.assert_called_once()

    def test_post_numeric_status_3(self):
        """Post with numeric status '3' maps to unknown."""
        result = self._invoke(["post", "my.check", "myhost", "3"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "unknown" in result.output.lower()
        self.mock_client.service_checks.submit_service_check.assert_called_once()

    # --- Options tests ---

    def test_post_with_message(self):
        """Post with --message option includes it in the API call."""
        result = self._invoke(
            ["post", "my.check", "myhost", "ok", "--message", "Deployment complete"]
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify the message was passed to the API
        call_args = self.mock_client.service_checks.submit_service_check.call_args
        body = call_args.kwargs["body"]
        assert body[0].message == "Deployment complete"

    def test_post_with_tags(self):
        """Post with --tags option parses and includes tags."""
        result = self._invoke(
            ["post", "my.check", "myhost", "ok", "--tags", "env:prod,service:web"]
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify tags were parsed and passed to the API
        call_args = self.mock_client.service_checks.submit_service_check.call_args
        body = call_args.kwargs["body"]
        assert "env:prod" in body[0].tags
        assert "service:web" in body[0].tags

    def test_post_with_message_and_tags(self):
        """Post with both --message and --tags options."""
        result = self._invoke(
            [
                "post",
                "deploy.check",
                "web-01",
                "warning",
                "--message",
                "High latency detected",
                "--tags",
                "env:staging,team:platform",
            ]
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        call_args = self.mock_client.service_checks.submit_service_check.call_args
        body = call_args.kwargs["body"]
        assert body[0].message == "High latency detected"
        assert "env:staging" in body[0].tags
        assert "team:platform" in body[0].tags

    # --- Invalid status tests ---

    def test_post_invalid_status(self):
        """Post with invalid status exits with non-zero code and error message."""
        result = self._invoke(["post", "my.check", "myhost", "invalid"])

        assert result.exit_code != 0, f"Should have failed: {result.output}"
        assert "invalid" in result.output.lower() or "status" in result.output.lower()

    def test_post_invalid_numeric_status(self):
        """Post with out-of-range numeric status exits with error."""
        result = self._invoke(["post", "my.check", "myhost", "5"])

        assert result.exit_code != 0, f"Should have failed: {result.output}"

    # --- API body verification ---

    def test_post_api_called_with_correct_body(self):
        """Verify the API is called with a correctly constructed ServiceCheck body."""
        result = self._invoke(
            [
                "post",
                "app.health",
                "prod-web-01",
                "ok",
                "--message",
                "All systems go",
                "--tags",
                "env:prod",
            ]
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        call_args = self.mock_client.service_checks.submit_service_check.call_args
        body = call_args.kwargs["body"]

        # Body should be a list with one ServiceCheck
        assert len(body) == 1
        check = body[0]
        assert check.check == "app.health"
        assert check.host_name == "prod-web-01"
        assert check.status.value == 0  # ok
        assert check.message == "All systems go"
        assert "env:prod" in check.tags

    def test_post_without_message_sends_empty_string(self):
        """Post without --message sends empty string as message."""
        result = self._invoke(["post", "my.check", "myhost", "ok"])

        assert result.exit_code == 0, f"Command failed: {result.output}"

        call_args = self.mock_client.service_checks.submit_service_check.call_args
        body = call_args.kwargs["body"]
        assert body[0].message == ""

    def test_post_without_tags_sends_empty_list(self):
        """Post without --tags sends empty list as tags."""
        result = self._invoke(["post", "my.check", "myhost", "ok"])

        assert result.exit_code == 0, f"Command failed: {result.output}"

        call_args = self.mock_client.service_checks.submit_service_check.call_args
        body = call_args.kwargs["body"]
        assert body[0].tags == []
