from __future__ import annotations

from seme.bytecode import Chunk, Instruction, OpCode, SourceSpan
from seme.diagnostics import Diagnostic
from seme.runtime import is_string_value
from seme.source_mapping import source_span_for_offset


def validate_chunk(chunk: Chunk) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if len(chunk.instructions) != len(chunk.source_map):
        diagnostics.append(
            Diagnostic(
                code="BYTECODE-001",
                message="bytecode chunk instructions and source map lengths must match",
                line=1,
                column=1,
            )
        )
        return diagnostics

    for offset, instruction in enumerate(chunk.instructions):
        span = source_span_for_offset(chunk, offset)
        diagnostics.extend(_validate_instruction(chunk, instruction, span, offset))

    return diagnostics


def _validate_instruction(
    chunk: Chunk,
    instruction: Instruction,
    span: SourceSpan,
    offset: int,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    opcode = instruction.opcode
    operands = instruction.operands

    def add_diag(message: str, code: str = "BYTECODE-002") -> None:
        diagnostics.append(Diagnostic(code=code, message=message, line=span.line, column=span.column))

    if opcode in (OpCode.LOAD_CONST, OpCode.LOAD_GLOBAL, OpCode.DEFINE_GLOBAL, OpCode.STORE_GLOBAL, OpCode.LOAD_LOCAL, OpCode.STORE_LOCAL):
        if len(operands) != 1:
            add_diag(f"{opcode.value} expects exactly one operand")
            return diagnostics
        operand = operands[0]
        if operand < 0:
            add_diag(f"{opcode.value} operand must be non-negative")
            return diagnostics
        if opcode == OpCode.LOAD_CONST:
            if operand >= len(chunk.constants):
                add_diag(f"{opcode.value} constant index {operand} is out of range")
                return diagnostics
            return diagnostics
        if opcode in (OpCode.LOAD_GLOBAL, OpCode.DEFINE_GLOBAL, OpCode.STORE_GLOBAL):
            if operand >= len(chunk.constants):
                add_diag(f"{opcode.value} name constant index {operand} is out of range")
                return diagnostics
            if not is_string_value(chunk.constants[operand]):
                add_diag(f"{opcode.value} requires a string constant operand")
            return diagnostics
        return diagnostics

    if opcode in (OpCode.LOAD_UNINITIALIZED, OpCode.POP, OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, OpCode.MOD, OpCode.NEGATE, OpCode.NOT, OpCode.EQUAL, OpCode.NOT_EQUAL, OpCode.LESS, OpCode.LESS_EQUAL, OpCode.GREATER, OpCode.GREATER_EQUAL, OpCode.PRINT, OpCode.RETURN):
        if operands:
            add_diag(f"{opcode.value} expects no operands")
        return diagnostics

    if opcode in (OpCode.POP_N, OpCode.JUMP, OpCode.JUMP_IF_FALSE):
        if len(operands) != 1:
            add_diag(f"{opcode.value} expects exactly one operand")
            return diagnostics
        operand = operands[0]
        if operand < 0:
            add_diag(f"{opcode.value} operand must be non-negative")
            return diagnostics
        if opcode in (OpCode.JUMP, OpCode.JUMP_IF_FALSE) and operand >= len(chunk.instructions):
            add_diag(f"{opcode.value} target {operand} is out of range")
        return diagnostics

    add_diag(f"unsupported opcode {opcode.value}")
    return diagnostics


__all__ = [
    "validate_chunk",
]
