from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter_ns

from seme.builtins import DEFAULT_BUILTINS
from seme.bytecode import Chunk, Instruction, OpCode, SourceSpan
from seme.bytecode_validator import validate_chunk
from seme.diagnostics import Diagnostic
from seme.runtime import (
    RuntimeHeap,
    RuntimeValue,
    RuntimeValueError,
    SemeString,
    StackValue,
    UNINITIALIZED,
    expect_bool,
    is_runtime_value,
    make_runtime_value,
    require_runtime_value,
    runtime_arithmetic,
    runtime_compare,
    runtime_equal,
    runtime_negate,
    runtime_not,
)
from seme.runtime_faults import (
    RuntimeFault,
    diagnostic_from_runtime_fault,
    diagnostic_from_unexpected_runtime_error,
)
from seme.source_mapping import source_span_for_incomplete_chunk, source_span_for_offset
from seme.vm_metrics import ProfilingHook, VMMetrics
from seme.vm_trace import TraceEvent, TraceHook, TracePhase


@dataclass
class Frame:
    locals: list[StackValue] = field(default_factory=list)
    return_ip: int | None = None


@dataclass
class RuntimeState:
    frames: list[Frame] = field(default_factory=lambda: [Frame()])
    globals: dict[str, StackValue] = field(default_factory=dict)
    heap: RuntimeHeap = field(default_factory=RuntimeHeap)

    @property
    def current_frame(self) -> Frame:
        if not self.frames:
            raise RuntimeError("runtime has no active frame")
        return self.frames[-1]

    def gc_root_values(self) -> list[StackValue]:
        roots: list[StackValue] = []
        for frame in self.frames:
            roots.extend(frame.locals)
        roots.extend(self.globals.values())
        return roots


@dataclass
class VirtualMachine:
    chunk: Chunk
    ip: int = 0
    stack: list[StackValue] = field(default_factory=list)
    runtime: RuntimeState = field(default_factory=RuntimeState)
    stdout_lines: list[str] = field(default_factory=list)
    trace_hook: TraceHook | None = None
    profiling_hook: ProfilingHook | None = None
    metrics: VMMetrics = field(default_factory=VMMetrics)

    @property
    def locals(self) -> list[StackValue]:
        return self.runtime.current_frame.locals

    @property
    def runtime_heap(self) -> RuntimeHeap:
        return self.runtime.heap

    def gc_root_values(self) -> list[StackValue]:
        roots = list(self.stack)
        roots.extend(self.runtime.gc_root_values())
        roots.extend(self.chunk.constants)
        return roots

    def write_stdout_line(self, line: str) -> None:
        self.stdout_lines.append(line)

    def execute(self) -> tuple[list[str], list[Diagnostic]]:
        start_index = len(self.stdout_lines)
        diagnostics: list[Diagnostic] = []
        validation_diags = validate_chunk(self.chunk)
        if validation_diags:
            return self.stdout_lines[start_index:], validation_diags
        self.metrics = VMMetrics()
        started = True
        start_ns = perf_counter_ns()
        try:
            while self.ip < len(self.chunk.instructions):
                instruction = self.chunk.instructions[self.ip]
                offset = self.ip
                self.ip += 1
                span = source_span_for_offset(self.chunk, offset)
                self._record_instruction(instruction.opcode.value)
                self._emit_trace(TracePhase.BEFORE, offset, instruction, span)
                try:
                    self._dispatch(instruction.opcode, instruction.operands)
                except RuntimeFault:
                    self.metrics.runtime_error_count += 1
                    self._emit_trace(TracePhase.ERROR, offset, instruction, span)
                    raise
                self._record_peaks()
                self._emit_trace(TracePhase.AFTER, offset, instruction, span)
            return self.stdout_lines[start_index:], diagnostics
        except RuntimeFault as err:
            diagnostics.append(diagnostic_from_runtime_fault(err))
            return self.stdout_lines[start_index:], diagnostics
        except Exception as exc:  # pragma: no cover
            span = source_span_for_incomplete_chunk(
                self.chunk,
                min(self.ip, len(self.chunk.instructions) - 1),
            ) if self.chunk.instructions else None
            if span is not None and self.ip > 0:
                instruction = self.chunk.instructions[self.ip - 1]
                self._emit_trace(TracePhase.ERROR, self.ip - 1, instruction, span)
            diagnostics.append(
                diagnostic_from_unexpected_runtime_error(
                    exc,
                    line=span.line if span else 1,
                    column=span.column if span else 1,
                )
            )
            return self.stdout_lines[start_index:], diagnostics
        finally:
            if started:
                self.metrics.wall_time_ns = perf_counter_ns() - start_ns
                if self.profiling_hook is not None:
                    self.profiling_hook(self.metrics)

    def _dispatch(self, opcode: OpCode, operands: tuple[int, ...]) -> None:
        current_offset = self.ip - 1

        if opcode == OpCode.LOAD_CONST:
            constant = self.chunk.constants[operands[0]]
            if isinstance(constant, SemeString):
                self.stack.append(make_runtime_value(constant.value, heap=self.runtime.heap))
            else:
                self.stack.append(constant)
            return
        if opcode == OpCode.LOAD_UNINITIALIZED:
            self.stack.append(UNINITIALIZED)
            return
        if opcode == OpCode.LOAD_GLOBAL:
            name = self._global_name(operands[0], current_offset)
            self.stack.append(self._read_global(name, current_offset))
            return
        if opcode == OpCode.DEFINE_GLOBAL:
            name = self._global_name(operands[0], current_offset)
            value = self._peek(current_offset)
            self.runtime.globals[name] = value
            return
        if opcode == OpCode.STORE_GLOBAL:
            name = self._global_name(operands[0], current_offset)
            value = self._peek(current_offset)
            self._write_global(name, value, current_offset)
            return
        if opcode == OpCode.LOAD_LOCAL:
            slot = operands[0]
            value = self._read_local(slot, current_offset)
            self.stack.append(value)
            return
        if opcode == OpCode.STORE_LOCAL:
            slot = operands[0]
            value = self._peek(current_offset)
            self._write_local(slot, value, current_offset)
            return
        if opcode == OpCode.POP:
            self._pop(current_offset)
            return
        if opcode == OpCode.POP_N:
            count = operands[0]
            frame = self.runtime.current_frame
            if count > len(frame.locals):
                self._fault("local cleanup underflow", current_offset)
            del frame.locals[-count:]
            return
        if opcode in (OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, OpCode.MOD):
            right = self._pop_runtime(current_offset)
            left = self._pop_runtime(current_offset)
            try:
                if opcode == OpCode.ADD:
                    self.stack.append(runtime_arithmetic("add", left, right))
                    return
                if opcode == OpCode.SUB:
                    self.stack.append(runtime_arithmetic("sub", left, right))
                    return
                if opcode == OpCode.MUL:
                    self.stack.append(runtime_arithmetic("mul", left, right))
                    return
                if opcode == OpCode.DIV:
                    self.stack.append(runtime_arithmetic("div", left, right))
                    return
                self.stack.append(runtime_arithmetic("mod", left, right))
            except RuntimeValueError as err:
                self._fault(err.message, current_offset)
            return
        if opcode == OpCode.NEGATE:
            operand = self._pop_runtime(current_offset)
            try:
                self.stack.append(runtime_negate(operand))
            except RuntimeValueError as err:
                self._fault(err.message, current_offset)
            return
        if opcode == OpCode.NOT:
            operand = self._pop_runtime(current_offset)
            try:
                self.stack.append(runtime_not(operand))
            except RuntimeValueError as err:
                self._fault(err.message, current_offset)
            return
        if opcode in (OpCode.EQUAL, OpCode.NOT_EQUAL):
            right = self._pop_runtime(current_offset)
            left = self._pop_runtime(current_offset)
            try:
                self.stack.append(
                    runtime_equal(
                        "eq" if opcode == OpCode.EQUAL else "neq",
                        left,
                        right,
                        heap=self.runtime.heap,
                    )
                )
            except RuntimeValueError as err:
                self._fault(err.message, current_offset)
            return
        if opcode in (OpCode.LESS, OpCode.LESS_EQUAL, OpCode.GREATER, OpCode.GREATER_EQUAL):
            right = self._pop_runtime(current_offset)
            left = self._pop_runtime(current_offset)
            try:
                if opcode == OpCode.LESS:
                    self.stack.append(runtime_compare("lt", left, right))
                elif opcode == OpCode.LESS_EQUAL:
                    self.stack.append(runtime_compare("lte", left, right))
                elif opcode == OpCode.GREATER:
                    self.stack.append(runtime_compare("gt", left, right))
                else:
                    self.stack.append(runtime_compare("gte", left, right))
            except RuntimeValueError as err:
                self._fault(err.message, current_offset)
            return
        if opcode == OpCode.JUMP:
            self.ip = operands[0]
            return
        if opcode == OpCode.JUMP_IF_FALSE:
            value = self._peek_runtime(current_offset)
            try:
                condition = expect_bool(value, "condition must evaluate to bool")
            except RuntimeValueError as err:
                self._fault(err.message, current_offset)
            if not condition:
                self.ip = operands[0]
            return
        if opcode == OpCode.PRINT:
            value = self._pop_runtime(current_offset)
            try:
                DEFAULT_BUILTINS.invoke("print", [value], self)
            except RuntimeValueError as err:
                self._fault(err.message, current_offset)
            return
        if opcode == OpCode.RETURN:
            self.ip = len(self.chunk.instructions)
            return

        self._fault(f"unsupported opcode {opcode}", current_offset)

    def _read_local(self, slot: int, offset: int) -> RuntimeValue:
        frame = self.runtime.current_frame
        if slot >= len(frame.locals):
            self._fault(f"invalid local slot {slot}", offset)
        value = frame.locals[slot]
        if value is UNINITIALIZED:
            self._fault(f"variable in slot {slot} is uninitialized", offset)
        if not is_runtime_value(value):
            self._fault(f"invalid runtime value in slot {slot}", offset)
        return value

    def _read_global(self, name: str, offset: int) -> RuntimeValue:
        if name not in self.runtime.globals:
            self._fault(f"undeclared variable '{name}'", offset)
        value = self.runtime.globals[name]
        if value is UNINITIALIZED:
            self._fault(f"variable '{name}' is uninitialized", offset)
        if not is_runtime_value(value):
            self._fault(f"invalid runtime value in global '{name}'", offset)
        return value

    def _write_local(self, slot: int, value: StackValue, offset: int) -> None:
        frame = self.runtime.current_frame
        while len(frame.locals) <= slot:
            frame.locals.append(UNINITIALIZED)
        frame.locals[slot] = value

    def _write_global(self, name: str, value: StackValue, offset: int) -> None:
        if name not in self.runtime.globals:
            self._fault(f"undeclared variable '{name}'", offset)
        self.runtime.globals[name] = value

    def _peek(self, offset: int) -> StackValue:
        if not self.stack:
            self._fault("stack underflow", offset)
        return self.stack[-1]

    def _peek_runtime(self, offset: int) -> RuntimeValue:
        value = self._peek(offset)
        try:
            return require_runtime_value(value)
        except RuntimeValueError as err:
            self._fault(err.message, offset)

    def _pop(self, offset: int) -> StackValue:
        if not self.stack:
            self._fault("stack underflow", offset)
        return self.stack.pop()

    def _pop_runtime(self, offset: int) -> RuntimeValue:
        value = self._pop(offset)
        try:
            return require_runtime_value(value)
        except RuntimeValueError as err:
            self._fault(err.message, offset)

    def _fault(self, message: str, offset: int) -> None:
        span = source_span_for_offset(self.chunk, offset)
        raise RuntimeFault(message=message, line=span.line, column=span.column)

    def _global_name(self, const_index: int, offset: int) -> str:
        if const_index >= len(self.chunk.constants):
            self._fault(f"invalid global name constant {const_index}", offset)
        value = self.chunk.constants[const_index]
        if not isinstance(value, SemeString):
            self._fault(f"invalid global name constant {const_index}", offset)
        return value.value

    def _emit_trace(
        self,
        phase: TracePhase,
        offset: int,
        instruction: Instruction,
        span: SourceSpan,
    ) -> None:
        if self.trace_hook is None:
            return
        event = TraceEvent(
            phase=phase,
            offset=offset,
            instruction=instruction,
            span=span,
            stack_depth=len(self.stack),
            frame_depth=len(self.runtime.frames),
        )
        self.trace_hook(event)

    def _record_instruction(self, opcode_name: str) -> None:
        self.metrics.instruction_count += 1
        self.metrics.opcode_counts[opcode_name] = self.metrics.opcode_counts.get(opcode_name, 0) + 1
        self._record_peaks()

    def _record_peaks(self) -> None:
        self.metrics.max_stack_depth = max(self.metrics.max_stack_depth, len(self.stack))
        self.metrics.max_frame_depth = max(self.metrics.max_frame_depth, len(self.runtime.frames))


def execute_chunk(chunk: Chunk) -> tuple[list[str], list[Diagnostic]]:
    return VirtualMachine(chunk).execute()


__all__ = [
    "Frame",
    "RuntimeState",
    "VirtualMachine",
    "execute_chunk",
]
