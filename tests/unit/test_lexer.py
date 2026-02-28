from __future__ import annotations

import json
from pathlib import Path

import pytest

from seme.lexer import lex


FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "lexer_cases.json"
CASES = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


    let2 = [tok for tok in tokens if tok.lexeme == "let"][1]
    assert let2.line == 2
    assert let2.column == 1
