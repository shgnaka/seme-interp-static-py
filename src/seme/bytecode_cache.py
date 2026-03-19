from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from seme.bytecode import Chunk
from seme.bytecode_serialization import deserialize_chunk, serialize_chunk


@dataclass(frozen=True)
class CacheKey:
    source_hash: str
    compiler_version: str


@dataclass
class BytecodeCache:
    entries: dict[CacheKey, str] = field(default_factory=dict)

    def get_or_build(
        self,
        *,
        source_hash: str,
        compiler_version: str,
        build: Callable[[], Chunk],
    ) -> Chunk:
        key = CacheKey(source_hash=source_hash, compiler_version=compiler_version)
        serialized = self.entries.get(key)
        if serialized is not None:
            return deserialize_chunk(serialized)
        chunk = build()
        self.entries[key] = serialize_chunk(chunk)
        return chunk

    def clear(self) -> None:
        self.entries.clear()


__all__ = [
    "BytecodeCache",
    "CacheKey",
]
