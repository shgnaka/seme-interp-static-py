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
class If:
    condition: "Expr"
    then_branch: "Stmt"
    else_branch: "Stmt | None"
    line: int
    column: int


@dataclass(frozen=True)
class While:
    condition: "Expr"
    body: "Stmt"
    line: int
    column: int


@dataclass(frozen=True)
class For:
    init: "Stmt | Expr | None"
    condition: "Expr | None"
    update: "Expr | Assign | None"
    body: "Stmt"
    line: int
    column: int


@dataclass(frozen=True)
class Block:
    statements: list["Stmt"]
    line: int
    column: int


@dataclass(frozen=True)
class ExprStmt:
    expression: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class Binary:
    left: "Expr"
    operator: TokenKind
    right: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class Unary:
    operator: TokenKind
    operand: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class Literal:
    value: int | str | bool
    line: int
    column: int


@dataclass(frozen=True)
class Identifier:
    name: str
    line: int
    column: int


@dataclass(frozen=True)
class Grouping:
    expression: "Expr"
    line: int
    column: int


@dataclass(frozen=True)
class Call:
    callee: "Expr"
    arguments: list["Expr"]
    line: int
    column: int


Stmt = LetDecl | ConstDecl | Assign | If | While | For | Block | ExprStmt
Expr = Binary | Unary | Literal | Identifier | Grouping | Call

# Backward-compat aliases for earlier Phase 2 naming.
IfStmt = If
WhileStmt = While
ForStmt = For
BlockStmt = Block
BinaryExpr = Binary
UnaryExpr = Unary
LiteralExpr = Literal
IdentifierExpr = Identifier
GroupingExpr = Grouping
CallExpr = Call

__all__ = [
    "Program",
    "LetDecl",
    "ConstDecl",
    "Assign",
    "If",
    "While",
    "For",
    "Block",
    "ExprStmt",
    "Binary",
    "Unary",
    "Literal",
    "Identifier",
    "Grouping",
    "Call",
    "Stmt",
    "Expr",
    "IfStmt",
    "WhileStmt",
    "ForStmt",
    "BlockStmt",
    "BinaryExpr",
    "UnaryExpr",
    "LiteralExpr",
    "IdentifierExpr",
    "GroupingExpr",
    "CallExpr",
]
