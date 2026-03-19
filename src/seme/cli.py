from __future__ import annotations

import argparse
import sys
from io import TextIOBase
from pathlib import Path

from seme.ast import Program, Stmt
from seme.compiler import compile_program
from seme.diagnostics import Diagnostic
from seme.lexer import lex
from seme.parser import parse
from seme.pipeline import ExecutionBackend, run_check, run_execute
from seme.typechecker import check_types
from seme.vm import execute_chunk


def _format_diagnostic(diag: Diagnostic) -> str:
    base = f"{diag.code} {diag.line}:{diag.column} {diag.message}"
    if diag.suggestion:
        return f"{base} (suggestion: {diag.suggestion})"
    return base


def _print_diagnostics(diagnostics: list[Diagnostic], stream: TextIOBase) -> None:
    for diag in diagnostics:
        print(_format_diagnostic(diag), file=stream)


def _cmd_check(file_path: str) -> int:
    path = Path(file_path)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"RUNTIME-001 1:1 Failed to read file: {exc}", file=sys.stderr)
        return 1

    diagnostics = run_check(source)
    if diagnostics:
        _print_diagnostics(diagnostics, sys.stderr)
        return 1
    return 0


def _cmd_run(file_path: str, backend: ExecutionBackend) -> int:
    path = Path(file_path)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"RUNTIME-001 1:1 Failed to read file: {exc}", file=sys.stderr)
        return 1

    stdout_text, diagnostics = run_execute(source, backend=backend)
    if stdout_text:
        sys.stdout.write(stdout_text)
    if diagnostics:
        _print_diagnostics(diagnostics, sys.stderr)
        return 1
    return 0


def _program_for_history(statements: list[Stmt]) -> Program:
    if not statements:
        return Program(statements=[])
    first = statements[0]
    return Program(statements=list(statements), line=first.line, column=first.column)


def _execute_repl_program(program: Program) -> tuple[list[str], list[Diagnostic]]:
    chunk = compile_program(program)
    return execute_chunk(chunk)


def repl_loop(inp: TextIOBase, out: TextIOBase, err: TextIOBase) -> int:
    history: list[Stmt] = []
    committed_stdout_lines: list[str] = []

    while True:
        out.write("seme> ")
        out.flush()

        line = inp.readline()
        if line == "":
            out.write("\n")
            out.flush()
            return 0

        source = line.rstrip("\n")
        if not source.strip():
            continue
        if source.strip() == ":quit":
            return 0

        tokens, lex_diags = lex(source)
        if lex_diags:
            _print_diagnostics(lex_diags, err)
            continue

        program, parse_diags = parse(tokens)
        if parse_diags:
            _print_diagnostics(parse_diags, err)
            continue

        if len(program.statements) != 1:
            _print_diagnostics(
                [
                    Diagnostic(
                        code="PARSE-001",
                        message="REPL accepts exactly one statement per line",
                        line=1,
                        column=1,
                    )
                ],
                err,
            )
            continue

        stmt = program.statements[0]
        type_diags = check_types(_program_for_history(history + [stmt]))
        if type_diags:
            _print_diagnostics(type_diags, err)
            continue

        candidate_program = _program_for_history(history + [stmt])
        stdout_lines, runtime_diags = _execute_repl_program(candidate_program)
        new_stdout_lines = stdout_lines[len(committed_stdout_lines):]
        for runtime_line in new_stdout_lines:
            out.write(f"{runtime_line}\n")
        out.flush()

        if runtime_diags:
            _print_diagnostics(runtime_diags, err)
            continue

        history.append(stmt)
        committed_stdout_lines = stdout_lines


def _cmd_repl() -> int:
    return repl_loop(sys.stdin, sys.stdout, sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seme")
    sub = parser.add_subparsers(dest="command", required=True)

    check_parser = sub.add_parser("check")
    check_parser.add_argument("file")

    run_parser = sub.add_parser("run")
    run_parser.add_argument("file")
    run_parser.add_argument(
        "--backend",
        choices=("vm", "interpreter"),
        default="vm",
        help="Execution backend to use for seme run.",
    )

    sub.add_parser("repl")

    args = parser.parse_args(argv)

    if args.command == "check":
        return _cmd_check(args.file)
    if args.command == "run":
        return _cmd_run(args.file, backend=args.backend)
    if args.command == "repl":
        return _cmd_repl()

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
