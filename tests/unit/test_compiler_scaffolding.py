from __future__ import annotations

from seme.bytecode import OpCode, SourceSpan
from seme.compiler import BytecodeBuilder, CompilerState


def test_emit_jump_then_bind_label_patches_forward_target() -> None:
    builder = BytecodeBuilder()
    exit_label = builder.new_label("exit")

    jump_offset = builder.emit_jump(OpCode.JUMP_IF_FALSE, exit_label, span=SourceSpan(line=1, column=4))
    builder.emit(OpCode.LOAD_CONST, 0, span=SourceSpan(line=1, column=10))
    bound_offset = builder.bind_label(exit_label)

    assert jump_offset == 0
    assert bound_offset == 2
    assert builder.chunk.instructions[0].operands == (2,)
    assert exit_label.patch_sites == []


def test_compiler_state_tracks_scope_depth_and_locals() -> None:
    state = CompilerState()

    outer = state.declare_local("x", is_const=False)
    state.begin_scope()
    inner = state.declare_local("x", is_const=True)

    assert outer.slot == 0
    assert outer.depth == 0
    assert inner.slot == 1
    assert inner.depth == 1
    assert state.resolve_local("x") == inner

    dropped = state.end_scope()

    assert dropped == [inner]
    assert state.resolve_local("x") == outer


def test_render_produces_human_readable_bytecode_listing() -> None:
    builder = BytecodeBuilder()

    builder.emit(OpCode.LOAD_CONST, 0, span=SourceSpan(line=2, column=3))
    builder.emit(OpCode.PRINT, span=SourceSpan(line=2, column=9))

    assert builder.render() == [
        "0000 LOAD_CONST 0 ; 2:3",
        "0001 PRINT ; 2:9",
    ]
