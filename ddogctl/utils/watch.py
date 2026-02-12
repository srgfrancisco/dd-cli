"""Watch mode utility for auto-refreshing CLI output."""

import time

from rich.console import Console
from rich.live import Live


def watch_loop(render_func, interval=30, console=None):
    """Run render_func in a loop, updating the display every interval seconds.

    Uses Rich Live display for smooth in-place terminal updates.
    Exits cleanly on KeyboardInterrupt (Ctrl+C).

    Args:
        render_func: Callable that returns a Rich renderable (Table, Panel, etc.)
        interval: Refresh interval in seconds (default: 30, minimum: 1)
        console: Optional Rich Console instance (default: creates new one)
    """
    if interval < 1:
        interval = 1

    if console is None:
        console = Console()

    try:
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                output = render_func()
                live.update(output)
                time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[dim]Watch stopped[/dim]")
