from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SemeInt:
    value: int


@dataclass(frozen=True)
class SemeBool:
    value: bool


@dataclass(frozen=True)
class SemeString:
    value: str


@dataclass(frozen=True)
class RuntimeSentinel:
    name: str


@dataclass(frozen=True)
class RuntimeValueError(Exception):
    message: str


RuntimeValue = SemeInt | SemeBool | SemeString
StackValue = RuntimeValue | RuntimeSentinel

UNINITIALIZED = RuntimeSentinel("uninitialized")
VOID = RuntimeSentinel("void")


def make_runtime_value(value: int | bool | str) -> RuntimeValue:
    if isinstance(value, bool):
        return SemeBool(value)
    if isinstance(value, int):
        return SemeInt(value)
    return SemeString(value)


def is_runtime_value(value: object) -> bool:
    return isinstance(value, (SemeInt, SemeBool, SemeString))


def is_uninitialized(value: object) -> bool:
    return value is UNINITIALIZED


def is_void(value: object) -> bool:
    return value is VOID


def is_int_value(value: RuntimeValue) -> bool:
    return isinstance(value, SemeInt)


def is_bool_value(value: RuntimeValue) -> bool:
    return isinstance(value, SemeBool)


def is_string_value(value: RuntimeValue) -> bool:
    return isinstance(value, SemeString)


def same_runtime_type(left: RuntimeValue, right: RuntimeValue) -> bool:
    return type(left) is type(right)


def format_runtime_value(value: RuntimeValue) -> str:
    if isinstance(value, SemeBool):
        return "true" if value.value else "false"
    return str(value.value)


def runtime_raw_value(value: RuntimeValue) -> int | bool | str:
    return value.value


def require_runtime_value(value: StackValue) -> RuntimeValue:
    if value is VOID:
        raise RuntimeValueError("expression does not produce a value")
    if value is UNINITIALIZED:
        raise RuntimeValueError("uninitialized value used in expression")
    if not is_runtime_value(value):
        raise RuntimeValueError("invalid runtime value")
    return value


def expect_bool(value: RuntimeValue, message: str) -> bool:
    if not is_bool_value(value):
        raise RuntimeValueError(message)
    return value.value


def expect_int(value: RuntimeValue, message: str) -> int:
    if not is_int_value(value):
        raise RuntimeValueError(message)
    return value.value


def expect_string(value: RuntimeValue, message: str) -> str:
    if not is_string_value(value):
        raise RuntimeValueError(message)
    return value.value


def runtime_negate(operand: RuntimeValue) -> SemeInt:
    return SemeInt(-expect_int(operand, "unary '-' requires int operand"))


def runtime_not(operand: RuntimeValue) -> SemeBool:
    return SemeBool(not expect_bool(operand, "operator '!' requires bool operand"))


def runtime_arithmetic(
    operator: Literal["add", "sub", "mul", "div", "mod"],
    left: RuntimeValue,
    right: RuntimeValue,
) -> SemeInt:
    left_raw = expect_int(left, "arithmetic operators require int operands")
    right_raw = expect_int(right, "arithmetic operators require int operands")
    if operator == "add":
        return SemeInt(left_raw + right_raw)
    if operator == "sub":
        return SemeInt(left_raw - right_raw)
    if operator == "mul":
        return SemeInt(left_raw * right_raw)
    if right_raw == 0:
        raise RuntimeValueError("division or modulo by zero")
    if operator == "div":
        return SemeInt(left_raw // right_raw)
    return SemeInt(left_raw % right_raw)


def runtime_compare(
    operator: Literal["lt", "lte", "gt", "gte"],
    left: RuntimeValue,
    right: RuntimeValue,
) -> SemeBool:
    left_raw = expect_int(left, "comparison operators require int operands")
    right_raw = expect_int(right, "comparison operators require int operands")
    if operator == "lt":
        return SemeBool(left_raw < right_raw)
    if operator == "lte":
        return SemeBool(left_raw <= right_raw)
    if operator == "gt":
        return SemeBool(left_raw > right_raw)
    return SemeBool(left_raw >= right_raw)


def runtime_equal(operator: Literal["eq", "neq"], left: RuntimeValue, right: RuntimeValue) -> SemeBool:
    if not same_runtime_type(left, right):
        raise RuntimeValueError("equality operators require matching types")
    result = runtime_raw_value(left) == runtime_raw_value(right)
    if operator == "neq":
        result = not result
    return SemeBool(result)


__all__ = [
    "RuntimeSentinel",
    "RuntimeValueError",
    "RuntimeValue",
    "SemeBool",
    "SemeInt",
    "SemeString",
    "StackValue",
    "UNINITIALIZED",
    "VOID",
    "expect_bool",
    "expect_int",
    "expect_string",
    "format_runtime_value",
    "is_bool_value",
    "is_int_value",
    "is_runtime_value",
    "is_string_value",
    "is_uninitialized",
    "is_void",
    "make_runtime_value",
    "require_runtime_value",
    "runtime_arithmetic",
    "runtime_compare",
    "runtime_equal",
    "runtime_negate",
    "runtime_not",
    "runtime_raw_value",
    "same_runtime_type",
]
