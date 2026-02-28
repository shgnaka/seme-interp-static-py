from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    line: int
    column: int
    suggestion: str | None = None

    @property
    def category(self) -> str:
        return self.code.split("-", 1)[0]
