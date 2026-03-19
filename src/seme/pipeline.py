from __future__ import annotations

from hashlib import sha256
from typing import Literal

from seme.bytecode_cache import BytecodeCache
from seme.compiler import compile_program
from seme.diagnostics import Diagnostic
from seme.interpreter import eval_program
from seme.lexer import lex
from seme.parser import parse
from seme.typechecker import check_types
from seme.vm import execute_chunk

ExecutionBackend = Literal["vm", "interpreter"]
COMPILER_VERSION = "bytecode-cache-v1"


def run_check(source: str) -> list[Diagnostic]:
    tokens, lex_diags = lex(source)
    if lex_diags:
        return lex_diags
    program, parse_diags = parse(tokens)
    if parse_diags:
        return parse_diags
    return check_types(program)


def run_execute(
    source: str,
    backend: ExecutionBackend = "vm",
    *,
    cache: BytecodeCache | None = None,
) -> tuple[str, list[Diagnostic]]:
    tokens, lex_diags = lex(source)
    if lex_diags:
        return "", lex_diags

    program, parse_diags = parse(tokens)
    if parse_diags:
        return "", parse_diags

    type_diags = check_types(program)
    if type_diags:
        return "", type_diags

    if backend == "vm":
        if cache is not None:
            source_hash = sha256(source.encode("utf-8")).hexdigest()
            chunk = cache.get_or_build(
                source_hash=source_hash,
                compiler_version=COMPILER_VERSION,
                build=lambda: compile_program(program),
            )
        else:
            chunk = compile_program(program)
        stdout_lines, runtime_diags = execute_chunk(chunk)
    elif backend == "interpreter":
        stdout_lines, runtime_diags = eval_program(program)
    else:  # pragma: no cover
        raise ValueError(f"Unsupported execution backend: {backend}")

    stdout_text = ""
    if stdout_lines:
        stdout_text = "\n".join(stdout_lines) + "\n"
    if runtime_diags:
        return stdout_text, runtime_diags
    return stdout_text, []
