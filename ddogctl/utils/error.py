"""Error handling utilities with retry logic."""

from datadog_api_client.exceptions import ApiException
from rich.console import Console
import sys
import time
from functools import wraps

console = Console()


def handle_api_error(func):
    """Decorator for API error handling with retry logic."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        retries = 3
        retry_delay = 1.0

        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except ApiException as e:
                if e.status == 401:
                    console.print(
                        "[red]✗ Authentication failed. Check DD_API_KEY and DD_APP_KEY[/red]"
                    )
                    sys.exit(1)
                elif e.status == 403:
                    console.print("[red]✗ Permission denied. Check API key permissions[/red]")
                    sys.exit(1)
                elif e.status == 429:
                    # Rate limited - retry with exponential backoff
                    if attempt < retries - 1:
                        wait_time = retry_delay * (2**attempt)
                        console.print(
                            f"[yellow]⚠ Rate limited. Retrying in {wait_time}s...[/yellow]"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        console.print("[red]✗ Rate limited. Maximum retries exceeded.[/red]")
                        sys.exit(1)
                elif e.status >= 500:
                    # Server error - retry
                    if attempt < retries - 1:
                        console.print(
                            f"[yellow]⚠ Server error. Retrying ({attempt + 1}/{retries})...[/yellow]"
                        )
                        time.sleep(retry_delay)
                        continue
                    else:
                        console.print(f"[red]✗ Server error: {e}[/red]")
                        sys.exit(1)
                else:
                    console.print(f"[red]✗ API Error ({e.status}): {e}[/red]")
                    sys.exit(1)
            except Exception as e:
                console.print(f"[red]✗ Unexpected error: {e}[/red]")
                sys.exit(1)

    return wrapper
