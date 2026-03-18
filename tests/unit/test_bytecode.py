from __future__ import annotations

from seme.bytecode import BYTECODE_INSTRUCTION_SET, Chunk, OpCode, SourceSpan


def test_chunk_emits_instruction_and_source_location() -> None:
    chunk = Chunk()

    const_index = chunk.add_constant(42)
    offset = chunk.emit(OpCode.LOAD_CONST, const_index, span=SourceSpan(line=3, column=5))

    assert const_index == 0
    assert offset == 0
    assert chunk.instructions[0].opcode is OpCode.LOAD_CONST
    assert chunk.instructions[0].operands == (0,)
    assert chunk.span_for_offset(0) == SourceSpan(line=3, column=5)


def test_chunk_preserves_parallel_instruction_and_source_map_lengths() -> None:
    chunk = Chunk()

    chunk.emit(OpCode.LOAD_CONST, 0, span=SourceSpan(line=1, column=1))
    chunk.emit(OpCode.PRINT, span=SourceSpan(line=1, column=10))
    chunk.emit(OpCode.RETURN, span=SourceSpan(line=1, column=17))

    assert len(chunk.instructions) == 3
    assert len(chunk.source_map) == 3


def test_documented_instruction_set_covers_control_flow_and_runtime_ops() -> None:
    assert OpCode.JUMP in BYTECODE_INSTRUCTION_SET
    assert OpCode.JUMP_IF_FALSE in BYTECODE_INSTRUCTION_SET
    assert OpCode.PRINT in BYTECODE_INSTRUCTION_SET
    assert OpCode.RETURN in BYTECODE_INSTRUCTION_SET
