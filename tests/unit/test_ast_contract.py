from __future__ import annotations

from dataclasses import fields, is_dataclass

from seme.ast import (
    Assign,
    Binary,
    Block,
    Call,
    ConstDecl,
    ExprStmt,
    For,
    Identifier,
    If,
    LetDecl,
    Literal,
    Program,
    While,
)
from seme.lexer import lex
from seme.parser import parse


def parse_source(source: str) -> tuple[Program, list]:
    tokens, lex_diags = lex(source)
    assert lex_diags == []
    return parse(tokens)


def _collect_ast_nodes(node: object) -> list[object]:
    seen: list[object] = []
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, list):
            stack.extend(current)
            continue
        if is_dataclass(current) and current.__class__.__module__ == "seme.ast":
            seen.append(current)
            for field in fields(current):
                stack.append(getattr(current, field.name))
    return seen


def test_phase3_canonical_stmt_and_expr_nodes() -> None:
    source = """
let x: int = 1;
const y = 2;
if (x < y) { x = x + 1; } else { x = x - 1; }
while (x < 10) { x = x + 1; }
for (let i = 0; i < 3; i = i + 1) { print(i); }
print(x);
""".strip()

    program, diags = parse_source(source)
    assert diags == []
    assert len(program.statements) == 6

    assert isinstance(program.statements[0], LetDecl)
    assert isinstance(program.statements[1], ConstDecl)
    assert isinstance(program.statements[2], If)
    assert isinstance(program.statements[3], While)
    assert isinstance(program.statements[4], For)
    assert isinstance(program.statements[5], ExprStmt)

    if_stmt = program.statements[2]
    assert isinstance(if_stmt.then_branch, Block)
    while_stmt = program.statements[3]
    assert isinstance(while_stmt.body, Block)
    for_stmt = program.statements[4]
    assert isinstance(for_stmt.init, LetDecl)
    assert isinstance(for_stmt.update, Assign)
    assert isinstance(for_stmt.body, Block)
    call_stmt = for_stmt.body.statements[0]
    assert isinstance(call_stmt, ExprStmt)
    assert isinstance(call_stmt.expression, Call)
    assert isinstance(call_stmt.expression.callee, Identifier)
    assert isinstance(program.statements[0].initializer, Literal)
    assign_in_if = if_stmt.then_branch.statements[0]
    assert isinstance(assign_in_if, Assign)
    assert isinstance(assign_in_if.value, Binary)


def test_all_ast_nodes_have_position_fields() -> None:
    source = "let x = 1; if (x < 3) { x = x + 1; }"
    program, diags = parse_source(source)
    assert diags == []

    nodes = _collect_ast_nodes(program)
    assert nodes
    for node in nodes:
        assert hasattr(node, "line")
        assert hasattr(node, "column")
        line = getattr(node, "line")
        column = getattr(node, "column")
        assert isinstance(line, int)
        assert isinstance(column, int)
        assert line >= 1
        assert column >= 1


def test_parser_returns_program_on_syntax_error() -> None:
    source = "let = 1;"
    tokens, lex_diags = lex(source)
    assert lex_diags == []

    program, diags = parse(tokens)
    assert isinstance(program, Program)
    assert len(diags) >= 1
    assert all(diag.code == "PARSE-001" for diag in diags)


def test_program_location_tracks_first_statement() -> None:
    source = "\n\nlet x = 1;"
    program, diags = parse_source(source)
    assert diags == []
    assert program.line == 3
    assert program.column == 1
