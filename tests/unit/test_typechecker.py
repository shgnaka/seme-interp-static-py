from __future__ import annotations

from seme.lexer import lex
from seme.parser import parse
from seme.typechecker import check_types


def check_source(source: str):
    tokens, lex_diags = lex(source)
    assert lex_diags == []
    program, parse_diags = parse(tokens)
    assert parse_diags == []
    return check_types(program)


def codes(diagnostics) -> list[str]:
    return [diag.code for diag in diagnostics]


def test_type001_uninferrable_declaration() -> None:
    diagnostics = check_source("let x;")
    assert "TYPE-001" in codes(diagnostics)


def test_type002_redeclaration_same_scope() -> None:
    diagnostics = check_source("{ let x = 1; let x = 2; }")
    assert "TYPE-002" in codes(diagnostics)


def test_type003_undeclared_variable() -> None:
    diagnostics = check_source("x = 1;")
    assert "TYPE-003" in codes(diagnostics)


def test_type007_if_condition_must_be_bool() -> None:
    diagnostics = check_source("if (1) { let x = 1; }")
    assert "TYPE-007" in codes(diagnostics)


def test_type004_const_reassignment() -> None:
    diagnostics = check_source("const x = 1; x = 2;")
    assert "TYPE-004" in codes(diagnostics)


def test_type005_assignment_and_initializer_mismatch() -> None:
    diagnostics = check_source("let b: bool = 1; let x: int = 1; x = true;")
    found = codes(diagnostics)
    assert "TYPE-005" in found


def test_type006_invalid_operator_operands() -> None:
    diagnostics = check_source("let x = true + 1;")
    assert "TYPE-006" in codes(diagnostics)


def test_type008_invalid_call_shape() -> None:
    diagnostics = check_source("let foo = 1; foo(1); print();")
    assert [
        (d.code, d.message, d.line, d.column)
        for d in diagnostics
    ] == [
        ("TYPE-008", "Only print(expr) call is supported", 1, 17),
        ("TYPE-008", "print requires exactly one argument", 1, 27),
    ]


def test_type008_print_is_statement_only() -> None:
    diagnostics = check_source("let x = print(3);")
    assert [
        (d.code, d.message, d.line, d.column)
        for d in diagnostics
    ] == [
        ("TYPE-008", "print(expr) can only appear as a statement", 1, 14),
    ]


def test_type008_print_bad_arity_in_expression_reports_single_diagnostic() -> None:
    diagnostics = check_source("let x = print();")
    assert [
        (d.code, d.message, d.line, d.column)
        for d in diagnostics
    ] == [
        ("TYPE-008", "print requires exactly one argument", 1, 14),
    ]


def test_collects_multiple_type_errors() -> None:
    diagnostics = check_source("let x; x = true; if (1) { const c = 1; c = 2; }")
    found = codes(diagnostics)
    assert len(found) >= 3
    assert "TYPE-001" in found
    assert "TYPE-007" in found
    assert "TYPE-004" in found


def test_valid_program_has_no_type_diagnostics() -> None:
    source = """
let x = 1;
let y: int = x + 2;
if (x < y) { print(y); } else { print(x); }
for (let i = 0; i < 3; i = i + 1) { print(i); }
""".strip()
    diagnostics = check_source(source)
    assert diagnostics == []
