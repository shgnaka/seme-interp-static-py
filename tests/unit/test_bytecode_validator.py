from __future__ import annotations

from seme.bytecode import Chunk, Instruction, OpCode, SourceSpan
from seme.bytecode_validator import validate_chunk
from seme.runtime import SemeInt, SemeString


def test_validate_chunk_accepts_well_formed_chunk() -> None:
    chunk = Chunk()
    const_index = chunk.add_constant(SemeInt(1))
    chunk.emit(OpCode.LOAD_CONST, const_index, span=SourceSpan(line=1, column=1))
    chunk.emit(OpCode.RETURN, span=SourceSpan(line=1, column=10))

    assert validate_chunk(chunk) == []


def test_validate_chunk_rejects_source_map_length_mismatch() -> None:
    chunk = Chunk()
    chunk.instructions.append(Instruction(opcode=OpCode.RETURN))

    diagnostics = validate_chunk(chunk)

    assert [(d.code, d.message, d.line, d.column) for d in diagnostics] == [
        (
            "BYTECODE-001",
            "bytecode chunk instructions and source map lengths must match",
            1,
            1,
        )
    ]


def test_validate_chunk_rejects_invalid_jump_target_and_name_constant() -> None:
    chunk = Chunk()
    chunk.constants.append(SemeInt(1))
    chunk.instructions.extend(
        [
            Instruction(opcode=OpCode.JUMP, operands=(5,)),
            Instruction(opcode=OpCode.LOAD_GLOBAL, operands=(0,)),
            Instruction(opcode=OpCode.RETURN),
        ]
    )
    chunk.source_map.extend(
        [
            SourceSpan(line=1, column=1),
            SourceSpan(line=1, column=2),
            SourceSpan(line=1, column=3),
        ]
    )

    diagnostics = validate_chunk(chunk)

    assert [(d.code, d.message, d.line, d.column) for d in diagnostics] == [
        ("BYTECODE-002", "JUMP target 5 is out of range", 1, 1),
        ("BYTECODE-002", "LOAD_GLOBAL requires a string constant operand", 1, 2),
    ]
