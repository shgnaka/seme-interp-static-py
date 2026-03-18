from __future__ import annotations

from seme.runtime import (
    RuntimeValueError,
    SemeBool,
    SemeInt,
    SemeString,
    UNINITIALIZED,
    VOID,
    expect_bool,
    expect_int,
    expect_string,
    format_runtime_value,
    is_bool_value,
    is_int_value,
    is_runtime_value,
    is_string_value,
    is_uninitialized,
    is_void,
    make_runtime_value,
    require_runtime_value,
    runtime_arithmetic,
    runtime_compare,
    runtime_equal,
    runtime_negate,
    runtime_not,
    runtime_raw_value,
    same_runtime_type,
)


def test_make_runtime_value_wraps_language_literals() -> None:
    assert make_runtime_value(7) == SemeInt(7)
    assert make_runtime_value(True) == SemeBool(True)
    assert make_runtime_value("hi") == SemeString("hi")


def test_runtime_formatting_matches_cli_output_conventions() -> None:
    assert format_runtime_value(SemeBool(True)) == "true"
    assert format_runtime_value(SemeBool(False)) == "false"
    assert format_runtime_value(SemeInt(12)) == "12"
    assert format_runtime_value(SemeString("hello")) == "hello"


def test_runtime_type_helpers_distinguish_supported_values() -> None:
    int_value = SemeInt(1)
    bool_value = SemeBool(False)
    string_value = SemeString("x")

    assert is_runtime_value(int_value)
    assert is_runtime_value(bool_value)
    assert is_runtime_value(string_value)
    assert not is_runtime_value(UNINITIALIZED)
    assert not is_runtime_value(VOID)
    assert is_uninitialized(UNINITIALIZED)
    assert not is_uninitialized(int_value)
    assert is_void(VOID)
    assert not is_void(string_value)
    assert is_int_value(int_value)
    assert not is_int_value(bool_value)
    assert is_bool_value(bool_value)
    assert is_string_value(string_value)


def test_runtime_equality_helpers_compare_by_runtime_type() -> None:
    assert same_runtime_type(SemeInt(1), SemeInt(2))
    assert not same_runtime_type(SemeInt(1), SemeBool(True))
    assert runtime_raw_value(SemeString("abc")) == "abc"


def test_runtime_operation_helpers_cover_success_paths() -> None:
    assert expect_bool(SemeBool(True), "bad") is True
    assert expect_int(SemeInt(3), "bad") == 3
    assert expect_string(SemeString("ok"), "bad") == "ok"
    assert runtime_not(SemeBool(False)) == SemeBool(True)
    assert runtime_negate(SemeInt(4)) == SemeInt(-4)
    assert runtime_arithmetic("add", SemeInt(2), SemeInt(5)) == SemeInt(7)
    assert runtime_compare("gte", SemeInt(5), SemeInt(5)) == SemeBool(True)
    assert runtime_equal("eq", SemeString("x"), SemeString("x")) == SemeBool(True)


def test_runtime_operation_helpers_cover_failure_paths() -> None:
    try:
        require_runtime_value(VOID)
    except RuntimeValueError as err:
        assert err.message == "expression does not produce a value"
    else:
        raise AssertionError("expected VOID to be rejected")

    try:
        runtime_arithmetic("div", SemeInt(1), SemeInt(0))
    except RuntimeValueError as err:
        assert err.message == "division or modulo by zero"
    else:
        raise AssertionError("expected zero division to be rejected")

    try:
        runtime_equal("eq", SemeInt(1), SemeBool(True))
    except RuntimeValueError as err:
        assert err.message == "equality operators require matching types"
    else:
        raise AssertionError("expected mixed equality to be rejected")

    try:
        expect_string(SemeInt(1), "string required")
    except RuntimeValueError as err:
        assert err.message == "string required"
    else:
        raise AssertionError("expected bad string conversion to be rejected")
