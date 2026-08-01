"""Command-line interface for the GitHub Actions failure log parser."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .parser import summarize_run


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="gha-log-parser",
        description="Extract structured failure information from a GitHub Actions run URL.",
    )
    parser.add_argument("run_url", help="GitHub Actions run URL")
    parser.add_argument("--token", help="GitHub token; defaults to GITHUB_TOKEN", default=None)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line program."""
    args = build_arg_parser().parse_args(argv)
    try:
        summary = summarize_run(args.run_url, args.token)
    except (RuntimeError, ValueError) as exc:
        print(json.dumps({"error": str(exc), "run_url": args.run_url}), file=sys.stderr)
        return 2
    indent = 2 if args.pretty else None
    print(json.dumps(summary.to_dict(), indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
