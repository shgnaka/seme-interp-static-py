from __future__ import annotations

from seme.diagnostics import Diagnostic
from seme.lexer import lex


def run_check(source: str) -> list[Diagnostic]:
    _, diagnostics = lex(source)
    return diagnostics
