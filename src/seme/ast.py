from __future__ import annotations

from dataclasses import dataclass

from seme.token import TokenKind


@dataclass(frozen=True)
class Program:
    statements: list["Stmt"]
    line: int = 1
    column: int = 1


@dataclass(frozen=True)
class LetDecl:
    name: str
    initializer: "Expr"
    type_name: str | None
    line: int
    column: int


@dataclass(frozen=True)
class ConstDecl:
    name: str
    initializer: "Expr"
    type_name: str | None
    line: int
    column: int


@dataclass(frozen=True)
class Assign:
    name: str
    value: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class IfStmt:
    condition: "Expr"
    then_branch: "Stmt"
    else_branch: "Stmt | None"
    line: int
    column: int


@dataclass(frozen=True)
class WhileStmt:
    condition: "Expr"
    body: "Stmt"
    line: int
    column: int


@dataclass(frozen=True)
class ForStmt:
    init: "Stmt | Expr | None"
    condition: "Expr | None"
    update: "Expr | Assign | None"
    body: "Stmt"
    line: int
    column: int


@dataclass(frozen=True)
class BlockStmt:
    statements: list["Stmt"]
    line: int
    column: int


@dataclass(frozen=True)
class ExprStmt:
    expression: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class BinaryExpr:
    left: "Expr"
    operator: TokenKind
    right: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class UnaryExpr:
    operator: TokenKind
    operand: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class LiteralExpr:
    value: int | str | bool
    line: int
    column: int


@dataclass(frozen=True)
class IdentifierExpr:
    name: str
    line: int
    column: int


@dataclass(frozen=True)
class GroupingExpr:
    expression: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class CallExpr:
    callee: "Expr"
    arguments: list["Expr"]
    line: int
    column: int


Stmt = LetDecl | ConstDecl | Assign | IfStmt | WhileStmt | ForStmt | BlockStmt | ExprStmt
Expr = BinaryExpr | UnaryExpr | LiteralExpr | IdentifierExpr | GroupingExpr | CallExpr
