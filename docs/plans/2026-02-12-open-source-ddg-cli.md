# Open-Source ddogctl Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for Tasks 4-6.

**Goal:** Transform dd-cli from a Kojo-internal tool into an open-source Datadog CLI (`ddogctl`) with logs, DBM, and investigation commands, publishable to PyPI.

**Architecture:** Click CLI with command groups, each backed by the `datadog-api-client` SDK via a unified `DatadogClient` wrapper. Rich tables for output. Pydantic for config. `@handle_api_error` decorator for retry logic.

**Tech Stack:** Python 3.10+, Click, Rich, datadog-api-client, Pydantic, pytest

**Reference implementation:** `ddg/commands/apm.py` + `tests/commands/test_apm.py` — follow this pattern exactly for all new commands.

---

## Task 1: Rename `dd` → `ddg`

**Files:**
- Rename: `dd/` → `ddg/` (entire directory)
- Modify: `pyproject.toml`
- Modify: All `.py` files under `ddg/` (update internal imports)
- Modify: All `.py` files under `tests/` (update imports and patch targets)
- Delete: `scripts/dd_cli.sh`

**Step 1: Rename the directory**

```bash
cd /Users/sergio.francisco/code/kojo/infrastructure/dd-cli
mv dd ddg
```

**Step 2: Update all `from dd.` imports in source files**

Replace `from dd.` with `from ddg.` in every file under `ddg/`:

- `ddg/cli.py` lines 31-35: `from dd.commands.X` → `from ddg.commands.X`
- `ddg/client.py` lines 12,46: `from dd.config` → `from ddg.config`
- `ddg/commands/apm.py` lines 8-10: `from dd.client` / `from dd.utils.X` → `from ddg.client` / `from ddg.utils.X`
- `ddg/commands/event.py` lines 7-9: same pattern
- `ddg/commands/host.py` lines 7-8: same pattern
- `ddg/commands/metric.py` lines 7-9: same pattern
- `ddg/commands/monitor.py` lines 8-10: same pattern

**Step 3: Update all imports and patch targets in test files**

Replace `from dd.` with `from ddg.` and `'dd.` / `"dd.` with `'ddg.` / `"ddg.` in:

- `tests/commands/test_apm.py`: line 12 import, all `patch('dd.commands.apm.` → `patch('ddg.commands.apm.`
- `tests/commands/test_event.py`: line 7 import, all `patch("dd.commands.event.` → `patch("ddg.commands.event.`
- `tests/commands/test_host.py`: line 6 import, all `patch('dd.commands.host.` → `patch('ddg.commands.host.`
- `tests/commands/test_metric.py`: line 7 import, all `patch("dd.commands.metric.` → `patch("ddg.commands.metric.`
- `tests/commands/test_monitor.py`: line 7 import, all `patch('dd.commands.monitor.` → `patch('ddg.commands.monitor.`
- `tests/test_client.py`: lines 5-6 imports, all `patch('dd.client.` and `patch('dd.config.` → `patch('ddg.client.` / `patch('ddg.config.`
- `tests/test_config.py`: line 6 import, `patch('dd.config.` → `patch('ddg.config.`
- `tests/utils/test_error.py`: line 6 import, `patch('dd.utils.error.` → `patch('ddg.utils.error.`
- `tests/utils/test_tags.py`: line 4 import
- `tests/utils/test_time.py`: line 6 import, all `patch('dd.utils.time.` → `patch('ddg.utils.time.`

**Step 4: Update pyproject.toml**

```toml
[tool.setuptools]
packages = ["ddg", "ddg.commands", "ddg.formatters", "ddg.models", "ddg.utils"]

[project]
name = "ddogctl"
description = "A modern CLI for the Datadog API. Like Dogshell, but better."

[project.scripts]
ddg = "ddg.cli:main"
```

**Step 5: Reinstall and run tests**

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

Expected: 176 passed

**Step 6: Delete shell wrapper**

```bash
rm scripts/dd_cli.sh
rmdir scripts/
```

**Step 7: Commit**

```bash
git add -A
git commit -m "refactor: rename ddg to ddogctl

Rename package and CLI from ddg to ddogctl.
CLI entry point: ddogctl. PyPI name: ddogctl."
```

---

## Task 2: Genericize (Remove Kojo References)

**Files:**
- Modify: `ddg/cli.py:12` — remove "Kojo troubleshooting"
- Modify: `CLAUDE.md:7` — update description
- Delete: `MIGRATION_GUIDE.md`
- Modify: `IMPLEMENTATION_PLAN.md` — update references

**Step 1: Update CLI docstring**

In `ddg/cli.py`, change the main docstring from:
```python
"""Datadog CLI for Kojo troubleshooting.
```
to:
```python
"""A modern CLI for the Datadog API.
```

Also update the description body to be generic (remove Kojo-specific text).

**Step 2: Update CLAUDE.md**

Replace "DD CLI is a Python CLI tool for querying Datadog APIs, built for Kojo troubleshooting." with "ddogctl is a modern CLI for the Datadog API. Like Dogshell, but better." Update all command references to `ddogctl`.

**Step 3: Delete MIGRATION_GUIDE.md**

```bash
rm MIGRATION_GUIDE.md
```

**Step 4: Update pyproject.toml description**

Already done in Task 1. Verify it says: `description = "A modern CLI for the Datadog API. Like Dogshell, but better."`

**Step 5: Run tests**

```bash
pytest tests/ -v
```

Expected: 176 passed (no functional changes)

**Step 6: Commit**

```bash
git add -A
git commit -m "chore: remove Kojo-specific references, genericize for open source"
```

---

## Task 3: Open-Source Scaffolding

**Files:**
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `.github/workflows/ci.yml`
- Rewrite: `README.md`
- Modify: `pyproject.toml` (metadata additions)

**Step 1: Create LICENSE**

Create `LICENSE` with MIT license, year 2026, author name from git config.

**Step 2: Create CONTRIBUTING.md**

```markdown
# Contributing to ddogctl

## Setup

\```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
\```

## Development (TDD)

We follow strict RED-GREEN-REFACTOR:

1. Write a failing test in `tests/`
2. Run it: `pytest tests/commands/test_<module>.py::<test_name> -v`
3. Write minimal code to make it pass
4. Run all tests: `pytest tests/ -v`
5. Check coverage: `pytest tests/ --cov=ddg --cov-report=term-missing`

Target: >90% coverage on all modules.

## Code Quality

\```bash
black ddg/ tests/          # Format (line-length: 100)
ruff check ddg/ tests/     # Lint
mypy ddg/                  # Type check
\```

## Pull Requests

- One feature per PR
- All tests must pass
- Include tests for new functionality
- Follow existing patterns (see `ddg/commands/apm.py` as reference)
```

**Step 3: Create .github/workflows/ci.yml**

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: black --check ddg/ tests/
      - run: ruff check ddg/ tests/
      - run: pytest tests/ -v --cov=ddg --cov-report=xml
  publish:
    needs: test
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

**Step 4: Rewrite README.md**

Full rewrite with:
- Title: "ddogctl"
- Tagline: "A modern CLI for the Datadog API. Like Dogshell, but better."
- Badges: CI, PyPI version, Python versions, License
- Feature comparison table (ddg vs Dogshell)
- Install: `pip install ddogctl` / `pipx install ddogctl`
- Quick start with config and example commands
- Full command reference with all subcommands
- Contributing link

**Step 5: Update pyproject.toml metadata**

Add to `[project]`:
```toml
license = {text = "MIT"}
readme = "README.md"
keywords = ["datadog", "cli", "monitoring", "observability", "apm", "logs"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: System :: Monitoring",
]

[project.urls]
Homepage = "https://github.com/srgfrancisco/ddogctl"
Issues = "https://github.com/srgfrancisco/ddogctl/issues"
```

**Step 6: Run tests**

```bash
pytest tests/ -v
```

Expected: 176 passed

**Step 7: Commit**

```bash
git add -A
git commit -m "chore: add open-source scaffolding (LICENSE, CI, README, CONTRIBUTING)"
```

---

## Task 4: Phase 1 — Logs Commands (TDD)

> **REQUIRED:** Use superpowers:test-driven-development skill for this task.

**Files:**
- Create: `ddg/commands/logs.py`
- Create: `tests/commands/test_logs.py`
- Modify: `ddg/cli.py` (register logs group)
- Modify: `tests/conftest.py` (add `create_mock_log` factory)

**Architecture:** The `DatadogClient` already has `self.logs` (LogsApi from v2). Logs commands use `client.logs.list_logs()` for search/tail/trace and `client.logs.aggregate_logs()` for query analytics.

### Step 1: Add mock factory to conftest.py

Add to `tests/conftest.py`:

```python
def create_mock_log(message, service, status, timestamp, attributes=None, trace_id=None):
    """Factory for mock log objects."""
    class MockLog:
        def __init__(self):
            self.id = f"log-{hash(message) % 10000}"
            self.type = "log"
            self.attributes = Mock(
                message=message,
                service=service,
                status=status,
                timestamp=timestamp,
                attributes=attributes or {},
                tags=[f"service:{service}"],
            )
            if trace_id:
                self.attributes.attributes = {"trace_id": trace_id, **(attributes or {})}
        def to_dict(self):
            return {
                "id": self.id,
                "attributes": {
                    "message": self.attributes.message,
                    "service": self.attributes.service,
                    "status": self.attributes.status,
                    "timestamp": str(self.attributes.timestamp),
                }
            }
    return MockLog()
```

### Step 2: Register logs in cli.py

Add to `ddg/cli.py`:
```python
from ddg.commands.logs import logs
main.add_command(logs)
```

### Sub-task 4a: `ddg logs search` (8 tests, TDD)

**Test file:** `tests/commands/test_logs.py`

Follow this TDD cycle for each test. Pattern mirrors `test_apm.py`:

```python
"""Tests for logs commands."""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from tests.conftest import create_mock_log


def test_logs_search_basic_query(mock_client, runner):
    """Test basic log search returns results."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Connection error", "api-service", "error", now),
        create_mock_log("Request completed", "api-service", "info", now),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch('ddg.commands.logs.get_datadog_client', return_value=mock_client):
        result = runner.invoke(logs, ['search', 'service:api-service', '--format', 'json'])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 2


def test_logs_search_table_format(mock_client, runner):
    """Test log search displays table with columns."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Error occurred", "web-service", "error", now),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch('ddg.commands.logs.get_datadog_client', return_value=mock_client):
        result = runner.invoke(logs, ['search', '*'])
        assert result.exit_code == 0
        assert "Logs" in result.output
        assert "Error occurred" in result.output


def test_logs_search_json_format(mock_client, runner):
    """Test log search outputs valid JSON."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Test message", "my-api", "info", now),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch('ddg.commands.logs.get_datadog_client', return_value=mock_client):
        result = runner.invoke(logs, ['search', '*', '--format', 'json'])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output[0]['message'] == "Test message"
        assert output[0]['service'] == "my-api"
        assert output[0]['status'] == "info"


def test_logs_search_with_time_range(mock_client, runner):
    """Test log search passes time range to API."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch('ddg.commands.logs.get_datadog_client', return_value=mock_client):
        result = runner.invoke(logs, ['search', '*', '--from', '24h'])
        assert result.exit_code == 0
        mock_client.logs.list_logs.assert_called_once()


def test_logs_search_with_service_filter(mock_client, runner):
    """Test log search with service filter."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Filtered log", "target-service", "info", now),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch('ddg.commands.logs.get_datadog_client', return_value=mock_client):
        result = runner.invoke(logs, ['search', '*', '--service', 'target-service', '--format', 'json'])
        assert result.exit_code == 0
        # Verify service was added to query
        call_kwargs = mock_client.logs.list_logs.call_args
        body = call_kwargs.kwargs.get('body') or call_kwargs[0][0] if call_kwargs[0] else call_kwargs.kwargs['body']
        assert 'target-service' in str(body)


def test_logs_search_with_status_filter(mock_client, runner):
    """Test log search with status filter."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch('ddg.commands.logs.get_datadog_client', return_value=mock_client):
        result = runner.invoke(logs, ['search', '*', '--status', 'error'])
        assert result.exit_code == 0
        call_kwargs = mock_client.logs.list_logs.call_args
        body = call_kwargs.kwargs.get('body') or call_kwargs[0][0] if call_kwargs[0] else call_kwargs.kwargs['body']
        assert 'error' in str(body)


def test_logs_search_empty_results(mock_client, runner):
    """Test log search with no results."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch('ddg.commands.logs.get_datadog_client', return_value=mock_client):
        result = runner.invoke(logs, ['search', 'nonexistent'])
        assert result.exit_code == 0
        assert "Total logs: 0" in result.output


def test_logs_search_with_limit(mock_client, runner):
    """Test log search respects limit parameter."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch('ddg.commands.logs.get_datadog_client', return_value=mock_client):
        result = runner.invoke(logs, ['search', '*', '--limit', '10'])
        assert result.exit_code == 0
        call_kwargs = mock_client.logs.list_logs.call_args
        body = call_kwargs.kwargs.get('body') or call_kwargs[0][0] if call_kwargs[0] else call_kwargs.kwargs['body']
        assert body.get('page', {}).get('limit') == 10 or 'limit' in str(body)
```

**Implementation:** `ddg/commands/logs.py`

```python
"""Logs commands."""

import click
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from ddg.client import get_datadog_client
from ddg.utils.error import handle_api_error
from ddg.utils.time import parse_time_range

console = Console()


@click.group()
def logs():
    """Log querying and analytics."""
    pass


@logs.command(name="search")
@click.argument("query")
@click.option("--from", "from_time", default="1h", help="Start time (e.g., 1h, 24h, 7d)")
@click.option("--to", "to_time", default="now", help="End time")
@click.option("--service", help="Filter by service name")
@click.option("--status", help="Filter by status (info, warn, error)")
@click.option("--limit", default=50, type=int, help="Max logs to return")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def search_logs(query, from_time, to_time, service, status, limit, format):
    """Search logs with filters."""
    client = get_datadog_client()

    from_ts, to_ts = parse_time_range(from_time, to_time)
    from_str = datetime.fromtimestamp(from_ts).isoformat() + "Z"
    to_str = datetime.fromtimestamp(to_ts).isoformat() + "Z"

    # Build query with filters
    full_query = query
    if service:
        full_query = f"{full_query} service:{service}"
    if status:
        full_query = f"{full_query} status:{status}"

    body = {
        "filter": {
            "query": full_query,
            "from": from_str,
            "to": to_str,
        },
        "page": {"limit": limit},
        "sort": "-timestamp",
    }

    with console.status("[cyan]Searching logs...[/cyan]"):
        response = client.logs.list_logs(body=body)

    logs_data = response.data if response.data else []

    if format == "json":
        output = []
        for log in logs_data:
            attrs = log.attributes
            output.append({
                "message": attrs.message,
                "service": attrs.service,
                "status": attrs.status,
                "timestamp": str(attrs.timestamp),
            })
        print(json.dumps(output, indent=2, default=str))
    else:
        table = Table(title="Logs")
        table.add_column("Time", style="dim", width=12)
        table.add_column("Status", width=7)
        table.add_column("Service", style="cyan", width=20)
        table.add_column("Message", style="white")

        for log in logs_data:
            attrs = log.attributes
            status_str = str(attrs.status)
            if status_str == "error":
                status_style = f"[red]{status_str}[/red]"
            elif status_str == "warn":
                status_style = f"[yellow]{status_str}[/yellow]"
            else:
                status_style = f"[cyan]{status_str}[/cyan]"

            time_str = attrs.timestamp.strftime("%H:%M:%S") if hasattr(attrs.timestamp, 'strftime') else str(attrs.timestamp)[:8]
            table.add_row(time_str, status_style, str(attrs.service), str(attrs.message)[:80])

        console.print(table)
        console.print(f"\n[dim]Total logs: {len(logs_data)}[/dim]")
```

**TDD cycle for each test:**
1. Write one test → run `pytest tests/commands/test_logs.py::<test_name> -v` → verify FAIL
2. Add minimal code to `ddg/commands/logs.py` → run same test → verify PASS
3. Run full suite: `pytest tests/ -v` → verify no regressions

**After all 8 search tests pass, commit:**
```bash
git add ddg/commands/logs.py tests/commands/test_logs.py tests/conftest.py ddg/cli.py
git commit -m "feat: add logs search command with filters and time range"
```

### Sub-task 4b: `ddg logs tail` (5 tests, TDD)

Append to `tests/commands/test_logs.py`:

```python
def test_logs_tail_basic(mock_client, runner):
    """Test basic log tailing."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Recent log 1", "my-api", "info", now),
        create_mock_log("Recent log 2", "my-api", "error", now),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch('ddg.commands.logs.get_datadog_client', return_value=mock_client):
        result = runner.invoke(logs, ['tail', 'service:my-api'])
        assert result.exit_code == 0
        assert "Recent log 1" in result.output
        assert "Recent log 2" in result.output


def test_logs_tail_with_lines(mock_client, runner):
    """Test tail respects --lines parameter."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch('ddg.commands.logs.get_datadog_client', return_value=mock_client):
        result = runner.invoke(logs, ['tail', '*', '--lines', '20'])
        assert result.exit_code == 0


def test_logs_tail_with_service_filter(mock_client, runner):
    """Test tail with service filter."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch('ddg.commands.logs.get_datadog_client', return_value=mock_client):
        result = runner.invoke(logs, ['tail', '*', '--service', 'web-service'])
        assert result.exit_code == 0


def test_logs_tail_color_coded_output(mock_client, runner):
    """Test tail color-codes by log level."""
    from ddg.commands.logs import logs

    now = datetime.now()
    mock_logs = [
        create_mock_log("Error msg", "my-api", "error", now),
        create_mock_log("Info msg", "my-api", "info", now),
    ]
    mock_response = Mock(data=mock_logs, meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch('ddg.commands.logs.get_datadog_client', return_value=mock_client):
        result = runner.invoke(logs, ['tail', '*'])
        assert result.exit_code == 0
        assert "Error msg" in result.output
        assert "Info msg" in result.output


def test_logs_tail_empty(mock_client, runner):
    """Test tail with no logs."""
    from ddg.commands.logs import logs

    mock_response = Mock(data=[], meta=Mock(page=Mock(after=None)))
    mock_client.logs.list_logs.return_value = mock_response

    with patch('ddg.commands.logs.get_datadog_client', return_value=mock_client):
        result = runner.invoke(logs, ['tail', '*'])
        assert result.exit_code == 0
        assert "No logs found" in result.output or "Total" in result.output
```

**Implementation:** Add `tail` command to `ddg/commands/logs.py`:

```python
@logs.command(name="tail")
@click.argument("query")
@click.option("--lines", default=50, type=int, help="Number of recent logs")
@click.option("--service", help="Filter by service name")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def tail_logs(query, lines, service, format):
    """Show recent logs (newest first)."""
    client = get_datadog_client()

    full_query = query
    if service:
        full_query = f"{full_query} service:{service}"

    body = {
        "filter": {
            "query": full_query,
            "from": "now-15m",
            "to": "now",
        },
        "page": {"limit": lines},
        "sort": "-timestamp",
    }

    with console.status("[cyan]Fetching recent logs...[/cyan]"):
        response = client.logs.list_logs(body=body)

    logs_data = response.data if response.data else []
    # ... same output logic as search, with color coding
```

**Commit after passing:**
```bash
git add ddg/commands/logs.py tests/commands/test_logs.py
git commit -m "feat: add logs tail command for recent log viewing"
```

### Sub-task 4c: `ddg logs query` (6 tests, TDD)

Tests for analytics aggregation using `client.logs.aggregate_logs()`. Follow same pattern as APM analytics tests. Tests cover: count by service, count by status, percentiles, json format, table format, empty results.

**Commit after passing:**
```bash
git commit -m "feat: add logs query command for log analytics"
```

### Sub-task 4d: `ddg logs trace` (4 tests, TDD)

Tests for trace correlation — searches logs by `@trace_id:<id>`. Tests cover: basic trace lookup, json format, correlation verification, no logs found.

**Commit after passing:**
```bash
git commit -m "feat: add logs trace command for APM correlation"
```

### Task 4 final verification:
```bash
pytest tests/commands/test_logs.py -v --cov=ddg.commands.logs --cov-report=term-missing
pytest tests/ -v
```

Expected: ~23 new tests, all 199 total pass, >90% coverage on logs module.

---

## Task 5: Phase 2 — Database Monitoring Commands (TDD)

> **REQUIRED:** Use superpowers:test-driven-development skill for this task.

**Files:**
- Create: `ddg/commands/dbm.py`
- Create: `tests/commands/test_dbm.py`
- Modify: `ddg/cli.py` (register dbm group)
- Modify: `ddg/client.py` (add dbm API)
- Modify: `tests/conftest.py` (add DBM mock factories)

**Architecture:** Add `database_monitoring_api` to `DatadogClient`. DBM uses the V2 API.

### Step 1: Add DBM API to client

In `ddg/client.py`, add:
```python
from datadog_api_client.v2.api import database_monitoring_api

# In __init__:
self.dbm = database_monitoring_api.DatabaseMonitoringApi(self.api_client)
```

### Step 2: Add mock factories to conftest.py

```python
def create_mock_dbm_host(host, engine, version, connections, status):
    """Factory for mock DBM host objects."""
    class MockDBMHost:
        def __init__(self):
            self.host = host
            self.engine = engine
            self.version = version
            self.connections = connections
            self.status = status
        def to_dict(self):
            return {"host": host, "engine": engine, "version": version,
                    "connections": connections, "status": status}
    return MockDBMHost()


def create_mock_dbm_query(query_id, normalized_query, avg_latency_ms,
                          calls, total_time_ms, service, database):
    """Factory for mock DBM query objects."""
    class MockDBMQuery:
        def __init__(self):
            self.query_id = query_id
            self.normalized_query = normalized_query
            self.avg_latency = avg_latency_ms * 1_000_000  # ns
            self.calls = calls
            self.total_time = total_time_ms * 1_000_000  # ns
            self.service = service
            self.database = database
        def to_dict(self):
            return {"query_id": query_id, "normalized_query": normalized_query,
                    "avg_latency_ms": avg_latency_ms, "calls": calls}
    return MockDBMQuery()


def create_mock_dbm_sample(timestamp, duration_ms, rows_affected, params):
    """Factory for mock DBM query sample objects."""
    class MockDBMSample:
        def __init__(self):
            self.timestamp = timestamp
            self.duration = duration_ms * 1_000_000  # ns
            self.rows_affected = rows_affected
            self.parameters = params
        def to_dict(self):
            return {"timestamp": str(timestamp), "duration_ms": duration_ms,
                    "rows_affected": rows_affected}
    return MockDBMSample()
```

### Sub-task 5a: `ddg dbm hosts` (5 tests, TDD)

Tests: list all, filter by env, json format, table format, empty.

### Sub-task 5b: `ddg dbm queries` (8 tests, TDD)

Tests: top by latency, top by calls, filter by service, filter by database, json format, table format, limit, empty.

### Sub-task 5c: `ddg dbm explain` (5 tests, TDD)

Tests: get plan, json format, human-readable format, with metadata, not found.

### Sub-task 5d: `ddg dbm samples` (6 tests, TDD)

Tests: list samples, json format, table format, with limit, time range, empty.

**Each sub-task follows the same TDD cycle and commit pattern as Task 4.**

### Task 5 final verification:
```bash
pytest tests/commands/test_dbm.py -v --cov=ddg.commands.dbm --cov-report=term-missing
pytest tests/ -v
```

Expected: ~24 new tests, all 223 total pass, >90% coverage on dbm module.

**Bump version to 0.3.0 after commit.**

---

## Task 6: Phase 3 — Investigation Workflows (TDD)

> **REQUIRED:** Use superpowers:test-driven-development skill for this task.

**Files:**
- Create: `ddg/commands/investigate.py`
- Create: `tests/commands/test_investigate.py`
- Modify: `ddg/cli.py` (register investigate group)

**Architecture:** Investigation commands orchestrate multiple API calls (APM spans, logs, metrics) and produce combined analysis reports. They use the existing `DatadogClient` APIs — no new API imports needed.

### Sub-task 6a: `ddg investigate latency` (5 tests, TDD)

Queries APM traces above threshold, identifies slow endpoints, checks correlated logs.

### Sub-task 6b: `ddg investigate errors` (5 tests, TDD)

Aggregates error traces and error logs, groups by endpoint and error type.

### Sub-task 6c: `ddg investigate throughput` (5 tests, TDD)

Queries trace counts over time to show traffic patterns.

### Sub-task 6d: `ddg investigate compare` (5 tests, TDD)

Compares metrics/traces between two time periods (e.g., last hour vs previous hour).

### Task 6 final verification:
```bash
pytest tests/commands/test_investigate.py -v --cov=ddg.commands.investigate --cov-report=term-missing
pytest tests/ -v
```

Expected: ~20 new tests, all 243 total pass, >85% coverage on investigate module.

**Bump version to 0.4.0 after commit.**

---

## Task 7: Release Prep

**Files:**
- Modify: `pyproject.toml` (version → 1.0.0)
- Modify: `README.md` (final polish with all commands)
- Modify: `CLAUDE.md` (update with all new commands)
- Update: `IMPLEMENTATION_PLAN.md` (mark all phases complete)

**Step 1: Bump version**

In `pyproject.toml`: `version = "1.0.0"`
In `ddg/cli.py`: `@click.version_option(version="1.0.0")`

**Step 2: Update README with complete command reference**

Add all new commands (logs, dbm, investigate) with examples.

**Step 3: Update CLAUDE.md**

Add logs, dbm, investigate commands to the architecture section.

**Step 4: Final test run**

```bash
pytest tests/ -v --cov=ddg --cov-report=html
black --check ddg/ tests/
ruff check ddg/ tests/
```

Expected: 243+ tests pass, >90% overall coverage, clean lint.

**Step 5: Commit and tag**

```bash
git add -A
git commit -m "release: v1.0.0 - modern Datadog CLI with full feature set

Commands: monitor, metric, event, host, apm, logs, dbm, investigate
243+ tests, >90% coverage"

git tag v1.0.0
```

**Step 6: Build and verify**

```bash
pip install build
python -m build
pip install dist/ddg_cli-1.0.0-py3-none-any.whl
ddg --version
ddg --help
```
