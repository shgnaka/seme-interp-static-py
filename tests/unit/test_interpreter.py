from __future__ import annotations

from seme.interpreter import Interpreter, eval_program
from seme.lexer import lex
from seme.parser import parse
from seme.runtime import SemeBool, SemeInt
from seme.typechecker import check_types


def eval_source(source: str):
    tokens, lex_diags = lex(source)
    assert lex_diags == []
    program, parse_diags = parse(tokens)
    assert parse_diags == []
    type_diags = check_types(program)
    assert type_diags == []
    return eval_program(program)


def parse_checked_program(source: str):
    tokens, lex_diags = lex(source)
    assert lex_diags == []
    program, parse_diags = parse(tokens)
    assert parse_diags == []
    type_diags = check_types(program)
    assert type_diags == []
    return program


def test_arithmetic_and_print_output() -> None:
    source = "let x = 1 + 2 * 3; print(x);"
    lines, diags = eval_source(source)
    assert diags == []
    assert lines == ["7"]


def test_if_else_branching() -> None:
    source = "let x = 1; if (x < 2) { print(1); } else { print(2); }"
    lines, diags = eval_source(source)
    assert diags == []
    assert lines == ["1"]


def test_while_loop_accumulation() -> None:
    source = """
let i = 0;
let sum = 0;
while (i < 4) { sum = sum + i; i = i + 1; }
print(sum);
""".strip()
    lines, diags = eval_source(source)
    assert diags == []
    assert lines == ["6"]


def test_for_loop_and_print_sequence() -> None:
    source = "for (let i = 0; i < 3; i = i + 1) { print(i); }"
    lines, diags = eval_source(source)
    assert diags == []
    assert lines == ["0", "1", "2"]


def test_logical_comparison_and_equality() -> None:
    source = """
print(1 == 1);
print(1 != 2);
print(true && false);
print(!false);
print(3 >= 3);
""".strip()
    lines, diags = eval_source(source)
    assert diags == []
    assert lines == ["true", "true", "false", "true", "true"]


def test_runtime_error_divide_by_zero_maps_to_runtime_001() -> None:
    source = "let x = 1 / 0; print(x);"
    lines, diags = eval_source(source)
    assert lines == []
    assert len(diags) == 1
    assert diags[0].code == "RUNTIME-001"
    assert "division or modulo by zero" in diags[0].message


def test_runtime_error_uninitialized_variable() -> None:
    source = "let x: int; print(x);"
    lines, diags = eval_source(source)
    assert lines == []
    assert len(diags) == 1
    assert diags[0].code == "RUNTIME-001"
    assert "uninitialized" in diags[0].message


def test_interpreter_stores_runtime_value_objects_in_bindings() -> None:
    program = parse_checked_program("let x = 1 + 2; let ok = x == 3;")
    interpreter = Interpreter()

    lines, diags = interpreter.execute(program)

    assert lines == []
    assert diags == []
    assert interpreter._resolve("x").value == SemeInt(3)
    assert interpreter._resolve("ok").value == SemeBool(True)
