from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from seme.bytecode import Instruction, OpCode, SourceSpan


class TracePhase(StrEnum):
    BEFORE = "before"
    AFTER = "after"
    ERROR = "error"


@dataclass(frozen=True)
class TraceEvent:
    phase: TracePhase
    offset: int
    instruction: Instruction
    span: SourceSpan
    stack_depth: int
    frame_depth: int


TraceHook = Callable[[TraceEvent], None]


__all__ = [
    "TraceEvent",
    "TraceHook",
    "TracePhase",
]
