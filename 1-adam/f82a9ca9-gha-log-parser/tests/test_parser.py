"""Unit tests for GitHub Actions log parser."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from actions_log_parser.cli import main
from actions_log_parser.parser import (
    fetch_json,
    parse_actions_run_url,
    parse_failure_log,
    summarize_run,
)


class ParserTests(unittest.TestCase):
    """Cover URL parsing, failure classification, and API success/error paths."""

    def test_parse_actions_run_url_success(self) -> None:
        self.assertEqual(
            parse_actions_run_url("https://github.com/acme/widget/actions/runs/12345"),
            ("acme", "widget", "12345"),
        )

    def test_parse_actions_run_url_rejects_invalid(self) -> None:
        with self.assertRaises(ValueError):
            parse_actions_run_url("https://example.com/acme/widget/actions/runs/nope")

    def test_pytest_failure_summary(self) -> None:
        log = """
##[group]Run pytest
Run pytest -q
=================================== FAILURES ===================================
____________________________ test_total ____________________________
  File "tests/test_math.py", line 10, in test_total
E   AssertionError: assert 2 == 3
FAILED tests/test_math.py::test_total - AssertionError: assert 2 == 3
Error: Process completed with exit code 1.
"""
        summary = parse_failure_log(log)
        self.assertEqual(summary.failure_type, "pytest")
        self.assertEqual(summary.failing_step, "pytest -q")
        self.assertEqual(summary.suggested_fix_category, "test-assertion-or-regression")
        self.assertIn("AssertionError", summary.error_message or "")
        self.assertTrue(summary.stack_trace)

    def test_jest_failure_summary(self) -> None:
        log = """
##[group]Run npm test
Run npm test
FAIL src/app.test.ts
● renders total
Expected: 3
Received: 2
    at Object.<anonymous> (/repo/src/app.test.ts:7:18)
Error: Process completed with exit code 1.
"""
        summary = parse_failure_log(log)
        self.assertEqual(summary.failure_type, "jest")
        self.assertEqual(summary.suggested_fix_category, "test-assertion-or-regression")
        self.assertIn("renders total", summary.error_message or "")

    def test_typescript_build_failure_summary(self) -> None:
        log = """
Run npm run build
src/index.ts(4,10): error TS2305: Module '"./types"' has no exported member 'User'.
Error: Process completed with exit code 2.
"""
        summary = parse_failure_log(log)
        self.assertEqual(summary.failure_type, "typescript_build")
        self.assertEqual(summary.suggested_fix_category, "compile-error")
        self.assertIn("TS2305", summary.error_message or "")

    def test_lint_failure_summary(self) -> None:
        log = """
Run npm run lint
src/index.ts:8:3: error Unexpected console statement no-console
✖ 1 problem (1 error, 0 warnings)
Error: Process completed with exit code 1.
"""
        summary = parse_failure_log(log)
        self.assertEqual(summary.failure_type, "lint")
        self.assertEqual(summary.suggested_fix_category, "lint-or-formatting")

    @patch("actions_log_parser.parser.fetch_text")
    @patch("actions_log_parser.parser.fetch_json")
    def test_summarize_run_uses_mocked_github_api(self, mock_fetch_json, mock_fetch_text) -> None:
        mock_fetch_json.return_value = {"jobs": [{"name": "test", "conclusion": "failure", "logs_url": "https://logs"}]}
        mock_fetch_text.return_value = "Run pytest\nE   AssertionError: boom\nError: Process completed with exit code 1."
        summary = summarize_run("https://github.com/acme/widget/actions/runs/99", token="x")
        self.assertEqual(summary.owner, "acme")
        self.assertEqual(summary.repo, "widget")
        self.assertEqual(summary.run_id, "99")
        self.assertEqual(summary.job_name, "test")
        self.assertEqual(summary.source, "github-api")

    @patch("actions_log_parser.parser.urlopen")
    def test_fetch_json_http_error_path(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = HTTPError("https://api", 404, "not found", {}, None)
        with self.assertRaises(RuntimeError):
            fetch_json("https://api", {})

    @patch("actions_log_parser.parser.urlopen")
    def test_fetch_json_url_error_path(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = URLError("offline")
        with self.assertRaises(RuntimeError):
            fetch_json("https://api", {})

    @patch("actions_log_parser.cli.summarize_run")
    def test_cli_outputs_json(self, mock_summarize) -> None:
        summary = parse_failure_log("Run tsc\nerror TS1005: ';' expected")
        mock_summarize.return_value = summary
        self.assertEqual(main(["https://github.com/acme/widget/actions/runs/1"]), 0)
        json.dumps(summary.to_dict())


if __name__ == "__main__":
    unittest.main()
