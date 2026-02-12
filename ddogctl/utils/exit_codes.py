"""Semantic exit codes for machine-readable CLI results."""

# Success
SUCCESS = 0

# General/unexpected error
GENERAL_ERROR = 1

# Authentication or authorization failure (401, 403)
AUTH_ERROR = 2

# Resource not found (404)
NOT_FOUND = 3

# Validation error (400, invalid input)
VALIDATION_ERROR = 4

# Rate limited after all retries exhausted (429)
RATE_LIMITED = 5

# Server error after all retries exhausted (5xx)
SERVER_ERROR = 6


def exit_code_for_status(status: int) -> int:
    """Map HTTP status code to semantic exit code.

    Args:
        status: HTTP status code from API response

    Returns:
        Semantic exit code
    """
    if status in (401, 403):
        return AUTH_ERROR
    elif status == 404:
        return NOT_FOUND
    elif status in (400, 422):
        return VALIDATION_ERROR
    elif status == 429:
        return RATE_LIMITED
    elif status >= 500:
        return SERVER_ERROR
    else:
        return GENERAL_ERROR
