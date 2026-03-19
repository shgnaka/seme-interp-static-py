from __future__ import annotations

from seme.bytecode import Chunk, OpCode
from seme.runtime import RuntimeValue, SemeBool, SemeInt, SemeString, format_runtime_value
from seme.source_mapping import source_span_for_offset


def disassemble_chunk(chunk: Chunk) -> list[str]:
    lines: list[str] = []
    for offset, instruction in enumerate(chunk.instructions):
        span = source_span_for_offset(chunk, offset)
        operands = _format_operands(chunk, instruction.opcode, instruction.operands)
        operand_suffix = f" {operands}" if operands else ""
        lines.append(
            f"{offset:04d} {instruction.opcode.value}{operand_suffix} ; {span.line}:{span.column}"
        )
    return lines


def _format_operands(chunk: Chunk, opcode: OpCode, operands: tuple[int, ...]) -> str:
    if not operands:
        return ""

    if opcode == OpCode.LOAD_CONST:
        const_index = operands[0]
        if const_index < len(chunk.constants):
            return f"{const_index} ({_format_constant(chunk.constants[const_index])})"
        return str(const_index)

    if opcode in (OpCode.LOAD_GLOBAL, OpCode.DEFINE_GLOBAL, OpCode.STORE_GLOBAL):
        name_index = operands[0]
        if name_index < len(chunk.constants):
            return f"{name_index} ({_format_constant(chunk.constants[name_index])})"
        return str(name_index)

    return " ".join(str(operand) for operand in operands)


def _format_constant(value: RuntimeValue) -> str:
    if isinstance(value, (SemeInt, SemeBool, SemeString)):
        return format_runtime_value(value)
    return repr(value)


__all__ = [
    "disassemble_chunk",
]
