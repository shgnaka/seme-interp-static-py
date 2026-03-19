from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class VMMetrics:
    instruction_count: int = 0
    max_stack_depth: int = 0
    max_frame_depth: int = 0
    runtime_error_count: int = 0
    wall_time_ns: int = 0
    opcode_counts: dict[str, int] = field(default_factory=dict)


ProfilingHook = Callable[[VMMetrics], None]


__all__ = [
    "ProfilingHook",
    "VMMetrics",
]
