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
    assert [
        (d.code, d.message, d.line, d.column)
        for d in diags
    ] == [
        ("TYPE-008", "print(expr) can only appear as a statement", 1, 6),
        ("TYPE-008", "print(expr) can only appear as a statement", 1, 18),
    ]


def test_run_execute_print_bad_arity_in_value_context_is_single_type_error() -> None:
    source = "let x = print();"
    stdout, diags = run_execute(source)
    assert stdout == ""
    assert [
        (d.code, d.message, d.line, d.column)
        for d in diags
    ] == [
        ("TYPE-008", "print requires exactly one argument", 1, 14),
    ]


def test_run_execute_vm_and_interpreter_backends_match() -> None:
    source = """
let sum = 0;
for (let i = 0; i < 4; i = i + 1) {
  if (i < 3) {
    sum = sum + i;
  }
}
print(sum);
""".strip()
    vm_stdout, vm_diags = run_execute(source, backend="vm")
    interp_stdout, interp_diags = run_execute(source, backend="interpreter")

    assert vm_stdout == interp_stdout
    assert [(d.code, d.message, d.line, d.column) for d in vm_diags] == [
        (d.code, d.message, d.line, d.column) for d in interp_diags
    ]
