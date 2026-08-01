"""Parse GitHub Actions run logs and summarize CI failures."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

USER_AGENT = "gha-log-parser/1.0"


@dataclass(slots=True)
class FailureSummary:
    """Structured summary of a failed GitHub Actions run."""

    run_url: str
    owner: str
    repo: str
    run_id: str
    job_name: str | None
    failing_step: str | None
    error_message: str | None
    stack_trace: list[str]
    suggested_fix_category: str
    failure_type: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the summary."""
        return asdict(self)


def parse_actions_run_url(run_url: str) -> tuple[str, str, str]:
    """Extract owner, repository, and run id from a GitHub Actions run URL."""
    parsed = urlparse(run_url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc.lower() != "github.com" or len(parts) < 5:
        raise ValueError("expected https://github.com/{owner}/{repo}/actions/runs/{run_id}")
    owner, repo, actions, runs, run_id = parts[:5]
    if actions != "actions" or runs != "runs" or not run_id.isdigit():
        raise ValueError("expected https://github.com/{owner}/{repo}/actions/runs/{run_id}")
    return owner, repo, run_id


def build_github_headers(token: str | None = None) -> dict[str, str]:
    """Build headers for GitHub REST calls."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    effective_token = token or os.environ.get("GITHUB_TOKEN")
    if effective_token:
        headers["Authorization"] = f"Bearer {effective_token}"
    return headers


def fetch_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    """Fetch JSON from an HTTP endpoint."""
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:  # nosec B310
            payload = response.read().decode("utf-8")
            return json.loads(payload)
    except HTTPError as exc:
        raw_detail = exc.read()
        detail = (raw_detail.decode("utf-8", errors="replace") if isinstance(raw_detail, bytes) else str(raw_detail))[:500]
        raise RuntimeError(f"GitHub API returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"failed to reach GitHub API: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("GitHub API returned non-JSON data") from exc


def fetch_text(url: str, headers: dict[str, str]) -> str:
    """Fetch text from an HTTP endpoint."""
    request = Request(url, headers={"User-Agent": USER_AGENT, **headers})
    try:
        with urlopen(request, timeout=30) as response:  # nosec B310
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raw_detail = exc.read()
        detail = (raw_detail.decode("utf-8", errors="replace") if isinstance(raw_detail, bytes) else str(raw_detail))[:500]
        raise RuntimeError(f"log download returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"failed to download logs: {exc.reason}") from exc


def get_failed_job_log(owner: str, repo: str, run_id: str, token: str | None = None) -> tuple[str | None, str]:
    """Return the first failed job name and its logs for a workflow run."""
    headers = build_github_headers(token)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs?per_page=100"
    jobs_payload = fetch_json(api_url, headers)
    jobs = jobs_payload.get("jobs", [])
    if not isinstance(jobs, list):
        raise RuntimeError("GitHub jobs response did not contain a jobs list")
    failed_jobs = [job for job in jobs if job.get("conclusion") in {"failure", "cancelled", "timed_out"}]
    if not failed_jobs:
        failed_jobs = [job for job in jobs if job.get("status") != "completed"]
    if not failed_jobs:
        raise RuntimeError("no failed jobs found for this run")
    job = failed_jobs[0]
    logs_url = job.get("logs_url")
    if not logs_url:
        raise RuntimeError("failed job did not include a logs_url")
    return job.get("name"), fetch_text(logs_url, headers)


def parse_failure_log(log_text: str, run_url: str = "", owner: str = "", repo: str = "", run_id: str = "") -> FailureSummary:
    """Parse raw GitHub Actions log text into a structured failure summary."""
    cleaned_lines = [_strip_gha_prefix(line.rstrip()) for line in log_text.splitlines()]
    failing_step = _find_failing_step(cleaned_lines)
    failure_type = _detect_failure_type(cleaned_lines)
    error_message = _extract_error_message(cleaned_lines, failure_type)
    stack_trace = _extract_stack_trace(cleaned_lines, failure_type)
    return FailureSummary(
        run_url=run_url,
        owner=owner,
        repo=repo,
        run_id=run_id,
        job_name=None,
        failing_step=failing_step,
        error_message=error_message,
        stack_trace=stack_trace,
        suggested_fix_category=_suggest_category(failure_type, error_message or ""),
        failure_type=failure_type,
        source="log-parser",
    )


def summarize_run(run_url: str, token: str | None = None) -> FailureSummary:
    """Fetch and summarize the first failed job for a GitHub Actions run."""
    owner, repo, run_id = parse_actions_run_url(run_url)
    job_name, log_text = get_failed_job_log(owner, repo, run_id, token)
    summary = parse_failure_log(log_text, run_url, owner, repo, run_id)
    summary.job_name = job_name
    summary.source = "github-api"
    return summary


def _strip_gha_prefix(line: str) -> str:
    line = re.sub(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s+", "", line)
    annotation = re.match(r"::(?P<level>error|warning)(?:\s+[^:]*)?::(?P<message>.*)$", line)
    if annotation:
        return f"{annotation.group('level').upper()}: {annotation.group('message')}"
    return line


def _find_failing_step(lines: list[str]) -> str | None:
    step_candidates: list[str] = []
    for line in lines:
        group = re.search(r"##\[group\](.+)", line)
        if group:
            step_candidates.append(group.group(1).strip())
        run_marker = re.search(r"^Run\s+(.+)$", line)
        if run_marker:
            step_candidates.append(run_marker.group(1).strip())
        if "Process completed with exit code" in line and step_candidates:
            return step_candidates[-1]
    return step_candidates[-1] if step_candidates else None


def _detect_failure_type(lines: list[str]) -> str:
    joined = "\n".join(lines).lower()
    if "eslint" in joined or "flake8" in joined or "pylint" in joined or "lint" in joined:
        return "lint"
    if "tsc" in joined or "typescript" in joined or re.search(r"error ts\d{4}", joined):
        return "typescript_build"
    if "jest" in joined or "expected:" in joined or "received:" in joined or "expect(received)" in joined or "test suite failed" in joined:
        return "jest"
    if "pytest" in joined or re.search(r"={2,}\s*failures\s*={2,}", joined) or "assertionerror" in joined:
        return "pytest"
    if "process completed with exit code" in joined:
        return "command_failure"
    return "unknown"


def _extract_error_message(lines: list[str], failure_type: str) -> str | None:
    for pattern in _error_patterns(failure_type):
        for line in lines:
            match = re.search(pattern, line)
            if match:
                return match.group(0).strip()
    for line in lines:
        lowered = line.lower()
        if "error" in lowered or "failed" in lowered or "assert" in lowered:
            return line.strip()
    return None


def _error_patterns(failure_type: str) -> list[str]:
    common = [r"Process completed with exit code \d+", r"ERROR:\s+.+", r"Error:\s+.+"]
    if failure_type == "typescript_build":
        return [r"[^\s].+\.tsx?\(\d+,\d+\): error TS\d+: .+", r"error TS\d+: .+"] + common
    if failure_type == "lint":
        return [r".+:\d+:\d+:\s+(?:error|warning)\s+.+", r"\d+ problems? \(\d+ errors?.+\)"] + common
    if failure_type == "jest":
        return [r"● .+", r"Expected:.+", r"Received:.+", r"Test suite failed to run"] + common
    if failure_type == "pytest":
        return [r"E\s+AssertionError:.+", r"FAILED .+", r"assert .+"] + common
    return common


def _extract_stack_trace(lines: list[str], failure_type: str) -> list[str]:
    trace: list[str] = []
    trace_patterns = [
        r"^\s*File \".+\", line \d+",
        r"^\s*at .+\(.+:\d+:\d+\)",
        r"^\s*at .+:\d+:\d+",
        r"^\s*>\s*\d+\s*\|",
        r"^\s*\d+\s*\|",
    ]
    for line in lines:
        if any(re.search(pattern, line) for pattern in trace_patterns):
            trace.append(line.strip())
        elif failure_type in {"typescript_build", "lint"} and re.search(r".+:\d+:\d+", line):
            trace.append(line.strip())
    return trace[:30]


def _suggest_category(failure_type: str, message: str) -> str:
    lowered = message.lower()
    if failure_type in {"pytest", "jest"}:
        if "timeout" in lowered:
            return "test-timeout"
        if "assert" in lowered or "expected" in lowered or "received" in lowered or "●" in message:
            return "test-assertion-or-regression"
        return "test-failure"
    if failure_type == "typescript_build":
        if "cannot find module" in lowered or "cannot find name" in lowered:
            return "missing-import-or-type"
        return "compile-error"
    if failure_type == "lint":
        return "lint-or-formatting"
    if "permission denied" in lowered:
        return "environment-permissions"
    if "exit code" in lowered:
        return "script-command-failure"
    return "needs-human-triage"
