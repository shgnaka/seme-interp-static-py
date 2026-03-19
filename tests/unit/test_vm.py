from __future__ import annotations

from seme.compiler import compile_program
from seme.bytecode import Chunk, Instruction, OpCode, SourceSpan
from seme.lexer import lex
from seme.parser import parse
from seme.runtime import HeapRef, SemeBool, SemeInt
from seme.typechecker import check_types
from seme.vm import Frame, VirtualMachine, execute_chunk
from seme.vm_metrics import VMMetrics
from seme.vm_trace import TracePhase


def execute_source(source: str):
    tokens, lex_diags = lex(source)
    assert lex_diags == []
    program, parse_diags = parse(tokens)
    assert parse_diags == []
    type_diags = check_types(program)
    assert type_diags == []
    chunk = compile_program(program)
    return execute_chunk(chunk)


def compile_checked_chunk(source: str):
    tokens, lex_diags = lex(source)
    assert lex_diags == []
    program, parse_diags = parse(tokens)
    assert parse_diags == []
    type_diags = check_types(program)
    assert type_diags == []
    return compile_program(program)


def test_vm_executes_basic_program_and_prints_output() -> None:
    stdout_lines, diags = execute_source("let x = 1 + 2 * 3; print(x); print(true);")

    assert diags == []
    assert stdout_lines == ["7", "true"]


def test_vm_executes_control_flow_program() -> None:
    source = """
let sum = 0;
for (let i = 0; i < 3; i = i + 1) {
  if (i < 2) {
    sum = sum + i;
  }
}
print(sum);
""".strip()
    stdout_lines, diags = execute_source(source)

    assert diags == []
    assert stdout_lines == ["1"]


def test_vm_maps_divide_by_zero_to_runtime_001() -> None:
    stdout_lines, diags = execute_source("print(1); let x = 10 / 0; print(x);")

    assert stdout_lines == ["1"]
    assert len(diags) == 1
    assert diags[0].code == "RUNTIME-001"
    assert "division or modulo by zero" in diags[0].message


def test_vm_maps_uninitialized_read_to_runtime_001() -> None:
    stdout_lines, diags = execute_source("let x: int; print(x);")

    assert stdout_lines == []
    assert len(diags) == 1
    assert diags[0].code == "RUNTIME-001"
    assert "uninitialized" in diags[0].message


def test_vm_short_circuits_logical_and_and_or() -> None:
    source = """
print(false && (1 / 0 == 0));
print(true || (1 / 0 == 0));
""".strip()
    stdout_lines, diags = execute_source(source)

    assert diags == []
    assert stdout_lines == ["false", "true"]


def test_vm_runtime_fault_reports_original_source_location() -> None:
    source = """
print(1);
let x = 10 / 0;
print(x);
""".strip()
    stdout_lines, diags = execute_source(source)

    assert stdout_lines == ["1"]
    assert [(d.code, d.line, d.column) for d in diags] == [
        ("RUNTIME-001", 2, 12),
    ]


def test_vm_keeps_runtime_value_objects_in_global_storage_for_top_level_bindings() -> None:
    chunk = compile_checked_chunk("let x = 1 + 2; let ok = x == 3;")
    vm = VirtualMachine(chunk)

    stdout_lines, diags = vm.execute()

    assert stdout_lines == []
    assert diags == []
    assert vm.runtime.globals == {"x": SemeInt(3), "ok": SemeBool(True)}
    assert vm.locals == []


def test_vm_bootstraps_with_a_single_current_frame() -> None:
    chunk = compile_checked_chunk("let x = 1;")
    vm = VirtualMachine(chunk)

    assert len(vm.runtime.frames) == 1
    assert isinstance(vm.runtime.current_frame, Frame)
    assert vm.locals is vm.runtime.current_frame.locals


def test_vm_stores_top_level_bindings_in_global_storage() -> None:
    chunk = compile_checked_chunk("let x = 1 + 2; let ok = x == 3;")
    vm = VirtualMachine(chunk)

    stdout_lines, diags = vm.execute()

    assert stdout_lines == []
    assert diags == []
    assert vm.runtime.globals == {"x": SemeInt(3), "ok": SemeBool(True)}
    assert vm.locals == []


def test_vm_exposes_gc_root_values_for_stack_frames_globals_and_constants() -> None:
    chunk = compile_checked_chunk('let msg = "hi"; print(msg);')
    vm = VirtualMachine(chunk)

    stdout_lines, diags = vm.execute()

    assert stdout_lines == ["hi"]
    assert diags == []
    assert any(isinstance(value, HeapRef) for value in vm.gc_root_values())
    assert vm.runtime.heap.live_object_ids(vm.gc_root_values()) == {1}


def test_vm_keeps_nested_block_shadowing_frame_local_over_global() -> None:
    stdout_lines, diags = execute_source("let x = 1; { let x = 2; print(x); } print(x);")

    assert diags == []
    assert stdout_lines == ["2", "1"]


def test_vm_refuses_to_execute_invalid_bytecode_chunks() -> None:
    chunk = Chunk()
    chunk.instructions.append(Instruction(opcode=OpCode.RETURN))

    stdout_lines, diags = execute_chunk(chunk)

    assert stdout_lines == []
    assert [(d.code, d.message, d.line, d.column) for d in diags] == [
        (
            "BYTECODE-001",
            "bytecode chunk instructions and source map lengths must match",
            1,
            1,
        )
    ]


def test_vm_trace_hook_emits_before_and_after_events_without_changing_output() -> None:
    chunk = compile_checked_chunk("print(1);")
    events = []
    vm = VirtualMachine(chunk, trace_hook=events.append)

    stdout_lines, diags = vm.execute()

    assert stdout_lines == ["1"]
    assert diags == []
    assert len(events) == 6
    assert [event.phase for event in events] == [
        TracePhase.BEFORE,
        TracePhase.AFTER,
        TracePhase.BEFORE,
        TracePhase.AFTER,
        TracePhase.BEFORE,
        TracePhase.AFTER,
    ]
    assert events[0].offset == 0
    assert events[0].span.line == 1
    assert events[0].span.column == 7
    assert events[0].stack_depth == 0
    assert events[-1].instruction.opcode is OpCode.RETURN


def test_vm_trace_hook_emits_error_events_for_runtime_faults() -> None:
    chunk = compile_checked_chunk("let x: int; print(x);")
    events = []
    vm = VirtualMachine(chunk, trace_hook=events.append)

    stdout_lines, diags = vm.execute()

    assert stdout_lines == []
    assert [(d.code, d.line, d.column) for d in diags] == [("RUNTIME-001", 1, 19)]
    assert any(event.phase is TracePhase.ERROR for event in events)


def test_vm_profiling_hook_emits_summary_without_changing_output() -> None:
    chunk = compile_checked_chunk("print(1);")
    summaries: list[VMMetrics] = []
    vm = VirtualMachine(chunk, profiling_hook=summaries.append)

    stdout_lines, diags = vm.execute()

    assert stdout_lines == ["1"]
    assert diags == []
    assert len(summaries) == 1
    metrics = summaries[0]
    assert metrics.instruction_count == 3
    assert metrics.opcode_counts == {"LOAD_CONST": 1, "PRINT": 1, "RETURN": 1}
    assert metrics.max_stack_depth == 1
    assert metrics.max_frame_depth == 1
    assert metrics.wall_time_ns >= 0
