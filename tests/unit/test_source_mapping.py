from __future__ import annotations

from seme.bytecode import Chunk, SourceSpan
from seme.source_mapping import DEFAULT_SOURCE_SPAN, source_span_for_incomplete_chunk, source_span_for_offset


def test_source_span_for_offset_returns_first_and_last_known_spans() -> None:
    chunk = Chunk()
    chunk.source_map.extend(
        [
            SourceSpan(line=2, column=4),
            SourceSpan(line=3, column=8),
        ]
    )

    assert source_span_for_offset(chunk, 0) == SourceSpan(line=2, column=4)
    assert source_span_for_offset(chunk, 99) == SourceSpan(line=3, column=8)


def test_source_span_for_offset_uses_default_for_empty_chunks() -> None:
    chunk = Chunk()

    assert source_span_for_offset(chunk, 0) == DEFAULT_SOURCE_SPAN


def test_source_span_for_incomplete_chunk_falls_back_to_safe_resolution() -> None:
    chunk = Chunk()
    chunk.source_map.extend([SourceSpan(line=7, column=11)])

    assert source_span_for_incomplete_chunk(chunk, 3) == SourceSpan(line=7, column=11)
