"""CLI: create a WordPress *draft* from one READY_FOR_REVIEW candidate.

Default is dry-run. Live POST requires --apply. There is no publish flag.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import HandoffError
from .handoff import format_dry_run, run_handoff


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a WordPress draft (status=draft only) from a "
            "READY_FOR_REVIEW candidate. Default: dry-run, no network write."
        )
    )
    parser.add_argument(
        "candidate_id",
        help="Candidate ID, e.g. bc-20260901-10",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="POST a WordPress draft. Requires HTTPS credentials. Never publishes.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root (default: two levels above this package).",
    )
    return parser


def _reject_forbidden_status_flags(argv: list[str]) -> None:
    forbidden = (
        "--status",
        "--publish",
        "--future",
        "--private",
        "--public",
        "--schedule",
    )
    for arg in argv:
        name = arg.split("=", 1)[0]
        if name in forbidden:
            raise HandoffError(
                "This tool cannot publish, schedule, or set WordPress status. "
                "Drafts only."
            )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        _reject_forbidden_status_flags(argv)
        parser = build_parser()
        args = parser.parse_args(argv)
        repo_root = (
            Path(args.repo_root).resolve()
            if args.repo_root
            else Path(__file__).resolve().parents[2]
        )
        result = run_handoff(
            repo_root,
            args.candidate_id,
            apply=bool(args.apply),
        )
        if result.dry_run:
            sys.stdout.write(format_dry_run(result))
        else:
            sys.stdout.write(result.message + "\n")
        return 0
    except HandoffError as exc:
        sys.stderr.write(str(exc) + "\n")
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
