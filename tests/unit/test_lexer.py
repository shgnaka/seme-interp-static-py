from __future__ import annotations

import json
from pathlib import Path

import pytest

from seme.lexer import lex


FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "lexer_cases.json"
CASES = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_lexer_cases(case: dict) -> None:
    tokens, diagnostics = lex(case["source"])
    got_kinds = [tok.kind.name for tok in tokens if tok.kind.name != "EOF"]
    assert got_kinds == case["expected_token_kinds"]

    expected_diags = case.get("expected_diagnostics", [])
    assert len(diagnostics) == len(expected_diags)
    for got, expected in zip(diagnostics, expected_diags):
        assert got.code == expected["code"]
        assert got.line == expected["line"]
        assert got.column == expected["column"]


def test_line_and_column_tracking_after_newline() -> None:
    source = "let x = 1;\nlet y = 2;"
    tokens, diagnostics = lex(source)
    assert diagnostics == []
    let_tokens = [tok for tok in tokens if tok.lexeme == "let"]
    assert len(let_tokens) == 2
    assert let_tokens[1].line == 2
    assert let_tokens[1].column == 1
