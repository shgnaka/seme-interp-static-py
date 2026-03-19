from __future__ import annotations

from seme.bytecode import Chunk, OpCode, SourceSpan
from seme.bytecode_cache import BytecodeCache
from seme.runtime import SemeInt


def test_bytecode_cache_reuses_serialized_chunk_for_same_source_and_version() -> None:
    cache = BytecodeCache()
    build_calls = {"count": 0}

    def build() -> Chunk:
        build_calls["count"] += 1
        chunk = Chunk()
        chunk.add_constant(SemeInt(1))
        chunk.emit(OpCode.RETURN, span=SourceSpan(line=1, column=1))
        return chunk

    first = cache.get_or_build(source_hash="abc", compiler_version="v1", build=build)
    second = cache.get_or_build(source_hash="abc", compiler_version="v1", build=build)

    assert build_calls["count"] == 1
    assert first == second
    assert first is not second


def test_bytecode_cache_invalidates_on_version_change() -> None:
    cache = BytecodeCache()
    build_calls = {"count": 0}

    def build() -> Chunk:
        build_calls["count"] += 1
        chunk = Chunk()
        chunk.emit(OpCode.RETURN, span=SourceSpan(line=1, column=1))
        return chunk

    cache.get_or_build(source_hash="abc", compiler_version="v1", build=build)
    cache.get_or_build(source_hash="abc", compiler_version="v2", build=build)

    assert build_calls["count"] == 2
