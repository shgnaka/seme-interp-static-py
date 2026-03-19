from __future__ import annotations

from hashlib import sha256

from seme.bytecode_cache import BytecodeCache
from seme.bytecode_serialization import deserialize_chunk, serialize_chunk
from seme.bytecode_validator import validate_chunk
from seme.compiler import compile_program
from seme.lexer import lex
from seme.parser import parse
from seme.runtime import SemeString
from seme.typechecker import check_types
from seme.vm import VirtualMachine
from seme.vm_metrics import VMMetrics
from seme.vm_trace import TracePhase


def compile_checked_chunk(source: str):
    tokens, lex_diags = lex(source)
    assert lex_diags == []
    program, parse_diags = parse(tokens)
    assert parse_diags == []
    type_diags = check_types(program)
    assert type_diags == []
    return compile_program(program)


def test_runtime_tooling_round_trip_validation_trace_and_metrics() -> None:
    chunk = compile_checked_chunk('let msg = "hi"; print(msg);')
    restored = deserialize_chunk(serialize_chunk(chunk))
    trace_events = []
    metrics: list[VMMetrics] = []
    vm = VirtualMachine(restored, trace_hook=trace_events.append, profiling_hook=metrics.append)

    validation_diags = validate_chunk(restored)
    stdout_lines, runtime_diags = vm.execute()

    assert validation_diags == []
    assert stdout_lines == ["hi"]
    assert runtime_diags == []
    assert [event.phase for event in trace_events[:2]] == [TracePhase.BEFORE, TracePhase.AFTER]
    assert any(event.instruction.opcode.value == "PRINT" for event in trace_events)
    assert len(metrics) == 1
    assert metrics[0].instruction_count >= 3
    assert metrics[0].opcode_counts["PRINT"] == 1


def test_runtime_tooling_cache_uses_source_hash_and_returns_fresh_chunks() -> None:
    source = 'print("hi");'
    cache = BytecodeCache()
    build_calls = {"count": 0}

    def build():
        build_calls["count"] += 1
        return compile_checked_chunk(source)

    source_hash = sha256(source.encode("utf-8")).hexdigest()
    first = cache.get_or_build(source_hash=source_hash, compiler_version="v1", build=build)
    first.constants.append(SemeString("mutated"))
    second = cache.get_or_build(source_hash=source_hash, compiler_version="v1", build=build)

    assert build_calls["count"] == 1
    assert second.constants == [SemeString("hi")]
    assert len(first.constants) == 2
