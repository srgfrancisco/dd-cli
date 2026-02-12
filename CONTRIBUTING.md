# Contributing to ddogctl

## Setup

```bash
git clone https://github.com/srgfrancisco/ddogctl.git
cd ddogctl
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## TDD Workflow

We follow strict RED-GREEN-REFACTOR:

1. **RED** -- Write a failing test first.
2. **GREEN** -- Write the minimum code to make the test pass.
3. **REFACTOR** -- Clean up while keeping tests green.

Run tests after every change:

```bash
pytest tests/ -v
```

## Code Quality

```bash
black --line-length 100 ddogctl/ tests/
ruff check ddogctl/ tests/
mypy ddogctl/ --ignore-missing-imports
```

All tools are configured with `line-length = 100` in `pyproject.toml`.

## PR Guidelines

- **One feature per PR.** Keep changes focused and reviewable.
- **All tests must pass.** Run `pytest tests/ -v` before submitting.
- **Follow existing patterns.** See `ddogctl/commands/apm.py` as the reference implementation.
- **Include tests.** Every new command or feature needs corresponding tests.
- **Run the full quality suite** before pushing:

```bash
black --check ddogctl/ tests/
ruff check ddogctl/ tests/
pytest tests/ -v --cov=ddogctl
```
