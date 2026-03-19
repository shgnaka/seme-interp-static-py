from __future__ import annotations

from seme.bytecode import Chunk, OpCode, SourceSpan
from seme.bytecode_serialization import deserialize_chunk, serialize_chunk
from seme.runtime import HeapRef, SemeBool, SemeInt, SemeString


def test_chunk_serialization_round_trips_instructions_constants_and_source_map() -> None:
    chunk = Chunk()
    chunk.add_constant(SemeInt(7))
    chunk.add_constant(SemeBool(True))
    chunk.add_constant(SemeString("hi"))
    chunk.add_constant(HeapRef(object_id=5, kind="string"))
    chunk.emit(OpCode.LOAD_CONST, 0, span=SourceSpan(line=2, column=3))
    chunk.emit(OpCode.PRINT, span=SourceSpan(line=2, column=9))
    chunk.emit(OpCode.RETURN, span=SourceSpan(line=2, column=17))

    restored = deserialize_chunk(serialize_chunk(chunk))

    assert restored == chunk


def test_serialized_chunk_is_json_stable_enough_for_cache_use() -> None:
    chunk = Chunk()
    chunk.add_constant(SemeString("hello"))
    chunk.emit(OpCode.RETURN, span=SourceSpan(line=1, column=1))

    serialized = serialize_chunk(chunk)

    assert '"instructions":[{"opcode":"RETURN","operands":[]}]' in serialized
    assert '"kind":"string"' in serialized
