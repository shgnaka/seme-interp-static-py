from __future__ import annotations

from seme.compiler import compile_program
from seme.lexer import lex
from seme.parser import parse
from seme.runtime import SemeBool, SemeInt, SemeString
from seme.typechecker import check_types


def compile_source(source: str):
    tokens, lex_diags = lex(source)
    assert lex_diags == []
    program, parse_diags = parse(tokens)
    assert parse_diags == []
    type_diags = check_types(program)
    assert type_diags == []
    return compile_program(program)


def test_compile_linear_program_with_decls_assign_and_print() -> None:
    chunk = compile_source("let x = 1; x = x + 2; print(x);")

    assert [instruction.opcode.value for instruction in chunk.instructions] == [
        "LOAD_CONST",
        "DEFINE_GLOBAL",
        "POP",
        "LOAD_GLOBAL",
        "LOAD_CONST",
        "ADD",
        "STORE_GLOBAL",
        "POP",
        "LOAD_GLOBAL",
        "PRINT",
        "RETURN",
    ]
    assert chunk.constants[0] == SemeInt(1)
    assert chunk.constants[3] == SemeInt(2)
    assert [const for const in chunk.constants if const == SemeString("x")] == [
        SemeString("x"),
        SemeString("x"),
        SemeString("x"),
        SemeString("x"),
    ]


def test_compile_uninitialized_let_uses_sentinel_opcode() -> None:
    chunk = compile_source("let x: int; print(1);")

    assert chunk.instructions[0].opcode.value == "LOAD_UNINITIALIZED"
    assert chunk.instructions[1].opcode.value == "DEFINE_GLOBAL"
    assert chunk.instructions[-1].opcode.value == "RETURN"


def test_compile_logical_and_uses_short_circuit_jumps() -> None:
    chunk = compile_source("let x = true && false;")

    assert [instruction.opcode.value for instruction in chunk.instructions] == [
        "LOAD_CONST",
        "JUMP_IF_FALSE",
        "POP",
        "LOAD_CONST",
        "JUMP",
        "POP",
        "LOAD_CONST",
        "DEFINE_GLOBAL",
        "POP",
        "RETURN",
    ]
    assert chunk.instructions[1].operands == (5,)
    assert chunk.instructions[4].operands == (7,)
    assert chunk.constants[:3] == [SemeBool(True), SemeBool(False), SemeBool(False)]
    assert chunk.constants[-1] == SemeString("x")


def test_compile_mixed_literal_kinds_to_runtime_value_constants() -> None:
    chunk = compile_source('let n = 1; let ok = false; let msg = "hi";')

    assert chunk.constants == [
        SemeInt(1),
        SemeString("n"),
        SemeBool(False),
        SemeString("ok"),
        SemeString("hi"),
        SemeString("msg"),
    ]


def test_compile_nested_scope_reads_global_but_stores_local_shadow() -> None:
    chunk = compile_source("let x = 1; { let x = 2; print(x); } print(x);")

    assert [instruction.opcode.value for instruction in chunk.instructions] == [
        "LOAD_CONST",
        "DEFINE_GLOBAL",
        "POP",
        "LOAD_CONST",
        "STORE_LOCAL",
        "POP",
        "LOAD_LOCAL",
        "PRINT",
        "POP_N",
        "LOAD_GLOBAL",
        "PRINT",
        "RETURN",
    ]
