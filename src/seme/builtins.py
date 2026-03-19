from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from seme.runtime import RuntimeHeap, RuntimeValue, RuntimeValueError, StackValue, VOID, format_runtime_value


class RuntimeHost(Protocol):
    @property
    def runtime_heap(self) -> RuntimeHeap:
        ...

    def write_stdout_line(self, line: str) -> None:
        ...


BuiltinHandler = Callable[[list[RuntimeValue], RuntimeHost], StackValue]


@dataclass(frozen=True)
class BuiltinSpec:
    name: str
    arity: int
    handler: BuiltinHandler


class BuiltinRegistry:
    def __init__(self, builtins: list[BuiltinSpec] | None = None) -> None:
        self._builtins: dict[str, BuiltinSpec] = {}
        for builtin in builtins or []:
            self.register(builtin)

    def register(self, builtin: BuiltinSpec) -> None:
        self._builtins[builtin.name] = builtin

    def lookup(self, name: str) -> BuiltinSpec | None:
        return self._builtins.get(name)

    def invoke(self, name: str, args: list[RuntimeValue], host: RuntimeHost) -> StackValue:
        builtin = self.lookup(name)
        if builtin is None:
            raise RuntimeValueError(f"unknown builtin '{name}'")
        if len(args) != builtin.arity:
            if builtin.arity == 1:
                raise RuntimeValueError(f"{name} requires exactly one argument")
            raise RuntimeValueError(f"{name} requires exactly {builtin.arity} arguments")
        return builtin.handler(args, host)


def _print_builtin(args: list[RuntimeValue], host: RuntimeHost) -> StackValue:
    host.write_stdout_line(format_runtime_value(args[0], heap=host.runtime_heap))
    return VOID


DEFAULT_BUILTINS = BuiltinRegistry(
    builtins=[
        BuiltinSpec(name="print", arity=1, handler=_print_builtin),
    ]
)


__all__ = [
    "BuiltinRegistry",
    "BuiltinSpec",
    "DEFAULT_BUILTINS",
    "RuntimeHost",
]
