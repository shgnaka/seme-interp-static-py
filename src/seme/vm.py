from __future__ import annotations

from dataclasses import dataclass, field

from seme.bytecode import Chunk, OpCode
from seme.diagnostics import Diagnostic

RuntimeValue = int | bool | str
StackValue = RuntimeValue | object
_UNINITIALIZED = object()


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
            self.stack.append(_UNINITIALIZED)
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
            if not self._is_int(left) or not self._is_int(right):
                self._fault("arithmetic operators require int operands", current_offset)
            if opcode == OpCode.ADD:
                self.stack.append(left + right)
                return
            if opcode == OpCode.SUB:
                self.stack.append(left - right)
                return
            if opcode == OpCode.MUL:
                self.stack.append(left * right)
                return
            if right == 0:
                self._fault("division or modulo by zero", current_offset)
            if opcode == OpCode.DIV:
                self.stack.append(left // right)
                return
            self.stack.append(left % right)
            return
        if opcode == OpCode.NEGATE:
            operand = self._pop_runtime(current_offset)
            if not self._is_int(operand):
                self._fault("unary '-' requires int operand", current_offset)
            self.stack.append(-operand)
            return
        if opcode == OpCode.NOT:
            operand = self._pop_runtime(current_offset)
            if not isinstance(operand, bool):
                self._fault("operator '!' requires bool operand", current_offset)
            self.stack.append(not operand)
            return
        if opcode in (OpCode.EQUAL, OpCode.NOT_EQUAL):
            right = self._pop_runtime(current_offset)
            left = self._pop_runtime(current_offset)
            if type(left) is not type(right):
                self._fault("equality operators require matching types", current_offset)
            self.stack.append(left == right if opcode == OpCode.EQUAL else left != right)
            return
        if opcode in (OpCode.LESS, OpCode.LESS_EQUAL, OpCode.GREATER, OpCode.GREATER_EQUAL):
            right = self._pop_runtime(current_offset)
            left = self._pop_runtime(current_offset)
            if not self._is_int(left) or not self._is_int(right):
                self._fault("comparison operators require int operands", current_offset)
            if opcode == OpCode.LESS:
                self.stack.append(left < right)
            elif opcode == OpCode.LESS_EQUAL:
                self.stack.append(left <= right)
            elif opcode == OpCode.GREATER:
                self.stack.append(left > right)
            else:
                self.stack.append(left >= right)
            return
        if opcode == OpCode.JUMP:
            self.ip = operands[0]
            return
        if opcode == OpCode.JUMP_IF_FALSE:
            value = self._peek_runtime(current_offset)
            if not isinstance(value, bool):
                self._fault("condition must evaluate to bool", current_offset)
            if not value:
                self.ip = operands[0]
            return
        if opcode == OpCode.PRINT:
            value = self._pop_runtime(current_offset)
            self.stdout_lines.append(self._format_value(value))
            return
        if opcode == OpCode.RETURN:
            self.ip = len(self.chunk.instructions)
            return

        self._fault(f"unsupported opcode {opcode}", current_offset)

    def _read_local(self, slot: int, offset: int) -> RuntimeValue:
        if slot >= len(self.locals):
            self._fault(f"invalid local slot {slot}", offset)
        value = self.locals[slot]
        if value is _UNINITIALIZED:
            self._fault(f"variable in slot {slot} is uninitialized", offset)
        if not isinstance(value, (int, bool, str)):
            self._fault(f"invalid runtime value in slot {slot}", offset)
        return value

    def _write_local(self, slot: int, value: StackValue, offset: int) -> None:
        while len(self.locals) <= slot:
            self.locals.append(_UNINITIALIZED)
        self.locals[slot] = value

    def _peek(self, offset: int) -> StackValue:
        if not self.stack:
            self._fault("stack underflow", offset)
        return self.stack[-1]

    def _peek_runtime(self, offset: int) -> RuntimeValue:
        value = self._peek(offset)
        if value is _UNINITIALIZED:
            self._fault("uninitialized value used in expression", offset)
        if not isinstance(value, (int, bool, str)):
            self._fault("invalid runtime value on stack", offset)
        return value

    def _pop(self, offset: int) -> StackValue:
        if not self.stack:
            self._fault("stack underflow", offset)
        return self.stack.pop()

    def _pop_runtime(self, offset: int) -> RuntimeValue:
        value = self._pop(offset)
        if value is _UNINITIALIZED:
            self._fault("uninitialized value used in expression", offset)
        if not isinstance(value, (int, bool, str)):
            self._fault("invalid runtime value on stack", offset)
        return value

    def _fault(self, message: str, offset: int) -> None:
        raise RuntimeFault(message=message, offset=offset)

    def _format_value(self, value: RuntimeValue) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def _is_int(self, value: RuntimeValue) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)


def execute_chunk(chunk: Chunk) -> tuple[list[str], list[Diagnostic]]:
    return VirtualMachine(chunk).execute()


__all__ = [
    "VirtualMachine",
    "execute_chunk",
]
