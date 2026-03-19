from __future__ import annotations

import json
from pathlib import Path

import pytest

from seme.pipeline import run_execute


RUN_CASES = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "run_cases.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", RUN_CASES, ids=[case["name"] for case in RUN_CASES])
def test_vm_backend_matches_existing_run_conformance(case: dict) -> None:
    stdout, diagnostics = run_execute(case["source"], backend="vm")

    expected_stdout = case.get("expected_stdout", "")
    expected_diagnostics = [
        (
            diag["code"],
            diag["message"],
            diag["line"],
            diag["column"],
        )
        for diag in case.get("expected_diagnostics", [])
    ]

    assert stdout == expected_stdout
    assert [
        (diag.code, diag.message, diag.line, diag.column)
        for diag in diagnostics
    ] == expected_diagnostics


@pytest.mark.parametrize("case", RUN_CASES, ids=[case["name"] for case in RUN_CASES])
def test_vm_and_interpreter_backends_match_on_run_cases(case: dict) -> None:
    vm_stdout, vm_diags = run_execute(case["source"], backend="vm")
    interp_stdout, interp_diags = run_execute(case["source"], backend="interpreter")

    assert vm_stdout == interp_stdout
    assert [
        (diag.code, diag.message, diag.line, diag.column)
        for diag in vm_diags
    ] == [
        (diag.code, diag.message, diag.line, diag.column)
        for diag in interp_diags
    ]
