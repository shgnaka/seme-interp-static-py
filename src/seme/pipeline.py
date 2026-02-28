from __future__ import annotations

from seme.diagnostics import Diagnostic
from seme.lexer import lex
from seme.parser import parse


def run_check(source: str) -> list[Diagnostic]:
    tokens, lex_diags = lex(source)
    if lex_diags:
        return lex_diags
    _, parse_diags = parse(tokens)
    return parse_diags
