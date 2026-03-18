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
from seme.runtime import (
    RuntimeValue,
    RuntimeValueError,
    SemeBool,
    SemeInt,
    SemeString,
    StackValue,
    UNINITIALIZED,
    VOID,
    expect_bool,
    format_runtime_value,
    make_runtime_value,
    require_runtime_value,
    runtime_arithmetic,
    runtime_compare,
    runtime_equal,
    runtime_negate,
    runtime_not,
)
from seme.token import TokenKind

EvalValue = StackValue


@dataclass
class RuntimeBinding:
    value: EvalValue
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
                self._declare(stmt.name, UNINITIALIZED, is_const=False, line=stmt.line, column=stmt.column)
            else:
                self._declare(
                    stmt.name,
                    self._require_runtime_value(
                        self._eval_expr(stmt.initializer),
                        stmt.initializer.line,
                        stmt.initializer.column,
                    ),
                    is_const=False,
                    line=stmt.line,
                    column=stmt.column,
                )
            return

        if isinstance(stmt, ConstDecl):
            if stmt.initializer is None:
                self._declare(stmt.name, UNINITIALIZED, is_const=True, line=stmt.line, column=stmt.column)
            else:
                self._declare(
                    stmt.name,
                    self._require_runtime_value(
                        self._eval_expr(stmt.initializer),
                        stmt.initializer.line,
                        stmt.initializer.column,
                    ),
                    is_const=True,
                    line=stmt.line,
                    column=stmt.column,
                )
            return

        if isinstance(stmt, Assign):
            value = self._require_runtime_value(
                self._eval_expr(stmt.value),
                stmt.value.line,
                stmt.value.column,
            )
            self._assign(stmt.name, value, stmt.line, stmt.column)
            return

        if isinstance(stmt, If):
            cond = self._require_runtime_value(
                self._eval_expr(stmt.condition),
                stmt.condition.line,
                stmt.condition.column,
            )
            try:
                cond_value = expect_bool(cond, "if condition must evaluate to bool")
            except RuntimeValueError as err:
                self._runtime_error(stmt.condition.line, stmt.condition.column, err.message)
            if cond_value:
                self._eval_stmt(stmt.then_branch)
            elif stmt.else_branch is not None:
                self._eval_stmt(stmt.else_branch)
            return

        if isinstance(stmt, While):
            while True:
                cond = self._require_runtime_value(
                    self._eval_expr(stmt.condition),
                    stmt.condition.line,
                    stmt.condition.column,
                )
                try:
                    cond_value = expect_bool(cond, "while condition must evaluate to bool")
                except RuntimeValueError as err:
                    self._runtime_error(stmt.condition.line, stmt.condition.column, err.message)
                if not cond_value:
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
                        cond = self._require_runtime_value(
                            self._eval_expr(stmt.condition),
                            stmt.condition.line,
                            stmt.condition.column,
                        )
                        try:
                            cond_value = expect_bool(cond, "for condition must evaluate to bool")
                        except RuntimeValueError as err:
                            self._runtime_error(stmt.condition.line, stmt.condition.column, err.message)
                        if not cond_value:
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

    def _eval_expr(self, expr: Expr) -> EvalValue:
        if isinstance(expr, Literal):
            return make_runtime_value(expr.value)

        if isinstance(expr, Identifier):
            return self._read(expr.name, expr.line, expr.column)

        if isinstance(expr, Grouping):
            return self._eval_expr(expr.expression)

        if isinstance(expr, Unary):
            operand = self._require_runtime_value(
                self._eval_expr(expr.operand),
                expr.operand.line,
                expr.operand.column,
            )
            try:
                if expr.operator == TokenKind.BANG:
                    return runtime_not(operand)
                if expr.operator == TokenKind.MINUS:
                    return runtime_negate(operand)
                self._runtime_error(expr.line, expr.column, "unsupported unary operator")
            except RuntimeValueError as err:
                self._runtime_error(expr.line, expr.column, err.message)

        if isinstance(expr, Binary):
            if expr.operator == TokenKind.ANDAND:
                left = self._require_runtime_value(
                    self._eval_expr(expr.left),
                    expr.left.line,
                    expr.left.column,
                )
                try:
                    left_value = expect_bool(left, "operator '&&' requires bool operands")
                except RuntimeValueError as err:
                    self._runtime_error(expr.line, expr.column, err.message)
                if not left_value:
                    return SemeBool(False)
                right = self._require_runtime_value(
                    self._eval_expr(expr.right),
                    expr.right.line,
                    expr.right.column,
                )
                try:
                    return SemeBool(left_value and expect_bool(right, "operator '&&' requires bool operands"))
                except RuntimeValueError as err:
                    self._runtime_error(expr.line, expr.column, err.message)

            if expr.operator == TokenKind.OROR:
                left = self._require_runtime_value(
                    self._eval_expr(expr.left),
                    expr.left.line,
                    expr.left.column,
                )
                try:
                    left_value = expect_bool(left, "operator '||' requires bool operands")
                except RuntimeValueError as err:
                    self._runtime_error(expr.line, expr.column, err.message)
                if left_value:
                    return SemeBool(True)
                right = self._require_runtime_value(
                    self._eval_expr(expr.right),
                    expr.right.line,
                    expr.right.column,
                )
                try:
                    return SemeBool(left_value or expect_bool(right, "operator '||' requires bool operands"))
                except RuntimeValueError as err:
                    self._runtime_error(expr.line, expr.column, err.message)

            left = self._require_runtime_value(
                self._eval_expr(expr.left),
                expr.left.line,
                expr.left.column,
            )
            right = self._require_runtime_value(
                self._eval_expr(expr.right),
                expr.right.line,
                expr.right.column,
            )
            op = expr.operator

            try:
                if op == TokenKind.PLUS:
                    return runtime_arithmetic("add", left, right)
                if op == TokenKind.MINUS:
                    return runtime_arithmetic("sub", left, right)
                if op == TokenKind.STAR:
                    return runtime_arithmetic("mul", left, right)
                if op == TokenKind.SLASH:
                    return runtime_arithmetic("div", left, right)
                if op == TokenKind.PERCENT:
                    return runtime_arithmetic("mod", left, right)
                if op == TokenKind.LT:
                    return runtime_compare("lt", left, right)
                if op == TokenKind.LTE:
                    return runtime_compare("lte", left, right)
                if op == TokenKind.GT:
                    return runtime_compare("gt", left, right)
                if op == TokenKind.GTE:
                    return runtime_compare("gte", left, right)
                if op == TokenKind.EQEQ:
                    return runtime_equal("eq", left, right)
                if op == TokenKind.NEQ:
                    return runtime_equal("neq", left, right)
                self._runtime_error(expr.line, expr.column, "unsupported binary operator")
            except RuntimeValueError as err:
                self._runtime_error(expr.line, expr.column, err.message)

        if isinstance(expr, Call):
            if not isinstance(expr.callee, Identifier) or expr.callee.name != "print":
                self._runtime_error(expr.line, expr.column, "only print(expr) call is supported")
            if len(expr.arguments) != 1:
                self._runtime_error(expr.line, expr.column, "print requires exactly one argument")
            value = self._require_runtime_value(
                self._eval_expr(expr.arguments[0]),
                expr.arguments[0].line,
                expr.arguments[0].column,
            )
            self.stdout_lines.append(format_runtime_value(value))
            return VOID

        self._runtime_error(expr.line, expr.column, "unsupported expression")

    def _declare(self, name: str, value: StackValue, is_const: bool, line: int, column: int) -> None:
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
        if binding.value is UNINITIALIZED:
            self._runtime_error(line, column, f"variable '{name}' is uninitialized")
        return self._require_runtime_value(binding.value, line, column)

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

    def _require_runtime_value(self, value: EvalValue, line: int, column: int) -> RuntimeValue:
        try:
            resolved = require_runtime_value(value)
        except RuntimeValueError as err:
            self._runtime_error(line, column, err.message)
        if not isinstance(resolved, (SemeInt, SemeBool, SemeString)):
            self._runtime_error(line, column, "invalid runtime value")
        return resolved


def eval_program(program: Program) -> tuple[list[str], list[Diagnostic]]:
    interpreter = Interpreter()
    return interpreter.execute(program)
