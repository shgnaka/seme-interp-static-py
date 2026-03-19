from __future__ import annotations

import json
from dataclasses import asdict

from seme.bytecode import Chunk, Instruction, OpCode, SourceSpan
from seme.runtime import HeapRef, SemeBool, SemeInt, SemeString, RuntimeValue, RuntimeValueError


def serialize_runtime_value(value: RuntimeValue) -> dict[str, object]:
    if isinstance(value, SemeInt):
        return {"kind": "int", "value": value.value}
    if isinstance(value, SemeBool):
        return {"kind": "bool", "value": value.value}
    if isinstance(value, SemeString):
        return {"kind": "string", "value": value.value}
    if isinstance(value, HeapRef):
        return {"kind": "heap_ref", "object_id": value.object_id, "ref_kind": value.kind}
    raise RuntimeValueError(f"unsupported runtime value type {type(value).__name__}")


def deserialize_runtime_value(payload: dict[str, object]) -> RuntimeValue:
    kind = payload.get("kind")
    if kind == "int":
        return SemeInt(int(payload["value"]))
    if kind == "bool":
        return SemeBool(bool(payload["value"]))
    if kind == "string":
        return SemeString(str(payload["value"]))
    if kind == "heap_ref":
        return HeapRef(object_id=int(payload["object_id"]), kind=str(payload["ref_kind"]))
    raise RuntimeValueError(f"unsupported serialized runtime value kind '{kind}'")


def serialize_chunk(chunk: Chunk) -> str:
    payload = {
        "instructions": [
            {
                "opcode": instruction.opcode.value,
                "operands": list(instruction.operands),
            }
            for instruction in chunk.instructions
        ],
        "constants": [serialize_runtime_value(value) for value in chunk.constants],
        "source_map": [asdict(span) for span in chunk.source_map],
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def deserialize_chunk(data: str) -> Chunk:
    payload = json.loads(data)
    chunk = Chunk()
    chunk.constants.extend(deserialize_runtime_value(value) for value in payload["constants"])
    chunk.instructions.extend(
        Instruction(opcode=OpCode(item["opcode"]), operands=tuple(int(op) for op in item["operands"]))
        for item in payload["instructions"]
    )
    chunk.source_map.extend(SourceSpan(line=int(span["line"]), column=int(span["column"])) for span in payload["source_map"])
    return chunk


__all__ = [
    "deserialize_chunk",
    "deserialize_runtime_value",
    "serialize_chunk",
    "serialize_runtime_value",
]
