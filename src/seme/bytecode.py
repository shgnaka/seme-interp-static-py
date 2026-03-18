from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from seme.runtime import RuntimeValue

ConstantValue = RuntimeValue


class OpCode(StrEnum):
    LOAD_CONST = "LOAD_CONST"
    LOAD_UNINITIALIZED = "LOAD_UNINITIALIZED"
    LOAD_LOCAL = "LOAD_LOCAL"
    STORE_LOCAL = "STORE_LOCAL"
    POP = "POP"
    POP_N = "POP_N"
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    MOD = "MOD"
    NEGATE = "NEGATE"
    NOT = "NOT"
    EQUAL = "EQUAL"
    NOT_EQUAL = "NOT_EQUAL"
    LESS = "LESS"
    LESS_EQUAL = "LESS_EQUAL"
    GREATER = "GREATER"
    GREATER_EQUAL = "GREATER_EQUAL"
    JUMP = "JUMP"
    JUMP_IF_FALSE = "JUMP_IF_FALSE"
    PRINT = "PRINT"
    RETURN = "RETURN"


@dataclass(frozen=True)
class SourceSpan:
    line: int
    column: int


@dataclass(frozen=True)
class Instruction:
    opcode: OpCode
    operands: tuple[int, ...] = ()


@dataclass(frozen=True)
class LocalInfo:
    name: str
    slot: int
    depth: int
    is_const: bool


@dataclass
class Chunk:
    instructions: list[Instruction] = field(default_factory=list)
    constants: list[ConstantValue] = field(default_factory=list)
    source_map: list[SourceSpan] = field(default_factory=list)

    def add_constant(self, value: ConstantValue) -> int:
        self.constants.append(value)
        return len(self.constants) - 1

    def emit(self, opcode: OpCode, *operands: int, span: SourceSpan) -> int:
        self.instructions.append(Instruction(opcode=opcode, operands=operands))
        self.source_map.append(span)
        return len(self.instructions) - 1

    def span_for_offset(self, offset: int) -> SourceSpan:
        return self.source_map[offset]


BYTECODE_INSTRUCTION_SET: dict[OpCode, str] = {
    OpCode.LOAD_CONST: "Push a constant-pool value onto the operand stack.",
    OpCode.LOAD_UNINITIALIZED: "Push an uninitialized local sentinel onto the operand stack.",
    OpCode.LOAD_LOCAL: "Push a local slot value onto the operand stack.",
    OpCode.STORE_LOCAL: "Write the top of stack into a local slot without popping it.",
    OpCode.POP: "Discard the top stack value.",
    OpCode.POP_N: "Discard N locals from the end of the local-slots array.",
    OpCode.ADD: "Pop two ints and push their sum.",
    OpCode.SUB: "Pop two ints and push their difference.",
    OpCode.MUL: "Pop two ints and push their product.",
    OpCode.DIV: "Pop two ints and push their quotient.",
    OpCode.MOD: "Pop two ints and push their modulo.",
    OpCode.NEGATE: "Pop one int and push its negation.",
    OpCode.NOT: "Pop one bool and push its logical negation.",
    OpCode.EQUAL: "Pop two same-typed values and push equality result.",
    OpCode.NOT_EQUAL: "Pop two same-typed values and push inequality result.",
    OpCode.LESS: "Pop two ints and push left < right.",
    OpCode.LESS_EQUAL: "Pop two ints and push left <= right.",
    OpCode.GREATER: "Pop two ints and push left > right.",
    OpCode.GREATER_EQUAL: "Pop two ints and push left >= right.",
    OpCode.JUMP: "Set the instruction pointer to an absolute target offset.",
    OpCode.JUMP_IF_FALSE: "Peek one bool and jump when the value is false.",
    OpCode.PRINT: "Pop one runtime value and append its display form to stdout.",
    OpCode.RETURN: "Terminate chunk execution.",
}


__all__ = [
    "BYTECODE_INSTRUCTION_SET",
    "Chunk",
    "ConstantValue",
    "Instruction",
    "LocalInfo",
    "OpCode",
    "SourceSpan",
]
