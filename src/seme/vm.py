from __future__ import annotations

from dataclasses import dataclass, field

from seme.bytecode import Chunk, OpCode
from seme.diagnostics import Diagnostic
from seme.runtime import (
    RuntimeValue,
    RuntimeValueError,
    SemeBool,
    SemeInt,
    SemeString,
    StackValue,
    UNINITIALIZED,
    expect_bool,
    format_runtime_value,
    require_runtime_value,
    runtime_arithmetic,
    runtime_compare,
    runtime_equal,
    runtime_negate,
    runtime_not,
)


@dataclass(frozen=True)
class RuntimeFault(Exception):
    message: str
    offset: int


@dataclass
class VirtualMachine:
    chunk: Chunk
    ip: int = 0
    stack: list[StackValue] = field(default_factory=list)
    locals: list[StackValue] = field(default_factory=list)
    stdout_lines: list[str] = field(default_factory=list)

    def execute(self) -> tuple[list[str], list[Diagnostic]]:
        start_index = len(self.stdout_lines)
        diagnostics: list[Diagnostic] = []
        try:
            while self.ip < len(self.chunk.instructions):
                instruction = self.chunk.instructions[self.ip]
                self.ip += 1
                self._dispatch(instruction.opcode, instruction.operands)
            return self.stdout_lines[start_index:], diagnostics
        except RuntimeFault as err:
            span = self.chunk.span_for_offset(err.offset)
            diagnostics.append(
                Diagnostic(
                    code="RUNTIME-001",
                    message=f"Runtime error: {err.message}",
                    line=span.line,
                    column=span.column,
                )
            )
            return self.stdout_lines[start_index:], diagnostics
        except Exception as exc:  # pragma: no cover
            span = self.chunk.span_for_offset(min(self.ip, len(self.chunk.instructions) - 1)) if self.chunk.instructions else None
            diagnostics.append(
                Diagnostic(
                    code="RUNTIME-001",
                    message=f"Runtime error: {exc}",
                    line=span.line if span else 1,
                    column=span.column if span else 1,
                )
            )
            return self.stdout_lines[start_index:], diagnostics

    def _dispatch(self, opcode: OpCode, operands: tuple[int, ...]) -> None:
        current_offset = self.ip - 1

        if opcode == OpCode.LOAD_CONST:
            self.stack.append(self.chunk.constants[operands[0]])
            return
        if opcode == OpCode.LOAD_UNINITIALIZED:
            self.stack.append(UNINITIALIZED)
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
            if count > len(self.locals):
                self._fault("local cleanup underflow", current_offset)
            del self.locals[-count:]
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
                self.stack.append(runtime_equal("eq" if opcode == OpCode.EQUAL else "neq", left, right))
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
            self.stdout_lines.append(format_runtime_value(value))
            return
        if opcode == OpCode.RETURN:
            self.ip = len(self.chunk.instructions)
            return

        self._fault(f"unsupported opcode {opcode}", current_offset)

    def _read_local(self, slot: int, offset: int) -> RuntimeValue:
        if slot >= len(self.locals):
            self._fault(f"invalid local slot {slot}", offset)
        value = self.locals[slot]
        if value is UNINITIALIZED:
            self._fault(f"variable in slot {slot} is uninitialized", offset)
        if not isinstance(value, (SemeInt, SemeBool, SemeString)):
            self._fault(f"invalid runtime value in slot {slot}", offset)
        return value

    def _write_local(self, slot: int, value: StackValue, offset: int) -> None:
        while len(self.locals) <= slot:
            self.locals.append(UNINITIALIZED)
        self.locals[slot] = value

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
        raise RuntimeFault(message=message, offset=offset)


def execute_chunk(chunk: Chunk) -> tuple[list[str], list[Diagnostic]]:
    return VirtualMachine(chunk).execute()


__all__ = [
    "VirtualMachine",
    "execute_chunk",
]
