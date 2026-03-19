from __future__ import annotations

from seme.bytecode import BYTECODE_INSTRUCTION_SET, Chunk, OpCode, SourceSpan
from seme.compiler import BytecodeBuilder
from seme.runtime import SemeBool, SemeInt, SemeString


def test_chunk_emits_instruction_and_source_location() -> None:
    chunk = Chunk()

    const_index = chunk.add_constant(SemeInt(42))
    offset = chunk.emit(OpCode.LOAD_CONST, const_index, span=SourceSpan(line=3, column=5))

    assert const_index == 0
    assert offset == 0
    assert chunk.instructions[0].opcode is OpCode.LOAD_CONST
    assert chunk.instructions[0].operands == (0,)
    assert chunk.constants == [SemeInt(42)]
    assert chunk.span_for_offset(0) == SourceSpan(line=3, column=5)


def test_chunk_preserves_parallel_instruction_and_source_map_lengths() -> None:
    chunk = Chunk()

    chunk.emit(OpCode.LOAD_CONST, 0, span=SourceSpan(line=1, column=1))
    chunk.emit(OpCode.PRINT, span=SourceSpan(line=1, column=10))
    chunk.emit(OpCode.RETURN, span=SourceSpan(line=1, column=17))

    assert len(chunk.instructions) == 3
    assert len(chunk.source_map) == 3


def test_documented_instruction_set_covers_control_flow_and_runtime_ops() -> None:
    assert OpCode.LOAD_GLOBAL in BYTECODE_INSTRUCTION_SET
    assert OpCode.DEFINE_GLOBAL in BYTECODE_INSTRUCTION_SET
    assert OpCode.STORE_GLOBAL in BYTECODE_INSTRUCTION_SET
    assert OpCode.JUMP in BYTECODE_INSTRUCTION_SET
    assert OpCode.JUMP_IF_FALSE in BYTECODE_INSTRUCTION_SET
    assert OpCode.PRINT in BYTECODE_INSTRUCTION_SET
    assert OpCode.RETURN in BYTECODE_INSTRUCTION_SET


def test_builder_wraps_literal_constants_as_runtime_values() -> None:
    builder = BytecodeBuilder()

    int_index = builder.add_literal_constant(7)
    bool_index = builder.add_literal_constant(True)
    string_index = builder.add_literal_constant("hello")

    assert (int_index, bool_index, string_index) == (0, 1, 2)
    assert builder.chunk.constants == [
        SemeInt(7),
        SemeBool(True),
        SemeString("hello"),
    ]
