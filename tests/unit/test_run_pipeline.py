from __future__ import annotations

from seme.pipeline import run_execute


def test_run_execute_success_output() -> None:
    source = """
for (let i = 0; i < 3; i = i + 1) { print(i); }
print(true);
""".strip()
    stdout, diags = run_execute(source)
    assert diags == []
    assert stdout == "0\n1\n2\ntrue\n"


def test_run_execute_type_error_blocks_runtime() -> None:
    source = "if (1) { print(1); }"
    stdout, diags = run_execute(source)
    assert stdout == ""
    assert diags
    assert diags[0].code.startswith("TYPE-")


def test_run_execute_parse_error_blocks_runtime() -> None:
    source = "let x = 1"
    stdout, diags = run_execute(source)
    assert stdout == ""
    assert diags
    assert diags[0].code == "PARSE-001"


def test_run_execute_lex_error_blocks_runtime() -> None:
    source = "@"
    stdout, diags = run_execute(source)
    assert stdout == ""
    assert diags
    assert diags[0].code == "LEX-001"


def test_run_execute_runtime_error() -> None:
    source = "print(1); let x = 10 / 0; print(x);"
    stdout, diags = run_execute(source)
    assert stdout == "1\n"
    assert diags
    assert diags[0].code == "RUNTIME-001"


def test_run_execute_print_in_value_context_is_type_error() -> None:
    source = "print(1) == print(2);"
    stdout, diags = run_execute(source)
    assert stdout == ""
    assert diags
    assert diags[0].code == "TYPE-008"
