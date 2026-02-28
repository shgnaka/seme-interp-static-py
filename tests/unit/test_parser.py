from __future__ import annotations

from seme.ast import (
    Assign,
    BinaryExpr,
    BlockStmt,
    CallExpr,
    ExprStmt,
    ForStmt,
    LetDecl,
    WhileStmt,
)
from seme.lexer import lex
from seme.parser import parse
from seme.token import TokenKind


def parse_source(source: str):
    tokens, lex_diags = lex(source)
    assert lex_diags == []
    return parse(tokens)


def test_parse_let_then_assign_statement() -> None:
    program, diags = parse_source("let x = 1; x = x + 1;")
    assert diags == []
    assert len(program.statements) == 2
    assert isinstance(program.statements[0], LetDecl)
    assert isinstance(program.statements[1], Assign)
    assign = program.statements[1]
    assert isinstance(assign.value, BinaryExpr)
    assert assign.value.operator == TokenKind.PLUS


def test_parse_while_block() -> None:
    program, diags = parse_source("while (x < 10) { x = x + 1; }")
    assert diags == []
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, WhileStmt)
    assert isinstance(stmt.body, BlockStmt)
    assert len(stmt.body.statements) == 1
    assert isinstance(stmt.body.statements[0], Assign)


def test_parse_for_with_assignment_update_and_call() -> None:
    source = "for (let i = 0; i < 3; i = i + 1) { print(i); }"
    program, diags = parse_source(source)
    assert diags == []
    stmt = program.statements[0]
    assert isinstance(stmt, ForStmt)
    assert isinstance(stmt.init, LetDecl)
    assert isinstance(stmt.update, Assign)
    assert isinstance(stmt.body, BlockStmt)
    call_stmt = stmt.body.statements[0]
    assert isinstance(call_stmt, ExprStmt)
    assert isinstance(call_stmt.expression, CallExpr)


def test_parse_error_missing_semicolon() -> None:
    program, diags = parse_source("let x = 1")
    assert program is not None
    assert len(diags) >= 1
    assert diags[0].code == "PARSE-001"
    assert "Expected ';' after let declaration" in diags[0].message


def test_parse_let_without_initializer() -> None:
    program, diags = parse_source("let x;")
    assert diags == []
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, LetDecl)
    assert stmt.type_name is None
    assert stmt.initializer is None


def test_parse_const_with_annotation_without_initializer() -> None:
    program, diags = parse_source("const s: string;")
    assert diags == []
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert stmt.name == "s"
    assert stmt.type_name == "string"
    assert stmt.initializer is None


def test_parse_error_recovery_collects_multiple_errors() -> None:
    source = "let a = ;\nlet b = 1\nlet c = 2;"
    program, diags = parse_source(source)
    assert len(diags) >= 2
    assert all(diag.code == "PARSE-001" for diag in diags)
    parsed_let_names = [stmt.name for stmt in program.statements if isinstance(stmt, LetDecl)]
    assert "c" in parsed_let_names
