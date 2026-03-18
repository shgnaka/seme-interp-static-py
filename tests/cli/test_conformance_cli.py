from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from seme.cli import main


FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"
DIAGNOSTIC_RE = re.compile(
    r"^(?P<code>\S+)\s+(?P<line>\d+):(?P<column>\d+)\s+(?P<message>.*?)(?:\s+\(suggestion:\s+(?P<suggestion>.*)\))?$"
)


def _load_cases(file_name: str) -> list[dict]:
    return json.loads((FIXTURES_DIR / file_name).read_text(encoding="utf-8"))


def _parse_diagnostics(stderr: str) -> list[dict[str, object]]:
    diagnostics: list[dict[str, object]] = []
    for line in stderr.splitlines():
        match = DIAGNOSTIC_RE.match(line)
        if match is None:
            raise AssertionError(f"Unexpected diagnostic format: {line!r}")
        diagnostic = {
            "code": match.group("code"),
            "message": match.group("message"),
            "line": int(match.group("line")),
            "column": int(match.group("column")),
        }
        suggestion = match.group("suggestion")
        if suggestion is not None:
            diagnostic["suggestion"] = suggestion
        diagnostics.append(diagnostic)
    return diagnostics


def _run_case(command: str, case: dict, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source_file = tmp_path / f"{case['name'].replace(' ', '_')}.seme"
    source_file.write_text(case["source"], encoding="utf-8")

    exit_code = main([command, str(source_file)])
    captured = capsys.readouterr()

    assert exit_code == case["expected_exit_code"]
    assert captured.out == case.get("expected_stdout", "")
    assert _parse_diagnostics(captured.err) == case.get("expected_diagnostics", [])


CHECK_CASES = _load_cases("check_cases.json")
RUN_CASES = _load_cases("run_cases.json")


@pytest.mark.parametrize("case", CHECK_CASES, ids=[case["name"] for case in CHECK_CASES])
def test_check_conformance_cases(
    case: dict, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _run_case("check", case, tmp_path, capsys)


@pytest.mark.parametrize("case", RUN_CASES, ids=[case["name"] for case in RUN_CASES])
def test_run_conformance_cases(
    case: dict, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _run_case("run", case, tmp_path, capsys)
