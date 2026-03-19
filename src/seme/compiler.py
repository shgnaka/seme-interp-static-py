from __future__ import annotations

from dataclasses import dataclass, field

from seme.ast import Assign, Binary, Block, Call, ConstDecl, Expr, ExprStmt, For, Grouping, Identifier, If, LetDecl, Literal, Program, Stmt, Unary, While
from seme.bytecode import Chunk, GlobalInfo, LocalInfo, OpCode, SourceSpan
from seme.bytecode_disassembler import disassemble_chunk
from seme.bytecode_peephole import optimize_chunk
from seme.runtime import RuntimeValue, make_runtime_value
from seme.token import TokenKind


@dataclass
class Label:
    name: str | None = None
    offset: int | None = None
    patch_sites: list[int] = field(default_factory=list)


@dataclass
class CompilerState:
    chunk: Chunk = field(default_factory=Chunk)
    locals: list[LocalInfo] = field(default_factory=list)
    globals: dict[str, GlobalInfo] = field(default_factory=dict)
    scope_depth: int = 0

    def begin_scope(self) -> None:
        self.scope_depth += 1

    def end_scope(self) -> list[LocalInfo]:
        to_drop = [local for local in self.locals if local.depth == self.scope_depth]
        self.locals = [local for local in self.locals if local.depth != self.scope_depth]
        if self.scope_depth > 0:
            self.scope_depth -= 1
        return to_drop

    def declare_local(self, name: str, *, is_const: bool) -> LocalInfo:
        local = LocalInfo(
            name=name,
            slot=len(self.locals),
            depth=self.scope_depth,
            is_const=is_const,
        )
        self.locals.append(local)
        return local

    def resolve_local(self, name: str) -> LocalInfo | None:
        for local in reversed(self.locals):
            if local.name == name:
                return local
        return None

    def declare_global(self, name: str, *, is_const: bool) -> GlobalInfo:
        global_info = GlobalInfo(name=name, is_const=is_const)
        self.globals[name] = global_info
        return global_info

    def resolve_global(self, name: str) -> GlobalInfo | None:
        return self.globals.get(name)


class BytecodeBuilder:
    def __init__(self, state: CompilerState | None = None) -> None:
        self.state = state or CompilerState()

    @property
    def chunk(self) -> Chunk:
        return self.state.chunk

    def add_constant(self, value: RuntimeValue) -> int:
        return self.chunk.add_constant(value)

    def add_literal_constant(self, value: int | bool | str) -> int:
        return self.add_constant(make_runtime_value(value))

    def emit(self, opcode: OpCode, *operands: int, span: SourceSpan) -> int:
        return self.chunk.emit(opcode, *operands, span=span)

    def new_label(self, name: str | None = None) -> Label:
        return Label(name=name)

    def bind_label(self, label: Label) -> int:
        if label.offset is not None:
            raise ValueError("label is already bound")
        label.offset = len(self.chunk.instructions)
        for patch_site in label.patch_sites:
            self.patch_jump(patch_site, label.offset)
        label.patch_sites.clear()
        return label.offset

    def emit_jump(self, opcode: OpCode, label: Label, *, span: SourceSpan) -> int:
        if opcode not in (OpCode.JUMP, OpCode.JUMP_IF_FALSE):
            raise ValueError(f"opcode {opcode} is not a jump instruction")
        target = label.offset if label.offset is not None else -1
        offset = self.emit(opcode, target, span=span)
        if label.offset is None:
            label.patch_sites.append(offset)
        return offset

    def patch_jump(self, offset: int, target: int) -> None:
        instruction = self.chunk.instructions[offset]
        if instruction.opcode not in (OpCode.JUMP, OpCode.JUMP_IF_FALSE):
            raise ValueError("only jump instructions can be patched")
        if len(instruction.operands) != 1:
            raise ValueError("jump instructions must carry exactly one target operand")
        self.chunk.instructions[offset] = type(instruction)(
            opcode=instruction.opcode,
            operands=(target,),
        )

    def render(self) -> list[str]:
        return disassemble_chunk(self.chunk)


__all__ = [
    "BytecodeBuilder",
    "CompilerState",
    "Label",
]


class Compiler:
    def __init__(self, *, optimize: bool = True) -> None:
        self.builder = BytecodeBuilder()
        self.optimize = optimize

    def compile(self, program: Program) -> Chunk:
        for stmt in program.statements:
            self._compile_stmt(stmt)
        self.builder.emit(OpCode.RETURN, span=SourceSpan(program.line, program.column))
        chunk = self.builder.chunk
        if self.optimize:
            return optimize_chunk(chunk)
        return chunk

    def _compile_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, LetDecl):
            is_global = self.builder.state.scope_depth == 0
            if is_global:
                self.builder.state.declare_global(stmt.name, is_const=False)
            else:
                local = self.builder.state.declare_local(stmt.name, is_const=False)
            if stmt.initializer is None:
                self.builder.emit(OpCode.LOAD_UNINITIALIZED, span=SourceSpan(stmt.line, stmt.column))
            else:
                self._compile_expr(stmt.initializer)
            if is_global:
                self.builder.emit(
                    OpCode.DEFINE_GLOBAL,
                    self._name_constant_index(stmt.name),
                    span=SourceSpan(stmt.line, stmt.column),
                )
            else:
                self.builder.emit(OpCode.STORE_LOCAL, local.slot, span=SourceSpan(stmt.line, stmt.column))
            self.builder.emit(OpCode.POP, span=SourceSpan(stmt.line, stmt.column))
            return

        if isinstance(stmt, ConstDecl):
            is_global = self.builder.state.scope_depth == 0
            if is_global:
                self.builder.state.declare_global(stmt.name, is_const=True)
            else:
                local = self.builder.state.declare_local(stmt.name, is_const=True)
            self._compile_expr(stmt.initializer)
            if is_global:
                self.builder.emit(
                    OpCode.DEFINE_GLOBAL,
                    self._name_constant_index(stmt.name),
                    span=SourceSpan(stmt.line, stmt.column),
                )
            else:
                self.builder.emit(OpCode.STORE_LOCAL, local.slot, span=SourceSpan(stmt.line, stmt.column))
            self.builder.emit(OpCode.POP, span=SourceSpan(stmt.line, stmt.column))
            return

        if isinstance(stmt, Assign):
            self._compile_expr(stmt.value)
            local = self.builder.state.resolve_local(stmt.name)
            if local is not None:
                self.builder.emit(OpCode.STORE_LOCAL, local.slot, span=SourceSpan(stmt.line, stmt.column))
            else:
                self._require_global(stmt.name, stmt.line, stmt.column)
                self.builder.emit(
                    OpCode.STORE_GLOBAL,
                    self._name_constant_index(stmt.name),
                    span=SourceSpan(stmt.line, stmt.column),
                )
            self.builder.emit(OpCode.POP, span=SourceSpan(stmt.line, stmt.column))
            return

        if isinstance(stmt, ExprStmt):
            expr = stmt.expression
            if self._is_print_stmt(expr):
                self._compile_expr(expr.arguments[0])
                self.builder.emit(OpCode.PRINT, span=SourceSpan(expr.line, expr.column))
                return
            self._compile_expr(expr)
            self.builder.emit(OpCode.POP, span=SourceSpan(stmt.line, stmt.column))
            return

        if isinstance(stmt, Block):
            self._compile_block(stmt)
            return

        if isinstance(stmt, If):
            self._compile_if(stmt)
            return

        if isinstance(stmt, While):
            self._compile_while(stmt)
            return

        if isinstance(stmt, For):
            self._compile_for(stmt)
            return

        raise NotImplementedError(f"statement compilation not implemented for {type(stmt).__name__}")

    def _compile_expr(self, expr: Expr) -> None:
        if isinstance(expr, Literal):
            const_index = self.builder.add_literal_constant(expr.value)
            self.builder.emit(OpCode.LOAD_CONST, const_index, span=SourceSpan(expr.line, expr.column))
            return

        if isinstance(expr, Identifier):
            local = self.builder.state.resolve_local(expr.name)
            if local is not None:
                self.builder.emit(OpCode.LOAD_LOCAL, local.slot, span=SourceSpan(expr.line, expr.column))
                return
            self._require_global(expr.name, expr.line, expr.column)
            self.builder.emit(
                OpCode.LOAD_GLOBAL,
                self._name_constant_index(expr.name),
                span=SourceSpan(expr.line, expr.column),
            )
            return

        if isinstance(expr, Grouping):
            self._compile_expr(expr.expression)
            return

        if isinstance(expr, Unary):
            self._compile_expr(expr.operand)
            if expr.operator == TokenKind.MINUS:
                self.builder.emit(OpCode.NEGATE, span=SourceSpan(expr.line, expr.column))
                return
            if expr.operator == TokenKind.BANG:
                self.builder.emit(OpCode.NOT, span=SourceSpan(expr.line, expr.column))
                return
            raise NotImplementedError(f"unsupported unary operator {expr.operator}")

        if isinstance(expr, Binary):
            if expr.operator in (TokenKind.ANDAND, TokenKind.OROR):
                self._compile_logical(expr)
                return
            self._compile_expr(expr.left)
            self._compile_expr(expr.right)
            self.builder.emit(self._binary_opcode(expr.operator), span=SourceSpan(expr.line, expr.column))
            return

        if isinstance(expr, Call) and self._is_print_stmt(expr):
            raise NotImplementedError("print(expr) is only supported in statement position")

        raise NotImplementedError(f"expression compilation not implemented for {type(expr).__name__}")

    def _compile_logical(self, expr: Binary) -> None:
        self._compile_expr(expr.left)
        short_circuit_label = self.builder.new_label("logical_short_circuit")
        done_label = self.builder.new_label("logical_done")

        if expr.operator == TokenKind.ANDAND:
            self.builder.emit_jump(OpCode.JUMP_IF_FALSE, short_circuit_label, span=SourceSpan(expr.line, expr.column))
            self.builder.emit(OpCode.POP, span=SourceSpan(expr.line, expr.column))
            self._compile_expr(expr.right)
            self.builder.emit_jump(OpCode.JUMP, done_label, span=SourceSpan(expr.line, expr.column))
            self.builder.bind_label(short_circuit_label)
            self.builder.emit(OpCode.POP, span=SourceSpan(expr.line, expr.column))
            false_index = self.builder.add_literal_constant(False)
            self.builder.emit(OpCode.LOAD_CONST, false_index, span=SourceSpan(expr.line, expr.column))
            self.builder.bind_label(done_label)
            return

        self.builder.emit_jump(OpCode.JUMP_IF_FALSE, short_circuit_label, span=SourceSpan(expr.line, expr.column))
        true_index = self.builder.add_literal_constant(True)
        self.builder.emit(OpCode.POP, span=SourceSpan(expr.line, expr.column))
        self.builder.emit(OpCode.LOAD_CONST, true_index, span=SourceSpan(expr.line, expr.column))
        self.builder.emit_jump(OpCode.JUMP, done_label, span=SourceSpan(expr.line, expr.column))
        self.builder.bind_label(short_circuit_label)
        self.builder.emit(OpCode.POP, span=SourceSpan(expr.line, expr.column))
        self._compile_expr(expr.right)
        self.builder.bind_label(done_label)

    def _binary_opcode(self, operator: TokenKind) -> OpCode:
        opcodes = {
            TokenKind.PLUS: OpCode.ADD,
            TokenKind.MINUS: OpCode.SUB,
            TokenKind.STAR: OpCode.MUL,
            TokenKind.SLASH: OpCode.DIV,
            TokenKind.PERCENT: OpCode.MOD,
            TokenKind.EQEQ: OpCode.EQUAL,
            TokenKind.NEQ: OpCode.NOT_EQUAL,
            TokenKind.LT: OpCode.LESS,
            TokenKind.LTE: OpCode.LESS_EQUAL,
            TokenKind.GT: OpCode.GREATER,
            TokenKind.GTE: OpCode.GREATER_EQUAL,
        }
        try:
            return opcodes[operator]
        except KeyError as exc:
            raise NotImplementedError(f"unsupported binary operator {operator}") from exc

    def _is_print_stmt(self, expr: Expr) -> bool:
        return (
            isinstance(expr, Call)
            and isinstance(expr.callee, Identifier)
            and expr.callee.name == "print"
            and len(expr.arguments) == 1
        )

    def _compile_block(self, block: Block) -> None:
        self.builder.state.begin_scope()
        try:
            for stmt in block.statements:
                self._compile_stmt(stmt)
        finally:
            self._emit_scope_cleanup(block.line, block.column)

    def _compile_if(self, stmt: If) -> None:
        self._compile_expr(stmt.condition)
        else_label = self.builder.new_label("if_else")
        done_label = self.builder.new_label("if_done")
        self.builder.emit_jump(OpCode.JUMP_IF_FALSE, else_label, span=SourceSpan(stmt.line, stmt.column))
        self.builder.emit(OpCode.POP, span=SourceSpan(stmt.line, stmt.column))
        self._compile_stmt(stmt.then_branch)
        self.builder.emit_jump(OpCode.JUMP, done_label, span=SourceSpan(stmt.line, stmt.column))
        self.builder.bind_label(else_label)
        self.builder.emit(OpCode.POP, span=SourceSpan(stmt.line, stmt.column))
        if stmt.else_branch is not None:
            self._compile_stmt(stmt.else_branch)
        self.builder.bind_label(done_label)

    def _compile_while(self, stmt: While) -> None:
        loop_start = self.builder.new_label("while_start")
        loop_end = self.builder.new_label("while_end")
        self.builder.bind_label(loop_start)
        self._compile_expr(stmt.condition)
        self.builder.emit_jump(OpCode.JUMP_IF_FALSE, loop_end, span=SourceSpan(stmt.line, stmt.column))
        self.builder.emit(OpCode.POP, span=SourceSpan(stmt.line, stmt.column))
        self._compile_stmt(stmt.body)
        self.builder.emit_jump(OpCode.JUMP, loop_start, span=SourceSpan(stmt.line, stmt.column))
        self.builder.bind_label(loop_end)
        self.builder.emit(OpCode.POP, span=SourceSpan(stmt.line, stmt.column))

    def _compile_for(self, stmt: For) -> None:
        self.builder.state.begin_scope()
        try:
            if stmt.init is not None:
                self._compile_for_clause(stmt.init)

            loop_start = self.builder.new_label("for_start")
            loop_end = self.builder.new_label("for_end")
            self.builder.bind_label(loop_start)

            if stmt.condition is not None:
                self._compile_expr(stmt.condition)
                self.builder.emit_jump(OpCode.JUMP_IF_FALSE, loop_end, span=SourceSpan(stmt.line, stmt.column))
                self.builder.emit(OpCode.POP, span=SourceSpan(stmt.line, stmt.column))

            self._compile_stmt(stmt.body)

            if stmt.update is not None:
                self._compile_for_clause(stmt.update)

            self.builder.emit_jump(OpCode.JUMP, loop_start, span=SourceSpan(stmt.line, stmt.column))
            self.builder.bind_label(loop_end)
            if stmt.condition is not None:
                self.builder.emit(OpCode.POP, span=SourceSpan(stmt.line, stmt.column))
        finally:
            self._emit_scope_cleanup(stmt.line, stmt.column)

    def _compile_for_clause(self, clause: Stmt | Expr) -> None:
        if isinstance(clause, Assign):
            self._compile_stmt(clause)
            return
        if isinstance(clause, (LetDecl, ConstDecl, ExprStmt, Block, If, While, For)):
            self._compile_stmt(clause)
            return
        self._compile_expr(clause)
        self.builder.emit(OpCode.POP, span=SourceSpan(clause.line, clause.column))

    def _emit_scope_cleanup(self, line: int, column: int) -> None:
        dropped = self.builder.state.end_scope()
        if dropped:
            self.builder.emit(OpCode.POP_N, len(dropped), span=SourceSpan(line, column))

    def _require_local(self, name: str, line: int, column: int) -> LocalInfo:
        local = self.builder.state.resolve_local(name)
        if local is None:
            raise ValueError(f"unresolved local '{name}' at {line}:{column}")
        return local

    def _require_global(self, name: str, line: int, column: int) -> GlobalInfo:
        global_info = self.builder.state.resolve_global(name)
        if global_info is None:
            raise ValueError(f"unresolved global '{name}' at {line}:{column}")
        return global_info

    def _name_constant_index(self, name: str) -> int:
        return self.builder.add_literal_constant(name)


def compile_program(program: Program, *, optimize: bool = True) -> Chunk:
    return Compiler(optimize=optimize).compile(program)


__all__ = [
    "BytecodeBuilder",
    "Compiler",
    "CompilerState",
    "Label",
    "compile_program",
]
