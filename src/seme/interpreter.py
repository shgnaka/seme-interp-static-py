from __future__ import annotations

from dataclasses import dataclass

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
    Literal,
    Program,
    Stmt,
    Unary,
    While,
)
from seme.diagnostics import Diagnostic
from seme.token import TokenKind

RuntimeValue = int | bool | str
_UNINITIALIZED = object()


@dataclass
class RuntimeBinding:
    value: RuntimeValue | object
    is_const: bool


@dataclass(frozen=True)
class RuntimeFault(Exception):
    message: str
    line: int
    column: int


class Interpreter:
    def __init__(self) -> None:
        self.scopes: list[dict[str, RuntimeBinding]] = [{}]
        self.stdout_lines: list[str] = []

    def execute(self, program: Program) -> tuple[list[str], list[Diagnostic]]:
        start_index = len(self.stdout_lines)
        diagnostics: list[Diagnostic] = []
        try:
            for stmt in program.statements:
                self._eval_stmt(stmt)
            return self.stdout_lines[start_index:], diagnostics
        except RuntimeFault as err:
            diagnostics.append(
                Diagnostic(
                    code="RUNTIME-001",
                    message=f"Runtime error: {err.message}",
                    line=err.line,
                    column=err.column,
                )
            )
            return self.stdout_lines[start_index:], diagnostics
        except Exception as exc:  # pragma: no cover
            diagnostics.append(
                Diagnostic(
                    code="RUNTIME-001",
                    message=f"Runtime error: {exc}",
                    line=program.line,
                    column=program.column,
                )
            )
            return self.stdout_lines[start_index:], diagnostics

    def _eval_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, LetDecl):
            if stmt.initializer is None:
                self._declare(stmt.name, _UNINITIALIZED, is_const=False, line=stmt.line, column=stmt.column)
            else:
                self._declare(
                    stmt.name,
                    self._eval_expr(stmt.initializer),
                    is_const=False,
                    line=stmt.line,
                    column=stmt.column,
                )
            return

        if isinstance(stmt, ConstDecl):
            if stmt.initializer is None:
                self._declare(stmt.name, _UNINITIALIZED, is_const=True, line=stmt.line, column=stmt.column)
            else:
                self._declare(
                    stmt.name,
                    self._eval_expr(stmt.initializer),
                    is_const=True,
                    line=stmt.line,
                    column=stmt.column,
                )
            return

        if isinstance(stmt, Assign):
            value = self._eval_expr(stmt.value)
            self._assign(stmt.name, value, stmt.line, stmt.column)
            return

        if isinstance(stmt, If):
            cond = self._eval_expr(stmt.condition)
            if not isinstance(cond, bool):
                self._runtime_error(stmt.condition.line, stmt.condition.column, "if condition must evaluate to bool")
            if cond:
                self._eval_stmt(stmt.then_branch)
            elif stmt.else_branch is not None:
                self._eval_stmt(stmt.else_branch)
            return

        if isinstance(stmt, While):
            while True:
                cond = self._eval_expr(stmt.condition)
                if not isinstance(cond, bool):
                    self._runtime_error(
                        stmt.condition.line,
                        stmt.condition.column,
                        "while condition must evaluate to bool",
                    )
                if not cond:
                    break
                self._eval_stmt(stmt.body)
            return

        if isinstance(stmt, For):
            self._push_scope()
            try:
                if stmt.init is not None:
                    if isinstance(stmt.init, (LetDecl, ConstDecl, Assign, ExprStmt, If, While, For, Block)):
                        self._eval_stmt(stmt.init)
                    else:
                        self._eval_expr(stmt.init)

                while True:
                    if stmt.condition is not None:
                        cond = self._eval_expr(stmt.condition)
                        if not isinstance(cond, bool):
                            self._runtime_error(
                                stmt.condition.line,
                                stmt.condition.column,
                                "for condition must evaluate to bool",
                            )
                        if not cond:
                            break
                    self._eval_stmt(stmt.body)
                    if stmt.update is not None:
                        if isinstance(stmt.update, Assign):
                            self._eval_stmt(stmt.update)
                        else:
                            self._eval_expr(stmt.update)
            finally:
                self._pop_scope()
            return

        if isinstance(stmt, Block):
            self._push_scope()
            try:
                for nested in stmt.statements:
                    self._eval_stmt(nested)
            finally:
                self._pop_scope()
            return

        if isinstance(stmt, ExprStmt):
            self._eval_expr(stmt.expression)
            return

    def _eval_expr(self, expr: Expr) -> RuntimeValue:
        if isinstance(expr, Literal):
            return expr.value

        if isinstance(expr, Identifier):
            return self._read(expr.name, expr.line, expr.column)

        if isinstance(expr, Grouping):
            return self._eval_expr(expr.expression)

        if isinstance(expr, Unary):
            operand = self._eval_expr(expr.operand)
            if expr.operator == TokenKind.BANG:
                if not isinstance(operand, bool):
                    self._runtime_error(expr.line, expr.column, "operator '!' requires bool operand")
                return not operand
            if expr.operator == TokenKind.MINUS:
                if not self._is_int(operand):
                    self._runtime_error(expr.line, expr.column, "unary '-' requires int operand")
                return -operand
            self._runtime_error(expr.line, expr.column, "unsupported unary operator")

        if isinstance(expr, Binary):
            if expr.operator == TokenKind.ANDAND:
                left = self._eval_expr(expr.left)
                if not isinstance(left, bool):
                    self._runtime_error(expr.line, expr.column, "operator '&&' requires bool operands")
                if not left:
                    return False
                right = self._eval_expr(expr.right)
                if not isinstance(right, bool):
                    self._runtime_error(expr.line, expr.column, "operator '&&' requires bool operands")
                return left and right

            if expr.operator == TokenKind.OROR:
                left = self._eval_expr(expr.left)
                if not isinstance(left, bool):
                    self._runtime_error(expr.line, expr.column, "operator '||' requires bool operands")
                if left:
                    return True
                right = self._eval_expr(expr.right)
                if not isinstance(right, bool):
                    self._runtime_error(expr.line, expr.column, "operator '||' requires bool operands")
                return left or right

            left = self._eval_expr(expr.left)
            right = self._eval_expr(expr.right)
            op = expr.operator

            if op in (TokenKind.PLUS, TokenKind.MINUS, TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT):
                if not self._is_int(left) or not self._is_int(right):
                    self._runtime_error(expr.line, expr.column, "arithmetic operators require int operands")
                if op == TokenKind.PLUS:
                    return left + right
                if op == TokenKind.MINUS:
                    return left - right
                if op == TokenKind.STAR:
                    return left * right
                if right == 0:
                    self._runtime_error(expr.line, expr.column, "division or modulo by zero")
                if op == TokenKind.SLASH:
                    return left // right
                return left % right

            if op in (TokenKind.LT, TokenKind.LTE, TokenKind.GT, TokenKind.GTE):
                if not self._is_int(left) or not self._is_int(right):
                    self._runtime_error(expr.line, expr.column, "comparison operators require int operands")
                if op == TokenKind.LT:
                    return left < right
                if op == TokenKind.LTE:
                    return left <= right
                if op == TokenKind.GT:
                    return left > right
                return left >= right

            if op in (TokenKind.EQEQ, TokenKind.NEQ):
                if type(left) is not type(right):
                    self._runtime_error(expr.line, expr.column, "equality operators require matching types")
                if op == TokenKind.EQEQ:
                    return left == right
                return left != right

            self._runtime_error(expr.line, expr.column, "unsupported binary operator")

        if isinstance(expr, Call):
            if not isinstance(expr.callee, Identifier) or expr.callee.name != "print":
                self._runtime_error(expr.line, expr.column, "only print(expr) call is supported")
            if len(expr.arguments) != 1:
                self._runtime_error(expr.line, expr.column, "print requires exactly one argument")
            value = self._eval_expr(expr.arguments[0])
            self.stdout_lines.append(self._format_value(value))
            return 0

        self._runtime_error(expr.line, expr.column, "unsupported expression")

    def _format_value(self, value: RuntimeValue) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int):
            return str(value)
        return value

    def _declare(self, name: str, value: RuntimeValue | object, is_const: bool, line: int, column: int) -> None:
        scope = self.scopes[-1]
        if name in scope:
            self._runtime_error(line, column, f"redeclaration of '{name}' in same scope")
        scope[name] = RuntimeBinding(value=value, is_const=is_const)

    def _resolve(self, name: str) -> RuntimeBinding | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _read(self, name: str, line: int, column: int) -> RuntimeValue:
        binding = self._resolve(name)
        if binding is None:
            self._runtime_error(line, column, f"undeclared variable '{name}'")
        if binding.value is _UNINITIALIZED:
            self._runtime_error(line, column, f"variable '{name}' is uninitialized")
        return binding.value  # type: ignore[return-value]

    def _assign(self, name: str, value: RuntimeValue, line: int, column: int) -> None:
        binding = self._resolve(name)
        if binding is None:
            self._runtime_error(line, column, f"undeclared variable '{name}'")
        if binding.is_const:
            self._runtime_error(line, column, f"cannot reassign const '{name}'")
        binding.value = value

    def _push_scope(self) -> None:
        self.scopes.append({})

    def _pop_scope(self) -> None:
        self.scopes.pop()

    def _runtime_error(self, line: int, column: int, message: str) -> None:
        raise RuntimeFault(message=message, line=line, column=column)

    def _is_int(self, value: RuntimeValue) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)


def eval_program(program: Program) -> tuple[list[str], list[Diagnostic]]:
    interpreter = Interpreter()
    return interpreter.execute(program)
