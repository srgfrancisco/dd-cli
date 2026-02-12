"""Tests for semantic exit codes."""

from ddogctl.utils.exit_codes import (
    SUCCESS,
    GENERAL_ERROR,
    AUTH_ERROR,
    NOT_FOUND,
    VALIDATION_ERROR,
    RATE_LIMITED,
    SERVER_ERROR,
    exit_code_for_status,
)


class TestExitCodeConstants:
    def test_success_is_zero(self):
        assert SUCCESS == 0

    def test_general_error_is_one(self):
        assert GENERAL_ERROR == 1

    def test_auth_error_is_two(self):
        assert AUTH_ERROR == 2

    def test_not_found_is_three(self):
        assert NOT_FOUND == 3

    def test_validation_error_is_four(self):
        assert VALIDATION_ERROR == 4

    def test_rate_limited_is_five(self):
        assert RATE_LIMITED == 5

    def test_server_error_is_six(self):
        assert SERVER_ERROR == 6


class TestExitCodeForStatus:
    def test_401_returns_auth_error(self):
        assert exit_code_for_status(401) == AUTH_ERROR

    def test_403_returns_auth_error(self):
        assert exit_code_for_status(403) == AUTH_ERROR

    def test_404_returns_not_found(self):
        assert exit_code_for_status(404) == NOT_FOUND

    def test_400_returns_validation_error(self):
        assert exit_code_for_status(400) == VALIDATION_ERROR

    def test_422_returns_validation_error(self):
        assert exit_code_for_status(422) == VALIDATION_ERROR

    def test_429_returns_rate_limited(self):
        assert exit_code_for_status(429) == RATE_LIMITED

    def test_500_returns_server_error(self):
        assert exit_code_for_status(500) == SERVER_ERROR

    def test_502_returns_server_error(self):
        assert exit_code_for_status(502) == SERVER_ERROR

    def test_503_returns_server_error(self):
        assert exit_code_for_status(503) == SERVER_ERROR

    def test_unknown_status_returns_general_error(self):
        assert exit_code_for_status(418) == GENERAL_ERROR
