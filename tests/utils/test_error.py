"""Tests for error handling utilities."""

import pytest
from unittest.mock import patch
from datadog_api_client.exceptions import ApiException
from ddg.utils.error import handle_api_error


class TestHandleApiError:
    """Test suite for handle_api_error decorator."""

    @pytest.fixture
    def mock_console(self):
        """Mock rich Console for capturing output."""
        with patch("ddg.utils.error.console") as mock:
            yield mock

    @pytest.fixture
    def mock_sleep(self):
        """Mock time.sleep to avoid delays in tests."""
        with patch("ddg.utils.error.time.sleep") as mock:
            yield mock

    def test_successful_call_no_error(self, mock_console):
        """Test that successful function calls work normally."""

        @handle_api_error
        def successful_func():
            return "success"

        result = successful_func()
        assert result == "success"
        # Console should not be called for successful operations
        mock_console.print.assert_not_called()

    def test_successful_call_with_args_and_kwargs(self, mock_console):
        """Test that decorator preserves function arguments."""

        @handle_api_error
        def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = func_with_args("x", "y", c="z")
        assert result == "x-y-z"
        mock_console.print.assert_not_called()

    def test_401_authentication_error(self, mock_console):
        """Test that 401 errors trigger authentication message and exit."""

        @handle_api_error
        def auth_error_func():
            raise ApiException(status=401, reason="Unauthorized")

        with pytest.raises(SystemExit) as exc_info:
            auth_error_func()

        assert exc_info.value.code == 1
        mock_console.print.assert_called_once()
        call_arg = mock_console.print.call_args[0][0]
        assert "Authentication failed" in call_arg
        assert "DD_API_KEY" in call_arg or "DD_APP_KEY" in call_arg

    def test_403_permission_error(self, mock_console):
        """Test that 403 errors trigger permission message and exit."""

        @handle_api_error
        def permission_error_func():
            raise ApiException(status=403, reason="Forbidden")

        with pytest.raises(SystemExit) as exc_info:
            permission_error_func()

        assert exc_info.value.code == 1
        mock_console.print.assert_called_once()
        call_arg = mock_console.print.call_args[0][0]
        assert "Permission denied" in call_arg

    def test_429_rate_limit_with_retry(self, mock_console, mock_sleep):
        """Test that 429 errors trigger retry with exponential backoff."""
        call_count = 0

        @handle_api_error
        def rate_limited_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ApiException(status=429, reason="Rate Limited")
            return "success"

        result = rate_limited_func()

        # Should succeed on third attempt
        assert result == "success"
        assert call_count == 3

        # Should have slept twice (before 2nd and 3rd attempts)
        assert mock_sleep.call_count == 2

        # Check exponential backoff: 1s * 2^0 = 1s, then 1s * 2^1 = 2s
        sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
        assert sleep_calls == [1.0, 2.0]

        # Should have printed rate limit warnings
        assert mock_console.print.call_count >= 2
        print_calls = [c[0][0] for c in mock_console.print.call_args_list]
        rate_limit_warnings = [c for c in print_calls if "Rate limited" in c]
        assert len(rate_limit_warnings) == 2

    def test_429_rate_limit_max_retries_exceeded(self, mock_console, mock_sleep):
        """Test that 429 errors exit after max retries."""

        @handle_api_error
        def always_rate_limited():
            raise ApiException(status=429, reason="Rate Limited")

        with pytest.raises(SystemExit) as exc_info:
            always_rate_limited()

        assert exc_info.value.code == 1

        # Should have attempted 3 times (initial + 2 retries)
        # and slept 2 times (before 2nd and 3rd attempts)
        assert mock_sleep.call_count == 2

        # Final error message should indicate max retries exceeded
        final_call = mock_console.print.call_args_list[-1][0][0]
        assert "Maximum retries exceeded" in final_call or "Rate limited" in final_call

    def test_500_server_error_with_retry(self, mock_console, mock_sleep):
        """Test that 5xx errors trigger retry."""
        call_count = 0

        @handle_api_error
        def server_error_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ApiException(status=500, reason="Internal Server Error")
            return "success"

        result = server_error_func()

        # Should succeed on second attempt
        assert result == "success"
        assert call_count == 2

        # Should have slept once (before 2nd attempt)
        mock_sleep.assert_called_once_with(1.0)

        # Should have printed server error warning
        print_calls = [c[0][0] for c in mock_console.print.call_args_list]
        server_error_warnings = [c for c in print_calls if "Server error" in c]
        assert len(server_error_warnings) >= 1

    def test_503_service_unavailable_retry(self, mock_console, mock_sleep):
        """Test that 503 errors (5xx) trigger retry."""
        call_count = 0

        @handle_api_error
        def service_unavailable_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ApiException(status=503, reason="Service Unavailable")
            return "success"

        result = service_unavailable_func()
        assert result == "success"
        assert call_count == 2

    def test_server_error_max_retries_exceeded(self, mock_console, mock_sleep):
        """Test that server errors exit after max retries."""

        @handle_api_error
        def always_server_error():
            raise ApiException(status=500, reason="Internal Server Error")

        with pytest.raises(SystemExit) as exc_info:
            always_server_error()

        assert exc_info.value.code == 1

        # Should have retried 3 times total
        # Should have slept 2 times (before 2nd and 3rd attempts)
        assert mock_sleep.call_count == 2

        # Final error should mention server error
        final_call = mock_console.print.call_args_list[-1][0][0]
        assert "Server error" in final_call

    def test_400_client_error_no_retry(self, mock_console, mock_sleep):
        """Test that 4xx errors (except 429) don't retry."""

        @handle_api_error
        def bad_request_func():
            raise ApiException(status=400, reason="Bad Request")

        with pytest.raises(SystemExit) as exc_info:
            bad_request_func()

        assert exc_info.value.code == 1

        # Should NOT retry
        mock_sleep.assert_not_called()

        # Should print API error
        mock_console.print.assert_called_once()
        call_arg = mock_console.print.call_args[0][0]
        assert "API Error (400)" in call_arg

    def test_404_not_found_no_retry(self, mock_console, mock_sleep):
        """Test that 404 errors don't retry."""

        @handle_api_error
        def not_found_func():
            raise ApiException(status=404, reason="Not Found")

        with pytest.raises(SystemExit) as exc_info:
            not_found_func()

        assert exc_info.value.code == 1
        mock_sleep.assert_not_called()

        call_arg = mock_console.print.call_args[0][0]
        assert "API Error (404)" in call_arg

    def test_generic_exception_handling(self, mock_console):
        """Test that non-ApiException errors are caught and logged."""

        @handle_api_error
        def generic_error_func():
            raise RuntimeError("Something went wrong")

        with pytest.raises(SystemExit) as exc_info:
            generic_error_func()

        assert exc_info.value.code == 1

        mock_console.print.assert_called_once()
        call_arg = mock_console.print.call_args[0][0]
        assert "Unexpected error" in call_arg
        assert "Something went wrong" in call_arg

    def test_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""

        @handle_api_error
        def documented_func():
            """This is a test function."""
            return "test"

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is a test function."

    def test_different_api_exception_messages(self, mock_console):
        """Test that exception messages are included in error output."""

        @handle_api_error
        def custom_error_func():
            raise ApiException(
                status=400,
                reason="Bad Request",
            )

        with pytest.raises(SystemExit):
            custom_error_func()

        # Error message should be in the output
        call_arg = mock_console.print.call_args[0][0]
        assert "400" in call_arg

    def test_multiple_function_applications(self, mock_console):
        """Test that decorator can be applied to multiple functions."""

        @handle_api_error
        def func1():
            return "func1"

        @handle_api_error
        def func2():
            return "func2"

        assert func1() == "func1"
        assert func2() == "func2"

        # No errors should be printed
        mock_console.print.assert_not_called()

    def test_nested_decorator_application(self, mock_console):
        """Test behavior when decorator is used with other decorators."""

        def other_decorator(func):
            def wrapper(*args, **kwargs):
                return f"wrapped: {func(*args, **kwargs)}"

            return wrapper

        @handle_api_error
        @other_decorator
        def nested_func():
            return "test"

        result = nested_func()
        assert result == "wrapped: test"

    def test_retry_count_tracking(self, mock_console, mock_sleep):
        """Test that retry attempts are properly tracked in log messages."""
        call_count = 0

        @handle_api_error
        def intermittent_server_error():
            nonlocal call_count
            call_count += 1
            # Fail twice, succeed on third
            if call_count <= 2:
                raise ApiException(status=500, reason="Server Error")
            return "success"

        result = intermittent_server_error()
        assert result == "success"

        # Check that retry messages include attempt numbers
        print_calls = [c[0][0] for c in mock_console.print.call_args_list]
        retry_messages = [c for c in print_calls if "Retrying" in c]

        # Should have 2 retry messages (for attempts 1 and 2)
        assert len(retry_messages) == 2

        # First retry message should show (1/3)
        assert "(1/3)" in retry_messages[0]
        # Second retry message should show (2/3)
        assert "(2/3)" in retry_messages[1]

    def test_exception_with_no_status_attribute(self, mock_console):
        """Test handling of exceptions that don't have a status attribute."""

        # Create a custom exception without status
        class CustomException(Exception):
            pass

        @handle_api_error
        def custom_exception_func():
            raise CustomException("Custom error")

        with pytest.raises(SystemExit) as exc_info:
            custom_exception_func()

        assert exc_info.value.code == 1

        # Should be caught as unexpected error
        call_arg = mock_console.print.call_args[0][0]
        assert "Unexpected error" in call_arg
