from __future__ import annotations

from seme.bytecode import Chunk, OpCode, SourceSpan
from seme.bytecode_peephole import optimize_chunk
from seme.compiler import compile_program
from seme.lexer import lex
from seme.parser import parse
from seme.runtime import SemeInt
from seme.typechecker import check_types


def compile_source(source: str, *, optimize: bool = True) -> Chunk:
    tokens, lex_diags = lex(source)
    assert lex_diags == []
    program, parse_diags = parse(tokens)
    assert parse_diags == []
    type_diags = check_types(program)
    assert type_diags == []
    return compile_program(program, optimize=optimize)


def test_optimize_chunk_folds_literals_and_removes_dead_stack_churn() -> None:
    chunk = Chunk()
    left = chunk.add_constant(SemeInt(1))
    right = chunk.add_constant(SemeInt(2))

    chunk.emit(OpCode.LOAD_CONST, left, span=SourceSpan(1, 1))
    chunk.emit(OpCode.LOAD_CONST, right, span=SourceSpan(1, 5))
    chunk.emit(OpCode.ADD, span=SourceSpan(1, 7))
    chunk.emit(OpCode.POP, span=SourceSpan(1, 8))
    chunk.emit(OpCode.RETURN, span=SourceSpan(1, 9))

    optimized = optimize_chunk(chunk)

    assert [instruction.opcode.value for instruction in optimized.instructions] == ["RETURN"]
    assert optimized.constants == [SemeInt(1), SemeInt(2), SemeInt(3)]
    assert optimized.span_for_offset(0) == SourceSpan(1, 9)


def test_compile_program_can_disable_peephole_optimization() -> None:
    raw_chunk = compile_source("1 + 2;", optimize=False)

    assert [instruction.opcode.value for instruction in raw_chunk.instructions] == [
        "LOAD_CONST",
        "LOAD_CONST",
        "ADD",
        "POP",
        "RETURN",
    ]


def test_compile_program_peephole_folds_nested_constant_expressions() -> None:
    chunk = compile_source("print(1 + 2 * 3);")

    assert [instruction.opcode.value for instruction in chunk.instructions] == [
        "LOAD_CONST",
        "PRINT",
        "RETURN",
    ]
    assert chunk.constants[-1] == SemeInt(7)
