from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from seme.ast import (
    Assign,
    Binary,
    Block,
    Call,
    ConstDecl,
    Expr,
    ExprStmt,
    For,
    Grouping,
    Identifier,
    If,
    LetDecl,
    Literal as LiteralExpr,
    Program,
    Stmt,
    Unary,
    While,
)
from seme.diagnostics import Diagnostic
from seme.token import TokenKind

TypeName = Literal["int", "bool", "string"]

TYPE_INT: TypeName = "int"
TYPE_BOOL: TypeName = "bool"
TYPE_STRING: TypeName = "string"
TYPE_UNKNOWN = "<unknown>"


@dataclass
class Symbol:
    name: str
    type_name: str
    is_const: bool
    line: int
    column: int


class TypeChecker:
    def __init__(self) -> None:
        self.scopes: list[dict[str, Symbol]] = [{}]
        self.diagnostics: list[Diagnostic] = []

    def check(self, program: Program) -> list[Diagnostic]:
        for stmt in program.statements:
            self._check_stmt(stmt)
        return self.diagnostics

    def _check_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, LetDecl):
            self._check_let_decl(stmt)
            return
        if isinstance(stmt, ConstDecl):
            self._check_const_decl(stmt)
            return
        if isinstance(stmt, Assign):
            self._check_assign(stmt)
            return
        if isinstance(stmt, If):
            cond_type = self._check_expr(stmt.condition)
            if cond_type != TYPE_BOOL and cond_type != TYPE_UNKNOWN:
                self._diag("TYPE-007", "if condition must be bool", stmt.condition.line, stmt.condition.column)
            self._check_stmt(stmt.then_branch)
            if stmt.else_branch is not None:
                self._check_stmt(stmt.else_branch)
            return
        if isinstance(stmt, While):
            cond_type = self._check_expr(stmt.condition)
            if cond_type != TYPE_BOOL and cond_type != TYPE_UNKNOWN:
                self._diag(
                    "TYPE-007",
                    "while condition must be bool",
                    stmt.condition.line,
                    stmt.condition.column,
                )
            self._check_stmt(stmt.body)
            return
        if isinstance(stmt, For):
            self._push_scope()
            if stmt.init is not None:
                if isinstance(stmt.init, (LetDecl, ConstDecl, Assign, ExprStmt, If, While, For, Block)):
                    self._check_stmt(stmt.init)
                else:
                    self._check_expr(stmt.init)
            if stmt.condition is not None:
                cond_type = self._check_expr(stmt.condition)
                if cond_type != TYPE_BOOL and cond_type != TYPE_UNKNOWN:
                    self._diag(
                        "TYPE-007",
                        "for condition must be bool",
                        stmt.condition.line,
                        stmt.condition.column,
                    )
            if stmt.update is not None:
                if isinstance(stmt.update, Assign):
                    self._check_assign(stmt.update)
                else:
                    self._check_expr(stmt.update)
            self._check_stmt(stmt.body)
            self._pop_scope()
            return
        if isinstance(stmt, Block):
            self._push_scope()
            for nested in stmt.statements:
                self._check_stmt(nested)
            self._pop_scope()
            return
        if isinstance(stmt, ExprStmt):
            if isinstance(stmt.expression, Call) and self._is_print_call(stmt.expression):
                self._check_print_stmt(stmt.expression)
                return
            self._check_expr(stmt.expression)
            return

    def _check_let_decl(self, decl: LetDecl) -> None:
        inferred = TYPE_UNKNOWN
        if decl.initializer is not None:
            inferred = self._check_expr(decl.initializer)

        declared = decl.type_name
        if declared is None and decl.initializer is None:
            self._diag(
                "TYPE-001",
                "Cannot infer type without annotation or initializer",
                decl.line,
                decl.column,
            )
            final_type = TYPE_UNKNOWN
        elif declared is None:
            final_type = inferred
        else:
            final_type = declared
            if decl.initializer is not None and inferred != TYPE_UNKNOWN and inferred != declared:
                self._diag(
                    "TYPE-005",
                    f"Initializer type mismatch: expected {declared}, got {inferred}",
                    decl.initializer.line,
                    decl.initializer.column,
                )

        self._declare(
            name=decl.name,
            symbol=Symbol(
                name=decl.name,
                type_name=final_type,
                is_const=False,
                line=decl.line,
                column=decl.column,
            ),
            line=decl.line,
            column=decl.column,
        )

    def _check_const_decl(self, decl: ConstDecl) -> None:
        inferred = TYPE_UNKNOWN
        if decl.initializer is not None:
            inferred = self._check_expr(decl.initializer)

        declared = decl.type_name
        if declared is None and decl.initializer is None:
            self._diag(
                "TYPE-001",
                "Cannot infer type without annotation or initializer",
                decl.line,
                decl.column,
            )
            final_type = TYPE_UNKNOWN
        elif declared is None:
            final_type = inferred
        else:
            final_type = declared
            if decl.initializer is not None and inferred != TYPE_UNKNOWN and inferred != declared:
                self._diag(
                    "TYPE-005",
                    f"Initializer type mismatch: expected {declared}, got {inferred}",
                    decl.initializer.line,
                    decl.initializer.column,
                )

        self._declare(
            name=decl.name,
            symbol=Symbol(
                name=decl.name,
                type_name=final_type,
                is_const=True,
                line=decl.line,
                column=decl.column,
            ),
            line=decl.line,
            column=decl.column,
        )

    def _check_assign(self, assign: Assign) -> None:
        value_type = self._check_expr(assign.value)
        symbol = self._resolve(assign.name)
        if symbol is None:
            self._diag("TYPE-003", f"Undeclared variable '{assign.name}'", assign.line, assign.column)
            return
        if symbol.is_const:
            self._diag("TYPE-004", f"Cannot reassign const '{assign.name}'", assign.line, assign.column)
            return
        if symbol.type_name == TYPE_UNKNOWN and value_type != TYPE_UNKNOWN:
            symbol.type_name = value_type
            return
        if value_type != TYPE_UNKNOWN and symbol.type_name != TYPE_UNKNOWN and value_type != symbol.type_name:
            self._diag(
                "TYPE-005",
                f"Assignment type mismatch: expected {symbol.type_name}, got {value_type}",
                assign.value.line,
                assign.value.column,
            )

    def _check_expr(self, expr: Expr) -> str:
        if isinstance(expr, LiteralExpr):
            if isinstance(expr.value, bool):
                return TYPE_BOOL
            if isinstance(expr.value, int):
                return TYPE_INT
            return TYPE_STRING

        if isinstance(expr, Identifier):
            symbol = self._resolve(expr.name)
            if symbol is None:
                self._diag("TYPE-003", f"Undeclared variable '{expr.name}'", expr.line, expr.column)
                return TYPE_UNKNOWN
            return symbol.type_name

        if isinstance(expr, Grouping):
            return self._check_expr(expr.expression)

        if isinstance(expr, Unary):
            operand = self._check_expr(expr.operand)
            if expr.operator == TokenKind.BANG:
                if operand not in (TYPE_BOOL, TYPE_UNKNOWN):
                    self._diag("TYPE-006", "Operator '!' requires bool operand", expr.line, expr.column)
                return TYPE_BOOL
            if expr.operator == TokenKind.MINUS:
                if operand not in (TYPE_INT, TYPE_UNKNOWN):
                    self._diag("TYPE-006", "Unary '-' requires int operand", expr.line, expr.column)
                return TYPE_INT
            self._diag("TYPE-006", "Unsupported unary operator", expr.line, expr.column)
            return TYPE_UNKNOWN

        if isinstance(expr, Binary):
            left = self._check_expr(expr.left)
            right = self._check_expr(expr.right)
            op = expr.operator

            if op in (TokenKind.PLUS, TokenKind.MINUS, TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT):
                if left not in (TYPE_INT, TYPE_UNKNOWN) or right not in (TYPE_INT, TYPE_UNKNOWN):
                    self._diag("TYPE-006", "Arithmetic operators require int operands", expr.line, expr.column)
                return TYPE_INT

            if op in (TokenKind.LT, TokenKind.LTE, TokenKind.GT, TokenKind.GTE):
                if left not in (TYPE_INT, TYPE_UNKNOWN) or right not in (TYPE_INT, TYPE_UNKNOWN):
                    self._diag("TYPE-006", "Comparison operators require int operands", expr.line, expr.column)
                return TYPE_BOOL

            if op in (TokenKind.EQEQ, TokenKind.NEQ):
                if left != TYPE_UNKNOWN and right != TYPE_UNKNOWN and left != right:
                    self._diag("TYPE-006", "Equality operators require matching operand types", expr.line, expr.column)
                return TYPE_BOOL

            if op in (TokenKind.ANDAND, TokenKind.OROR):
                if left not in (TYPE_BOOL, TYPE_UNKNOWN) or right not in (TYPE_BOOL, TYPE_UNKNOWN):
                    self._diag("TYPE-006", "Logical operators require bool operands", expr.line, expr.column)
                return TYPE_BOOL

            self._diag("TYPE-006", "Unsupported binary operator", expr.line, expr.column)
            return TYPE_UNKNOWN

        if isinstance(expr, Call):
            if self._is_print_call(expr):
                for arg in expr.arguments:
                    self._check_expr(arg)
                if len(expr.arguments) != 1:
                    self._diag("TYPE-008", "print requires exactly one argument", expr.line, expr.column)
                    return TYPE_UNKNOWN
                self._diag("TYPE-008", "print(expr) can only appear as a statement", expr.line, expr.column)
                return TYPE_UNKNOWN

            self._check_expr(expr.callee)
            for arg in expr.arguments:
                self._check_expr(arg)
            self._diag("TYPE-008", "Only print(expr) call is supported", expr.line, expr.column)
            return TYPE_UNKNOWN

        self._diag("TYPE-006", "Unsupported expression", expr.line, expr.column)
        return TYPE_UNKNOWN

    def _declare(self, name: str, symbol: Symbol, line: int, column: int) -> None:
        current = self.scopes[-1]
        if name in current:
            self._diag("TYPE-002", f"Redeclaration of '{name}' in same scope", line, column)
            return
        current[name] = symbol

    def _is_print_call(self, expr: Expr) -> bool:
        return isinstance(expr, Call) and isinstance(expr.callee, Identifier) and expr.callee.name == "print"

    def _check_print_stmt(self, call: Call) -> None:
        for arg in call.arguments:
            self._check_expr(arg)
        if len(call.arguments) != 1:
            self._diag("TYPE-008", "print requires exactly one argument", call.line, call.column)

    def _resolve(self, name: str) -> Symbol | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _push_scope(self) -> None:
        self.scopes.append({})

    def _pop_scope(self) -> None:
        self.scopes.pop()

    def _diag(self, code: str, message: str, line: int, column: int) -> None:
        self.diagnostics.append(Diagnostic(code=code, message=message, line=line, column=column))


def check_types(program: Program) -> list[Diagnostic]:
    return TypeChecker().check(program)
