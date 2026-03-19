from __future__ import annotations

from seme.bytecode import Chunk, SourceSpan


DEFAULT_SOURCE_SPAN = SourceSpan(line=1, column=1)


def source_span_for_offset(chunk: Chunk, offset: int) -> SourceSpan:
    if not chunk.source_map:
        return DEFAULT_SOURCE_SPAN
    if offset < 0:
        return chunk.source_map[0]
    if offset >= len(chunk.source_map):
        return chunk.source_map[-1]
    return chunk.source_map[offset]


def source_span_for_incomplete_chunk(chunk: Chunk, offset: int) -> SourceSpan:
    try:
        return chunk.span_for_offset(offset)
    except IndexError:
        return source_span_for_offset(chunk, offset)


__all__ = [
    "DEFAULT_SOURCE_SPAN",
    "source_span_for_incomplete_chunk",
    "source_span_for_offset",
]
