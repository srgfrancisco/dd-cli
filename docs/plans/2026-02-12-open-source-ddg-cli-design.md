# Design: Open-Source ddogctl

**Date**: 2026-02-12
**Status**: Approved

## Summary

Transform dd-cli from a Kojo-internal Datadog troubleshooting tool into an open-source CLI positioned as a modern Dogshell replacement. Rename to `ddogctl`, implement the full roadmap (logs, DBM, investigation workflows), and publish to PyPI.

## Decisions

| Decision | Choice |
|----------|--------|
| CLI command name | `ddg` |
| PyPI package name | `ddogctl` |
| Launch scope | Full roadmap before open-sourcing |
| Positioning | Modern Dogshell replacement |
| License | MIT |

## Renaming & Package Structure

Rename `dd/` directory to `ddg/`. All internal imports change from `from dd.X` to `from ddg.X`.

**pyproject.toml**:
```toml
[project]
name = "ddogctl"
description = "A modern CLI for the Datadog API. Like Dogshell, but better."

[project.scripts]
ddg = "ddg.cli:main"

[tool.setuptools]
packages = ["ddg", "ddg.commands", "ddg.formatters", "ddg.models", "ddg.utils"]
```

Test patches update accordingly (e.g., `ddg.commands.monitor.get_datadog_client`).

Remove `scripts/dd_cli.sh` — unnecessary once installed via pip.

Remove all Kojo references. Use generic service names in examples (`my-api`, `web-service`).

## Open-Source Scaffolding

**New files**:
- `LICENSE` — MIT
- `CONTRIBUTING.md` — Dev setup, TDD workflow, PR process
- `.github/workflows/ci.yml` — Tests on Python 3.10-3.13, lint, coverage, PyPI publish on tags

**README.md rewrite**:
- One-liner: "A modern CLI for the Datadog API. Like Dogshell, but better."
- Feature comparison table (ddg vs Dogshell)
- Install: `pip install ddogctl` / `pipx install ddogctl`
- Configuration: `DD_API_KEY`, `DD_APP_KEY`, `DD_SITE`
- Command overview with examples

**pyproject.toml additions**: license, readme, keywords, classifiers, project URLs.

**Remove**: `MIGRATION_GUIDE.md` (Kojo-specific).

## Implementation Phases

### Phase 1: Logs (~23 tests, ~300 lines)

- `ddg logs search <query>` — Search with filters (service, status, time range)
- `ddg logs tail <query>` — Stream logs with `--follow`, color-coded by level
- `ddg logs query` — Analytics/aggregations (count, group-by, percentiles)
- `ddg logs trace <trace_id>` — Correlate logs with APM traces

Highest-value addition. Trace correlation is the killer feature Dogshell never had.

### Phase 2: Database Monitoring (~24 tests, ~350 lines)

- `ddg dbm hosts` — List monitored database hosts
- `ddg dbm queries` — Top queries by latency/calls/total time
- `ddg dbm explain <query_id>` — Query execution plans
- `ddg dbm samples <query_id>` — Sample executions with timing

Zero Dogshell coverage of DBM — clear differentiator.

### Phase 3: Investigation Workflows (~20 tests, ~400 lines)

- `ddg investigate latency <service>` — Auto-analyze slow endpoints, correlate traces + DB + logs
- `ddg investigate errors <service>` — Aggregate error patterns across traces and logs
- `ddg investigate throughput <service>` — Traffic analysis with anomaly detection
- `ddg investigate compare <service>` — Compare two time periods side-by-side

Multi-API orchestration — 10 minutes of DD UI clicking in one command.

## Distribution

- Primary: `pip install ddogctl` / `pipx install ddogctl` / `uv pip install ddogctl`
- Build system: setuptools (already in place)
- CI publishes to PyPI on tagged releases via `pypa/gh-action-pypi-publish`

## Versioning

- Current: `0.1.0`
- After logs: `0.2.0`
- After DBM: `0.3.0`
- After investigate: `0.4.0`
- Public release: `1.0.0`

## Execution Order

1. **Rename `dd` → `ddg`** — directory, imports, pyproject.toml, tests. 176 tests must stay green.
2. **Genericize** — remove Kojo refs, generic service name examples, delete MIGRATION_GUIDE.md.
3. **Open-source scaffolding** — LICENSE, CONTRIBUTING.md, README.md rewrite, CI workflow, pyproject.toml metadata.
4. **Phase 1: Logs** — strict TDD, ~23 tests.
5. **Phase 2: DBM** — strict TDD, ~24 tests.
6. **Phase 3: Investigation Workflows** — strict TDD, ~20 tests.
7. **Release prep** — version 1.0.0, final README, tag, publish to PyPI.

## Test Count Progression

| Step | New Tests | Total | Status |
|------|-----------|-------|--------|
| Current | — | 176 | Complete |
| Phase 1 (Logs) | 23 | 199 | Pending |
| Phase 2 (DBM) | 24 | 223 | Pending |
| Phase 3 (Investigate) | 20 | 243 | Pending |
