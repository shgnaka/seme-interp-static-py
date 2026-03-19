from __future__ import annotations

from seme.bytecode import Chunk, OpCode, SourceSpan
from seme.bytecode_disassembler import disassemble_chunk
from seme.runtime import SemeBool, SemeInt, SemeString


def test_disassemble_chunk_renders_constants_and_source_locations() -> None:
    chunk = Chunk()
    int_index = chunk.add_constant(SemeInt(7))
    bool_index = chunk.add_constant(SemeBool(True))
    string_index = chunk.add_constant(SemeString("hi"))

    chunk.emit(OpCode.LOAD_CONST, int_index, span=SourceSpan(line=2, column=3))
    chunk.emit(OpCode.LOAD_CONST, bool_index, span=SourceSpan(line=2, column=10))
    chunk.emit(OpCode.LOAD_GLOBAL, string_index, span=SourceSpan(line=2, column=20))
    chunk.emit(OpCode.RETURN, span=SourceSpan(line=2, column=30))

    assert disassemble_chunk(chunk) == [
        "0000 LOAD_CONST 0 (7) ; 2:3",
        "0001 LOAD_CONST 1 (true) ; 2:10",
        "0002 LOAD_GLOBAL 2 (hi) ; 2:20",
        "0003 RETURN ; 2:30",
    ]


def test_disassemble_chunk_falls_back_to_raw_operand_for_incomplete_chunks() -> None:
    chunk = Chunk()
    chunk.emit(OpCode.LOAD_CONST, 99, span=SourceSpan(line=1, column=1))
    chunk.emit(OpCode.RETURN, span=SourceSpan(line=1, column=2))

    assert disassemble_chunk(chunk) == [
        "0000 LOAD_CONST 99 ; 1:1",
        "0001 RETURN ; 1:2",
    ]
