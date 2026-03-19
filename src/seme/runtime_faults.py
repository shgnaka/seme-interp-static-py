from __future__ import annotations

from dataclasses import dataclass

from seme.diagnostics import Diagnostic


@dataclass(frozen=True)
class RuntimeFault(Exception):
    message: str
    line: int
    column: int


def runtime_diagnostic(message: str, line: int, column: int) -> Diagnostic:
    return Diagnostic(
        code="RUNTIME-001",
        message=f"Runtime error: {message}",
        line=line,
        column=column,
    )


def diagnostic_from_runtime_fault(fault: RuntimeFault) -> Diagnostic:
    return runtime_diagnostic(fault.message, fault.line, fault.column)


def diagnostic_from_unexpected_runtime_error(exc: Exception, *, line: int, column: int) -> Diagnostic:
    return runtime_diagnostic(str(exc), line, column)


__all__ = [
    "RuntimeFault",
    "diagnostic_from_runtime_fault",
    "diagnostic_from_unexpected_runtime_error",
    "runtime_diagnostic",
]
