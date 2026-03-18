from __future__ import annotations

from seme.compiler import compile_program
from seme.lexer import lex
from seme.parser import parse
from seme.runtime import SemeBool, SemeInt
from seme.typechecker import check_types
from seme.vm import VirtualMachine, execute_chunk


def execute_source(source: str):
    tokens, lex_diags = lex(source)
    assert lex_diags == []
    program, parse_diags = parse(tokens)
    assert parse_diags == []
    type_diags = check_types(program)
    assert type_diags == []
    chunk = compile_program(program)
    return execute_chunk(chunk)


def compile_checked_chunk(source: str):
    tokens, lex_diags = lex(source)
    assert lex_diags == []
    program, parse_diags = parse(tokens)
    assert parse_diags == []
    type_diags = check_types(program)
    assert type_diags == []
    return compile_program(program)


def test_vm_executes_basic_program_and_prints_output() -> None:
    stdout_lines, diags = execute_source("let x = 1 + 2 * 3; print(x); print(true);")

    assert diags == []
    assert stdout_lines == ["7", "true"]


def test_vm_executes_control_flow_program() -> None:
    source = """
let sum = 0;
for (let i = 0; i < 3; i = i + 1) {
  if (i < 2) {
    sum = sum + i;
  }
}
print(sum);
""".strip()
    stdout_lines, diags = execute_source(source)

    assert diags == []
    assert stdout_lines == ["1"]


def test_vm_maps_divide_by_zero_to_runtime_001() -> None:
    stdout_lines, diags = execute_source("print(1); let x = 10 / 0; print(x);")

    assert stdout_lines == ["1"]
    assert len(diags) == 1
    assert diags[0].code == "RUNTIME-001"
    assert "division or modulo by zero" in diags[0].message


def test_vm_maps_uninitialized_read_to_runtime_001() -> None:
    stdout_lines, diags = execute_source("let x: int; print(x);")

    assert stdout_lines == []
    assert len(diags) == 1
    assert diags[0].code == "RUNTIME-001"
    assert "uninitialized" in diags[0].message


def test_vm_short_circuits_logical_and_and_or() -> None:
    source = """
print(false && (1 / 0 == 0));
print(true || (1 / 0 == 0));
""".strip()
    stdout_lines, diags = execute_source(source)

    assert diags == []
    assert stdout_lines == ["false", "true"]


def test_vm_runtime_fault_reports_original_source_location() -> None:
    source = """
print(1);
let x = 10 / 0;
print(x);
""".strip()
    stdout_lines, diags = execute_source(source)

    assert stdout_lines == ["1"]
    assert [(d.code, d.line, d.column) for d in diags] == [
        ("RUNTIME-001", 2, 12),
    ]


def test_vm_keeps_runtime_value_objects_in_local_slots() -> None:
    chunk = compile_checked_chunk("let x = 1 + 2; let ok = x == 3;")
    vm = VirtualMachine(chunk)

    stdout_lines, diags = vm.execute()

    assert stdout_lines == []
    assert diags == []
    assert vm.locals[:2] == [SemeInt(3), SemeBool(True)]
