from __future__ import annotations

from seme.diagnostics import Diagnostic
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
