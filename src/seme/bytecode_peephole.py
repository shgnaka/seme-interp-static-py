from __future__ import annotations

from dataclasses import dataclass

from seme.bytecode import Chunk, Instruction, OpCode, SourceSpan
from seme.runtime import (
    RuntimeValue,
    SemeBool,
    SemeInt,
    runtime_arithmetic,
    runtime_compare,
    runtime_equal,
    runtime_negate,
    runtime_not,
    same_runtime_type,
)


@dataclass(frozen=True)
class PeepholeRecord:
    instruction: Instruction
    span: SourceSpan
    source_offsets: tuple[int, ...]
    folded_constant: RuntimeValue | None = None


def optimize_chunk(chunk: Chunk, *, max_passes: int = 8) -> Chunk:
    current = chunk
    for _ in range(max_passes):
        optimized, changed = _optimize_once(current)
        if not changed:
            return current
        current = optimized
    return current


def _optimize_once(chunk: Chunk) -> tuple[Chunk, bool]:
    records: list[PeepholeRecord] = []
    offset_map: dict[int, int] = {}
    changed = False
    offset = 0
    while offset < len(chunk.instructions):
        constant_fold = _try_fold_constants(chunk, offset)
        if constant_fold is not None:
            instruction, span, consumed_offsets, folded_constant = constant_fold
            output_offset = len(records)
            records.append(
                PeepholeRecord(
                    instruction=instruction,
                    span=span,
                    source_offsets=consumed_offsets,
                    folded_constant=folded_constant,
                )
            )
            for consumed_offset in consumed_offsets:
                offset_map[consumed_offset] = output_offset
            offset += len(consumed_offsets)
            changed = True
            continue

        if _is_const_pop(chunk, offset):
            output_offset = len(records)
            offset_map[offset] = output_offset
            offset_map[offset + 1] = output_offset
            offset += 2
            changed = True
            continue

        instruction = chunk.instructions[offset]
        records.append(
            PeepholeRecord(
                instruction=instruction,
                span=chunk.span_for_offset(offset),
                source_offsets=(offset,),
            )
        )
        offset_map[offset] = len(records) - 1
        offset += 1

    optimized = Chunk(constants=list(chunk.constants))
    for record in records:
        instruction = record.instruction
        operands = instruction.operands
        if record.folded_constant is not None:
            constant_index = optimized.add_constant(record.folded_constant)
            optimized.emit(OpCode.LOAD_CONST, constant_index, span=record.span)
            continue

        if instruction.opcode in (OpCode.JUMP, OpCode.JUMP_IF_FALSE):
            if len(operands) != 1:
                optimized.emit(instruction.opcode, *operands, span=record.span)
                continue
            target_offset = operands[0]
            if target_offset not in offset_map:
                optimized.emit(instruction.opcode, *operands, span=record.span)
                continue
            optimized.emit(instruction.opcode, offset_map[target_offset], span=record.span)
            continue

        optimized.emit(instruction.opcode, *operands, span=record.span)

    return optimized, changed


def _is_const_pop(chunk: Chunk, offset: int) -> bool:
    if offset + 1 >= len(chunk.instructions):
        return False
    first = chunk.instructions[offset]
    second = chunk.instructions[offset + 1]
    return first.opcode == OpCode.LOAD_CONST and second.opcode == OpCode.POP


def _try_fold_constants(
    chunk: Chunk,
    offset: int,
) -> tuple[Instruction, SourceSpan, tuple[int, ...], RuntimeValue] | None:
    if offset + 1 >= len(chunk.instructions):
        return None

    first = chunk.instructions[offset]
    second = chunk.instructions[offset + 1]
    second_span = chunk.span_for_offset(offset + 1)

    if first.opcode == OpCode.LOAD_CONST and second.opcode in (OpCode.NEGATE, OpCode.NOT):
        operand = _constant_at(chunk, first)
        if operand is None:
            return None
        if second.opcode == OpCode.NEGATE and isinstance(operand, SemeInt):
            return (
                Instruction(opcode=OpCode.LOAD_CONST, operands=()),
                second_span,
                (offset, offset + 1),
                runtime_negate(operand),
            )
        if second.opcode == OpCode.NOT and isinstance(operand, SemeBool):
            return (
                Instruction(opcode=OpCode.LOAD_CONST, operands=()),
                second_span,
                (offset, offset + 1),
                runtime_not(operand),
            )
        return None

    if offset + 2 >= len(chunk.instructions):
        return None

    third = chunk.instructions[offset + 2]
    third_span = chunk.span_for_offset(offset + 2)
    if first.opcode != OpCode.LOAD_CONST or second.opcode != OpCode.LOAD_CONST:
        return None
    left = _constant_at(chunk, first)
    right = _constant_at(chunk, second)
    if left is None or right is None:
        return None

    if third.opcode in (OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, OpCode.MOD):
        if not isinstance(left, SemeInt) or not isinstance(right, SemeInt):
            return None
        if third.opcode in (OpCode.DIV, OpCode.MOD) and right.value == 0:
            return None
        operator = {
            OpCode.ADD: "add",
            OpCode.SUB: "sub",
            OpCode.MUL: "mul",
            OpCode.DIV: "div",
            OpCode.MOD: "mod",
        }[third.opcode]
        return (
            Instruction(opcode=OpCode.LOAD_CONST, operands=()),
            third_span,
            (offset, offset + 1, offset + 2),
            runtime_arithmetic(operator, left, right),
        )

    if third.opcode in (OpCode.LESS, OpCode.LESS_EQUAL, OpCode.GREATER, OpCode.GREATER_EQUAL):
        if not isinstance(left, SemeInt) or not isinstance(right, SemeInt):
            return None
        operator = {
            OpCode.LESS: "lt",
            OpCode.LESS_EQUAL: "lte",
            OpCode.GREATER: "gt",
            OpCode.GREATER_EQUAL: "gte",
        }[third.opcode]
        return (
            Instruction(opcode=OpCode.LOAD_CONST, operands=()),
            third_span,
            (offset, offset + 1, offset + 2),
            runtime_compare(operator, left, right),
        )

    if third.opcode in (OpCode.EQUAL, OpCode.NOT_EQUAL):
        if not same_runtime_type(left, right):
            return None
        if third.opcode == OpCode.EQUAL:
            operator = "eq"
        else:
            operator = "neq"
        return (
            Instruction(opcode=OpCode.LOAD_CONST, operands=()),
            third_span,
            (offset, offset + 1, offset + 2),
            runtime_equal(operator, left, right),
        )

    return None


def _constant_at(chunk: Chunk, instruction: Instruction) -> RuntimeValue | None:
    if instruction.opcode != OpCode.LOAD_CONST or len(instruction.operands) != 1:
        return None
    const_index = instruction.operands[0]
    if const_index >= len(chunk.constants):
        return None
    return chunk.constants[const_index]


__all__ = [
    "optimize_chunk",
]
