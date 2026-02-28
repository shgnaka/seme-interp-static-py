from __future__ import annotations

import argparse
import sys
from pathlib import Path

from seme.diagnostics import Diagnostic
from seme.pipeline import run_check


def _format_diagnostic(diag: Diagnostic) -> str:
    base = f"{diag.code} {diag.line}:{diag.column} {diag.message}"
    if diag.suggestion:
        return f"{base} (suggestion: {diag.suggestion})"
    return base


def _cmd_check(file_path: str) -> int:
    path = Path(file_path)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"RUNTIME-001 1:1 Failed to read file: {exc}", file=sys.stderr)
        return 1

    diagnostics = run_check(source)
    if diagnostics:
        for diag in diagnostics:
            print(_format_diagnostic(diag), file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seme")
    sub = parser.add_subparsers(dest="command", required=True)

    check_parser = sub.add_parser("check")
    check_parser.add_argument("file")

    run_parser = sub.add_parser("run")
    run_parser.add_argument("file")

    sub.add_parser("repl")

    args = parser.parse_args(argv)

    if args.command == "check":
        return _cmd_check(args.file)
    if args.command == "run":
        print("RUNTIME-001 1:1 'run' is not implemented in Phase 2", file=sys.stderr)
        return 1
    if args.command == "repl":
        print("RUNTIME-001 1:1 'repl' is not implemented in Phase 2", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
