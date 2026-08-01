# GitHub Actions Failure Log Parser CLI

`gha-log-parser` accepts a GitHub Actions run URL, downloads the first failed job log through the GitHub REST API, and outputs structured JSON for CI triage automation.

## Features

- Parses URLs like `https://github.com/owner/repo/actions/runs/123456789`.
- Outputs JSON fields: failing step, error message, compact stack trace, failure type, and suggested fix category.
- Handles pytest, Jest, TypeScript/build errors, lint failures, and generic command failures.
- Uses only the Python standard library.
- Includes mocked unit tests for success and error paths.

## Installation

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

A GitHub token is recommended for private repositories or higher API limits:

```bash
export GITHUB_TOKEN=ghp_...
```

## Usage

```bash
python -m actions_log_parser.cli https://github.com/owner/repo/actions/runs/123456789 --pretty
```

Example output:

```json
{
  "error_message": "E   AssertionError: assert 2 == 3",
  "failing_step": "pytest -q",
  "failure_type": "pytest",
  "job_name": "test",
  "owner": "owner",
  "repo": "repo",
  "run_id": "123456789",
  "source": "github-api",
  "stack_trace": ["File \"tests/test_math.py\", line 10, in test_total"],
  "suggested_fix_category": "test-assertion-or-regression"
}
```

## Verification

```bash
python -m unittest discover -s tests -v
python -m py_compile actions_log_parser/*.py tests/*.py
pylint actions_log_parser tests
```

The code uses type hints on public functions and is formatted for a pylint score above 8.
