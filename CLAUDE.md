# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ddogctl is a modern CLI for the Datadog API. Like Dogshell, but better. Rich terminal output, APM/logs/DBM support, retry logic, investigation workflows. Requires Python 3.10+.

## Commands

```bash
# Setup
uv sync --all-extras

# Run tests
uv run pytest tests/ -v
uv run pytest tests/commands/test_apm.py -v          # single module
uv run pytest tests/commands/test_apm.py::test_name   # single test
uv run pytest tests/ --cov=ddogctl --cov-report=html  # coverage

# Code quality
uv run black ddogctl/ tests/                          # format (line-length: 100)
uv run ruff check ddogctl/ tests/                     # lint (line-length: 100)
uv run mypy ddogctl/                                  # type check

# Run CLI
export DD_API_KEY=... DD_APP_KEY=...
uv run ddogctl monitor list --state Alert
uv run ddogctl apm services
uv run ddogctl logs search "status:error" --service my-api
uv run ddogctl dbm queries --sort-by avg_latency
uv run ddogctl investigate latency my-service --threshold 500
```

## Architecture

**Entry point**: `ddogctl.cli:main` — a Click group that registers command subgroups.

**Command structure** (`ddogctl/commands/`): Each file defines a Click group with subcommands. Commands call `get_datadog_client()` to get an API client, then use Rich for output formatting.

```
ddogctl monitor {list, get, mute, unmute, validate}
ddogctl metric  {query, search, metadata}
ddogctl event   {list, get, post}
ddogctl host    {list, get, totals}
ddogctl apm     {services, traces, analytics}
ddogctl logs    {search, tail, query, trace}
ddogctl dbm     {hosts, queries, explain, samples}
ddogctl investigate {latency, errors, throughput, compare}
```

**Key modules**:
- `ddogctl/client.py` — `DatadogClient` wraps `datadog_api_client` SDK, exposing V1 APIs (monitors, metrics, events, hosts, tags) and V2 APIs (logs, spans). Use `get_datadog_client()` to instantiate.
- `ddogctl/config.py` — `DatadogConfig` (Pydantic BaseSettings) loads from env vars (`DD_API_KEY`, `DD_APP_KEY`, `DD_SITE`). Supports region shortcuts (us, eu, us3, us5, ap1, gov).
- `ddogctl/utils/error.py` — `@handle_api_error` decorator with retry logic (exponential backoff on 429/5xx, immediate exit on 401/403).
- `ddogctl/utils/time.py` — `parse_time_range()` handles relative (1h, 24h, 7d) and ISO datetime formats, returns Unix timestamps.
- `ddogctl/utils/tags.py` — Tag parsing and display formatting.
- `ddogctl/utils/spans.py` — `aggregate_spans()` wrapper for spans API aggregation (used by APM analytics and investigate commands).

## Testing Patterns

Tests use `unittest.mock` with Click's `CliRunner`. Key fixtures from `tests/conftest.py`:
- `mock_client` — Mock with `.monitors`, `.hosts`, `.metrics`, `.events`, `.spans`, `.logs`, `.dbm` attributes
- `runner` — `CliRunner()` instance
- Factory functions: `create_mock_monitor()`, `create_mock_host()`, `create_mock_span()`, `create_mock_log()`, `create_mock_dbm_host()`, `create_mock_dbm_query()`, `create_mock_dbm_sample()`

Standard test pattern: patch `get_datadog_client` to return `mock_client`, invoke command via `runner`, assert on output and exit code.

## Development Workflow

- **Worktrees**: Always create a Git worktree for every new feature, fix, or change. Use the `./.worktrees` folder. Use `git gtr` instead of plain `git worktree` commands.
- **Pull requests**: Every change lands via PR — no direct commits to `main`. Open a PR from the worktree branch, get it reviewed, then merge.
- **Commits**: Follow conventional commit format.

## Development Methodology

Strict TDD (RED-GREEN-REFACTOR). Coverage target >90%. Reference implementation: `ddogctl/commands/apm.py`.

## Roadmap

See `docs/plans/2026-02-12-ddogctl-roadmap-design.md` for the approved 4-phase plan:
- **Phase 1**: API parity with Dogshell (monitor CRUD, dashboards, SLOs, downtimes, tags, service checks)
- **Phase 2**: CLI UX (profiles, apply/diff, shell completion, watch mode)
- **Phase 3**: Agentic (structured errors, semantic exit codes, stdin piping)
- **Phase 4**: Beyond Dogshell (synthetics, incidents, notebooks, users, usage, RUM, CI)
