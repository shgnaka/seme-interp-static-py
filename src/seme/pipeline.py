from __future__ import annotations

from seme.diagnostics import Diagnostic
from seme.interpreter import eval_program
from seme.lexer import lex
from seme.parser import parse
from seme.typechecker import check_types


def run_check(source: str) -> list[Diagnostic]:
    tokens, lex_diags = lex(source)
    if lex_diags:
        return lex_diags
    program, parse_diags = parse(tokens)
    if parse_diags:
        return parse_diags
    return check_types(program)


def run_execute(source: str) -> tuple[str, list[Diagnostic]]:
    tokens, lex_diags = lex(source)
    if lex_diags:
        return "", lex_diags

    program, parse_diags = parse(tokens)
    if parse_diags:
        return "", parse_diags

    type_diags = check_types(program)
    if type_diags:
        return "", type_diags

    stdout_lines, runtime_diags = eval_program(program)
    stdout_text = ""
    if stdout_lines:
        stdout_text = "\n".join(stdout_lines) + "\n"
    if runtime_diags:
        return stdout_text, runtime_diags
    return stdout_text, []
