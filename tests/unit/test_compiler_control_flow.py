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


def test_compile_if_else_uses_branch_and_join_jumps() -> None:
    chunk = compile_source("let x = 1; if (x < 2) { print(x); } else { print(2); }")

    assert [instruction.opcode.value for instruction in chunk.instructions] == [
        "LOAD_CONST",
        "STORE_LOCAL",
        "POP",
        "LOAD_LOCAL",
        "LOAD_CONST",
        "LESS",
        "JUMP_IF_FALSE",
        "POP",
        "LOAD_LOCAL",
        "PRINT",
        "JUMP",
        "POP",
        "LOAD_CONST",
        "PRINT",
        "RETURN",
    ]
    assert chunk.instructions[6].operands == (11,)
    assert chunk.instructions[10].operands == (14,)


def test_compile_while_loop_back_edges_to_condition() -> None:
    chunk = compile_source("let x = 0; while (x < 2) { x = x + 1; }")

    assert [instruction.opcode.value for instruction in chunk.instructions] == [
        "LOAD_CONST",
        "STORE_LOCAL",
        "POP",
        "LOAD_LOCAL",
        "LOAD_CONST",
        "LESS",
        "JUMP_IF_FALSE",
        "POP",
        "LOAD_LOCAL",
        "LOAD_CONST",
        "ADD",
        "STORE_LOCAL",
        "POP",
        "JUMP",
        "POP",
        "RETURN",
    ]
    assert chunk.instructions[6].operands == (14,)
    assert chunk.instructions[13].operands == (3,)


def test_compile_for_preserves_init_condition_body_update_order() -> None:
    chunk = compile_source("for (let i = 0; i < 2; i = i + 1) { print(i); }")

    assert [instruction.opcode.value for instruction in chunk.instructions] == [
        "LOAD_CONST",
        "STORE_LOCAL",
        "POP",
        "LOAD_LOCAL",
        "LOAD_CONST",
        "LESS",
        "JUMP_IF_FALSE",
        "POP",
        "LOAD_LOCAL",
        "PRINT",
        "LOAD_LOCAL",
        "LOAD_CONST",
        "ADD",
        "STORE_LOCAL",
        "POP",
        "JUMP",
        "POP",
        "POP_N",
        "RETURN",
    ]
    assert chunk.instructions[6].operands == (16,)
    assert chunk.instructions[15].operands == (3,)


def test_compile_nested_blocks_cleanup_only_inner_slots() -> None:
    chunk = compile_source("let x = 1; { let y = 2; print(y); } print(x);")

    assert [instruction.opcode.value for instruction in chunk.instructions] == [
        "LOAD_CONST",
        "STORE_LOCAL",
        "POP",
        "LOAD_CONST",
        "STORE_LOCAL",
        "POP",
        "LOAD_LOCAL",
        "PRINT",
        "POP_N",
        "LOAD_LOCAL",
        "PRINT",
        "RETURN",
    ]
    assert chunk.instructions[1].operands == (0,)
    assert chunk.instructions[4].operands == (1,)
