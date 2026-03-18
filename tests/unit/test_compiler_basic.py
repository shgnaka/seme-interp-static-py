from __future__ import annotations

from seme.compiler import compile_program
from seme.lexer import lex
from seme.parser import parse
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
        "STORE_LOCAL",
        "POP",
        "LOAD_LOCAL",
        "LOAD_CONST",
        "ADD",
        "STORE_LOCAL",
        "POP",
        "LOAD_LOCAL",
        "PRINT",
        "RETURN",
    ]
    assert chunk.instructions[1].operands == (0,)
    assert chunk.instructions[6].operands == (0,)
    assert chunk.constants == [1, 2]


def test_compile_uninitialized_let_uses_sentinel_opcode() -> None:
    chunk = compile_source("let x: int; print(1);")

    assert chunk.instructions[0].opcode.value == "LOAD_UNINITIALIZED"
    assert chunk.instructions[1].opcode.value == "STORE_LOCAL"
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
        "STORE_LOCAL",
        "POP",
        "RETURN",
    ]
    assert chunk.instructions[1].operands == (5,)
    assert chunk.instructions[4].operands == (7,)
    assert chunk.constants == [True, False, False]
