from __future__ import annotations

from seme.runtime_faults import (
    RuntimeFault,
    diagnostic_from_runtime_fault,
    diagnostic_from_unexpected_runtime_error,
)


def test_runtime_fault_maps_to_runtime_001_diagnostic() -> None:
    diagnostic = diagnostic_from_runtime_fault(
        RuntimeFault(message="division or modulo by zero", line=2, column=12)
    )

    assert (diagnostic.code, diagnostic.message, diagnostic.line, diagnostic.column) == (
        "RUNTIME-001",
        "Runtime error: division or modulo by zero",
        2,
        12,
    )


def test_unexpected_runtime_error_maps_through_shared_helper() -> None:
    diagnostic = diagnostic_from_unexpected_runtime_error(
        ValueError("boom"),
        line=4,
        column=7,
    )

    assert (diagnostic.code, diagnostic.message, diagnostic.line, diagnostic.column) == (
        "RUNTIME-001",
        "Runtime error: boom",
        4,
        7,
    )
