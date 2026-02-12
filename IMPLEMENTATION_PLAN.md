# DD CLI - Implementation Plan for Missing Features

**Status**: Complete
**Last Updated**: 2026-02-12
**Current State**: All phases complete (243 tests passing)

---

## Overview

This plan outlines the implementation of missing Datadog CLI features using strict TDD methodology. All implementations follow the RED-GREEN-REFACTOR cycle established in the APM implementation.

**Current Commands**: monitor, metric, event, host, apm, logs, dbm, investigate
**All features implemented.**

---

## Phase 1: Logs Command (High Priority)

### Objective
Implement comprehensive log querying capabilities to correlate with APM traces and debug application behavior.

### Commands to Implement

1. **`dd logs search <query>`** - Search logs with filters
2. **`dd logs tail <query>`** - Stream logs in real-time
3. **`dd logs query`** - Advanced analytics on logs
4. **`dd logs trace <trace_id>`** - Get logs for a specific trace

### Implementation Details

#### Prerequisites
- Client already has `logs_api` imported from `datadog_api_client.v2.api`
- Add to conftest.py: `client.logs = Mock()`

#### Command 1: `dd logs search`

**Test Structure** (8 tests):
```python
def test_logs_search_basic_query(mock_client, runner)  # Basic search
def test_logs_search_json_format(mock_client, runner)  # JSON output
def test_logs_search_table_format(mock_client, runner)  # Table output
def test_logs_search_with_time_range(mock_client, runner)  # Time filtering
def test_logs_search_with_service_filter(mock_client, runner)  # Service filter
def test_logs_search_with_status_filter(mock_client, runner)  # Status filter
def test_logs_search_empty_results(mock_client, runner)  # No logs found
def test_logs_search_pagination(mock_client, runner)  # Limit parameter
```

**Implementation Outline**:
```python
@logs.command(name="search")
@click.argument("query")
@click.option("--from", "from_time", default="1h")
@click.option("--to", "to_time", default="now")
@click.option("--service", help="Filter by service")
@click.option("--status", help="Filter by status (info, warn, error)")
@click.option("--limit", default=50, type=int)
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def search_logs(query, from_time, to_time, service, status, limit, format):
    """Search logs with filters."""
    # Implementation using client.logs.list_logs()
```

**Mock Factory** (conftest.py):
```python
def create_mock_log(message, service, status, timestamp, attributes=None):
    """Factory for mock log objects."""
    class MockLog:
        def __init__(self):
            self.attributes = Mock(
                message=message,
                service=service,
                status=status,
                timestamp=timestamp,
                attributes=attributes or {}
            )
    return MockLog()
```

#### Command 2: `dd logs tail`

**Test Structure** (5 tests):
```python
def test_logs_tail_basic(mock_client, runner)  # Basic tailing
def test_logs_tail_with_filter(mock_client, runner)  # Filtered tail
def test_logs_tail_stop_after_count(mock_client, runner)  # Limit logs
def test_logs_tail_format_output(mock_client, runner)  # Output format
def test_logs_tail_empty_stream(mock_client, runner)  # No logs
```

**Implementation Notes**:
- Use `client.logs.list_logs()` with pagination cursor
- Implement streaming with `--follow` flag
- Add `--lines` parameter for number of initial logs
- Color-code by log level (error=red, warn=yellow, info=cyan)

#### Command 3: `dd logs query`

**Test Structure** (6 tests):
```python
def test_logs_query_count_by_service(mock_client, runner)  # Count aggregation
def test_logs_query_count_by_status(mock_client, runner)  # Group by status
def test_logs_query_percentiles(mock_client, runner)  # Percentile metrics
def test_logs_query_json_format(mock_client, runner)  # JSON output
def test_logs_query_table_format(mock_client, runner)  # Table output
def test_logs_query_empty_results(mock_client, runner)  # No data
```

**Implementation Outline**:
```python
@logs.command(name="query")
@click.option("--query", default="*")
@click.option("--from", "from_time", default="1h")
@click.option("--to", "to_time", default="now")
@click.option("--group-by", help="Group by field (e.g., service, status)")
@click.option("--metric", default="count", help="Metric (count, avg, sum, min, max)")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def query_logs(query, from_time, to_time, group_by, metric, format):
    """Advanced log analytics."""
    # Implementation using client.logs.aggregate_logs()
```

#### Command 4: `dd logs trace`

**Test Structure** (4 tests):
```python
def test_logs_trace_by_id(mock_client, runner)  # Get logs for trace
def test_logs_trace_json_format(mock_client, runner)  # JSON output
def test_logs_trace_correlation(mock_client, runner)  # Verify trace correlation
def test_logs_trace_not_found(mock_client, runner)  # Trace has no logs
```

**Implementation Outline**:
```python
@logs.command(name="trace")
@click.argument("trace_id")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def logs_for_trace(trace_id, format):
    """Get logs correlated with a trace ID."""
    # Query logs with filter: @trace_id:<trace_id>
```

### Estimated Effort
- **Tests**: ~23 tests
- **Implementation**: ~300 lines
- **Coverage Target**: >90%
- **Time**: 2-3 hours with strict TDD

---

## Phase 2: Database Monitoring Command (High Priority)

### Objective
Implement PostgreSQL performance monitoring to analyze query performance, detect slow queries, and monitor database health.

### Commands to Implement

1. **`dd dbm hosts`** - List database hosts
2. **`dd dbm queries`** - Top queries by performance
3. **`dd dbm explain <query_id>`** - Get query execution plan
4. **`dd dbm samples <query_id>`** - Sample query executions

### Implementation Details

#### Prerequisites
- Add DBM API to client:
  ```python
  from datadog_api_client.v2.api import database_monitoring_api
  self.dbm = database_monitoring_api.DatabaseMonitoringApi(self.api_client)
  ```
- Add to conftest.py: `client.dbm = Mock()`

#### Command 1: `dd dbm hosts`

**Test Structure** (5 tests):
```python
def test_dbm_hosts_list_all(mock_client, runner)  # List all hosts
def test_dbm_hosts_filter_by_env(mock_client, runner)  # Environment filter
def test_dbm_hosts_json_format(mock_client, runner)  # JSON output
def test_dbm_hosts_table_format(mock_client, runner)  # Table output
def test_dbm_hosts_empty(mock_client, runner)  # No hosts
```

**Mock Factory**:
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
    return MockDBMHost()
```

#### Command 2: `dd dbm queries`

**Test Structure** (8 tests):
```python
def test_dbm_queries_top_by_latency(mock_client, runner)  # Top slow queries
def test_dbm_queries_top_by_calls(mock_client, runner)  # Most called
def test_dbm_queries_filter_by_service(mock_client, runner)  # Service filter
def test_dbm_queries_filter_by_database(mock_client, runner)  # Database filter
def test_dbm_queries_json_format(mock_client, runner)  # JSON output
def test_dbm_queries_table_format(mock_client, runner)  # Table with stats
def test_dbm_queries_limit(mock_client, runner)  # Respect limit
def test_dbm_queries_empty(mock_client, runner)  # No queries
```

**Implementation Outline**:
```python
@dbm.command(name="queries")
@click.option("--from", "from_time", default="1h")
@click.option("--to", "to_time", default="now")
@click.option("--service", help="Filter by service")
@click.option("--database", help="Filter by database name")
@click.option("--sort-by", default="avg_latency",
              help="Sort by: avg_latency, calls, total_time")
@click.option("--limit", default=20, type=int)
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def top_queries(from_time, to_time, service, database, sort_by, limit, format):
    """Show top queries by performance metrics."""
    # Display: query_id, normalized_query, avg_latency, calls, total_time
```

**Mock Factory**:
```python
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
    return MockDBMQuery()
```

#### Command 3: `dd dbm explain`

**Test Structure** (5 tests):
```python
def test_dbm_explain_query_plan(mock_client, runner)  # Get explain plan
def test_dbm_explain_json_format(mock_client, runner)  # JSON output
def test_dbm_explain_formatted(mock_client, runner)  # Human-readable
def test_dbm_explain_with_metadata(mock_client, runner)  # Include metadata
def test_dbm_explain_not_found(mock_client, runner)  # Query not found
```

**Implementation Outline**:
```python
@dbm.command(name="explain")
@click.argument("query_id")
@click.option("--format", type=click.Choice(["json", "text"]), default="text")
@click.option("--include-metadata/--no-metadata", default=True)
@handle_api_error
def explain_query(query_id, format, include_metadata):
    """Get query execution plan."""
    # Show: plan, estimated cost, actual cost, indexes used
```

#### Command 4: `dd dbm samples`

**Test Structure** (6 tests):
```python
def test_dbm_samples_list(mock_client, runner)  # List samples
def test_dbm_samples_json_format(mock_client, runner)  # JSON output
def test_dbm_samples_table_format(mock_client, runner)  # Table output
def test_dbm_samples_with_limit(mock_client, runner)  # Limit samples
def test_dbm_samples_time_range(mock_client, runner)  # Time filtering
def test_dbm_samples_empty(mock_client, runner)  # No samples
```

**Implementation Outline**:
```python
@dbm.command(name="samples")
@click.argument("query_id")
@click.option("--from", "from_time", default="1h")
@click.option("--to", "to_time", default="now")
@click.option("--limit", default=10, type=int)
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@handle_api_error
def query_samples(query_id, from_time, to_time, limit, format):
    """Get sample executions of a query."""
    # Show: timestamp, duration, rows_affected, parameters
```

**Mock Factory**:
```python
def create_mock_dbm_sample(timestamp, duration_ms, rows_affected, params):
    """Factory for mock DBM query sample objects."""
    class MockDBMSample:
        def __init__(self):
            self.timestamp = timestamp
            self.duration = duration_ms * 1_000_000  # ns
            self.rows_affected = rows_affected
            self.parameters = params
    return MockDBMSample()
```

### Estimated Effort
- **Tests**: ~24 tests
- **Implementation**: ~350 lines
- **Coverage Target**: >90%
- **Time**: 3-4 hours with strict TDD

---

## Phase 3: Investigation Workflows (Medium Priority)

### Objective
Automate common investigation patterns by correlating metrics, traces, logs, and errors.

### Commands to Implement

1. **`dd investigate latency <service>`** - Auto-analyze high latency
2. **`dd investigate errors <service>`** - Aggregate error patterns
3. **`dd investigate throughput <service>`** - Traffic analysis
4. **`dd investigate compare <service>`** - Compare time periods

### Implementation Approach

These commands are higher-level and orchestrate multiple API calls:

```python
@investigate.command(name="latency")
@click.argument("service")
@click.option("--from", "from_time", default="1h")
@click.option("--threshold", default=500, type=int, help="Latency threshold (ms)")
@click.option("--report", is_flag=True, help="Generate HTML report")
@handle_api_error
def investigate_latency(service, from_time, threshold, report):
    """Investigate high latency issues.

    This command:
    1. Queries APM traces above threshold
    2. Analyzes slow endpoints
    3. Checks database query performance
    4. Correlates with error logs
    5. Checks infrastructure metrics
    """
    # Multi-step investigation workflow
    # Generate findings report (markdown + optional HTML)
```

**Test Structure** (4 commands × 5 tests = 20 tests):
- Basic investigation
- With thresholds
- Report generation
- Multiple services (web-prod-blue + web-prod-green)
- Empty results / no issues found

### Estimated Effort
- **Tests**: ~20 tests
- **Implementation**: ~400 lines (orchestration logic)
- **Coverage Target**: >85%
- **Time**: 4-5 hours

---

## Implementation Strategy

### TDD Workflow (Strict RED-GREEN-REFACTOR)

For **each command**:

1. **RED**: Write failing test
   - Run test: `pytest tests/commands/test_<module>.py::<test_name> -v`
   - Confirm: Exit code != 0

2. **GREEN**: Write minimal implementation
   - Make test pass
   - Run test: Confirm exit code == 0

3. **REFACTOR**: Improve code quality
   - Keep tests green
   - Run all tests: `pytest tests/ -v`

4. **VERIFY**: Check coverage
   - Run: `pytest tests/commands/test_<module>.py --cov=dd.commands.<module> --cov-report=term-missing`
   - Target: >90% coverage

### File Structure

**New Files to Create**:
```
dd/commands/logs.py          # ~300 lines
dd/commands/dbm.py           # ~350 lines
dd/commands/investigate.py   # ~400 lines
tests/commands/test_logs.py  # ~600 lines (23 tests)
tests/commands/test_dbm.py   # ~650 lines (24 tests)
tests/commands/test_investigate.py  # ~500 lines (20 tests)
```

**Files to Modify**:
```
dd/client.py                 # Add logs, dbm APIs
dd/cli.py                    # Register new command groups
tests/conftest.py            # Add mock factories
```

### Test Count Progression

| Phase | New Tests | Total Tests | Status |
|-------|-----------|-------------|--------|
| Current (APM) | 15 | 176 | ✅ Complete |
| Phase 1 (Logs) | 23 | 199 | ✅ Complete |
| Phase 2 (DBM) | 24 | 223 | ✅ Complete |
| Phase 3 (Investigate) | 20 | 243 | ✅ Complete |

### Success Criteria (Each Phase)

- ✅ All commands implemented
- ✅ All tests passing (100% pass rate)
- ✅ >90% code coverage on new modules
- ✅ No regressions (all existing tests pass)
- ✅ TDD process documented (can show RED→GREEN→REFACTOR)
- ✅ CLI registration complete (`dd <command> --help` works)
- ✅ Manual verification with real Datadog API

---

## Execution Commands

### Run Tests
```bash
# Activate environment
source .venv/bin/activate

# Run specific module tests
pytest tests/commands/test_logs.py -v
pytest tests/commands/test_dbm.py -v
pytest tests/commands/test_investigate.py -v

# Run all tests
pytest tests/ -v

# Check coverage
pytest tests/commands/test_logs.py --cov=dd.commands.logs --cov-report=term-missing
pytest tests/ --cov=dd --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Manual Verification
```bash
# Activate environment
source .envrc

# Test logs commands
./dd_cli.sh logs search "service:web-prod-blue error" --from 1h
./dd_cli.sh logs tail "service:web-prod-blue" --lines 20
./dd_cli.sh logs query --group-by service --from 24h
./dd_cli.sh logs trace <trace_id>

# Test DBM commands
./dd_cli.sh dbm hosts
./dd_cli.sh dbm queries --service web-prod-blue --sort-by avg_latency
./dd_cli.sh dbm explain <query_id>
./dd_cli.sh dbm samples <query_id> --limit 10

# Test investigation workflows
./dd_cli.sh investigate latency web-prod-blue --report
./dd_cli.sh investigate errors marketplace-prod
```

---

## Critical Notes

### Web Service Blue/Green Fleets
**IMPORTANT**: When investigating `web` service issues, ALWAYS check BOTH:
- `web-prod-blue`
- `web-prod-green`

Traffic shifts between fleets during deployments. Analyzing only one fleet leads to misleading conclusions.

### API Rate Limits
- **Spans API**: 300 requests/hour
- **Logs API**: 300 requests/hour
- **Metrics API**: 100,000 requests/hour

Implement rate limit handling in `handle_api_error` decorator if needed.

### Datadog API Documentation
- Logs API v2: https://docs.datadoghq.com/api/latest/logs/
- DBM API v2: https://docs.datadoghq.com/api/latest/database-monitoring/
- APM API v2: https://docs.datadoghq.com/api/latest/apm/

---

## Migration to Standalone Repository

When moving to a standalone Git repository:

### Repository Structure
```
dd-cli/
├── .git/
├── .gitignore
├── README.md
├── IMPLEMENTATION_PLAN.md (this file)
├── pyproject.toml
├── requirements.txt
├── .envrc (git-ignored, template in .envrc.example)
├── dd/
│   ├── __init__.py
│   ├── cli.py
│   ├── client.py
│   ├── config.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── apm.py
│   │   ├── monitor.py
│   │   ├── metric.py
│   │   ├── event.py
│   │   ├── host.py
│   │   ├── logs.py (to implement)
│   │   ├── dbm.py (to implement)
│   │   └── investigate.py (to implement)
│   └── utils/
│       ├── __init__.py
│       ├── error.py
│       ├── time.py
│       └── tags.py
├── tests/
│   ├── conftest.py
│   ├── commands/
│   │   ├── test_apm.py (15 tests)
│   │   ├── test_monitor.py
│   │   ├── test_metric.py
│   │   ├── test_event.py
│   │   ├── test_host.py
│   │   ├── test_logs.py (to implement)
│   │   ├── test_dbm.py (to implement)
│   │   └── test_investigate.py (to implement)
│   └── utils/
│       ├── test_error.py
│       ├── test_time.py
│       └── test_tags.py
├── reports/ (git-ignored)
│   └── _template.html
└── scripts/
    └── dd_cli.sh
```

### Git Initialization
```bash
# Navigate to new standalone location
cd /path/to/new/location
mkdir dd-cli && cd dd-cli

# Initialize git
git init
git add .
git commit -m "chore: initial commit - dd cli with APM commands

- 176 tests, 94% coverage
- Commands: monitor, metric, event, host, apm
- Strict TDD implementation
- Ready for logs and dbm implementation"

# Create branches for new features
git checkout -b feature/logs-commands
git checkout -b feature/dbm-commands
git checkout -b feature/investigation-workflows
```

### .gitignore
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/
env/

# Testing
.pytest_cache/
.coverage
htmlcov/
*.cover
.hypothesis/

# Environment
.envrc
.env
*.local

# Reports
reports/*.html
reports/*.md
!reports/_template.html

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
```

---

## Changelog

### 2026-02-12
- ✅ Renamed dd → ddg, genericized for open source
- ✅ Added open-source scaffolding (LICENSE, CONTRIBUTING, CI, README)
- ✅ Phase 1: Logs commands (search, tail, query, trace) — 23 tests
- ✅ Phase 2: DBM commands (hosts, queries, explain, samples) — 24 tests
- ✅ Phase 3: Investigation workflows (latency, errors, throughput, compare) — 20 tests
- ✅ Total: 243 tests passing
- ✅ Version bumped to 1.0.0

### 2026-02-11
- ✅ Implemented APM commands (services, traces, analytics)
- ✅ 15 tests, 94% coverage
- ✅ Total: 176 tests passing
- 📝 Documented implementation plan for logs, dbm, investigate

---

## Next Steps

All phases are complete. Future work:
1. **Publish to PyPI** as `ddogctl`
2. **Manual verification** with real Datadog API
3. **Add more commands** as needed (dashboards, synthetics, etc.)

---

**Questions or Clarifications?**
- Refer to existing APM implementation as reference (`dd/commands/apm.py`)
- Follow established patterns in test fixtures (`tests/conftest.py`)
- Maintain strict TDD: RED → GREEN → REFACTOR → VERIFY
