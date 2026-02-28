from __future__ import annotations

from dataclasses import dataclass

from seme.ast import (
    Assign,
    Binary,
    Block,
    Call,
    ConstDecl,
    Expr,
    ExprStmt,
    For,
    Grouping,
    Identifier,
    If,
    LetDecl,
    Literal,
    Program,
    Stmt,
    Unary,
    While,
)
from seme.diagnostics import Diagnostic
from seme.token import Token, TokenKind

SUPPORTED_TYPES = {"int", "bool", "string"}

PREC_NONE = 0
PREC_OR = 10
PREC_AND = 20
PREC_EQUALITY = 30
PREC_COMPARISON = 40
PREC_TERM = 50
PREC_FACTOR = 60
PREC_UNARY = 70
PREC_CALL = 80


@dataclass(frozen=True)
class ParseError(Exception):
    diagnostic: Diagnostic


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0
        self.diagnostics: list[Diagnostic] = []

    def parse(self) -> tuple[Program, list[Diagnostic]]:
        statements: list[Stmt] = []
        while not self._at_end():
            try:
                statements.append(self._parse_statement())
            except ParseError:
                self._synchronize()
        if statements:
            return (
                Program(
                    statements=statements,
                    line=statements[0].line,
                    column=statements[0].column,
                ),
                self.diagnostics,
            )
        return Program(statements=statements), self.diagnostics

    def _parse_statement(self) -> Stmt:
        if self._match(TokenKind.LET):
            return self._parse_let_decl(self._previous(), require_semi=True)
        if self._match(TokenKind.CONST):
            return self._parse_const_decl(self._previous(), require_semi=True)
        if self._match(TokenKind.IF):
            return self._parse_if_stmt(self._previous())
        if self._match(TokenKind.WHILE):
            return self._parse_while_stmt(self._previous())
        if self._match(TokenKind.FOR):
            return self._parse_for_stmt(self._previous())
        if self._match(TokenKind.LBRACE):
            return self._parse_block(self._previous())
        if self._check(TokenKind.IDENT) and self._check_next(TokenKind.ASSIGN):
            return self._parse_assign_stmt(require_semi=True)
        return self._parse_expr_stmt()

    def _parse_let_decl(self, let_tok: Token, require_semi: bool) -> LetDecl:
        ident = self._consume(TokenKind.IDENT, "Expected identifier after 'let'")
        type_name: str | None = None
        initializer: Expr | None = None
        if self._match(TokenKind.COLON):
            type_tok = self._consume(TokenKind.IDENT, "Expected type name after ':'")
            if type_tok.lexeme not in SUPPORTED_TYPES:
                raise self._error(type_tok, f"Unknown type '{type_tok.lexeme}'")
            type_name = type_tok.lexeme
        if self._match(TokenKind.ASSIGN):
            initializer = self._parse_expression()
        if require_semi:
            self._consume(TokenKind.SEMI, "Expected ';' after let declaration")
        return LetDecl(
            name=ident.lexeme,
            initializer=initializer,
            type_name=type_name,
            line=let_tok.line,
            column=let_tok.column,
        )

    def _parse_const_decl(self, const_tok: Token, require_semi: bool) -> ConstDecl:
        ident = self._consume(TokenKind.IDENT, "Expected identifier after 'const'")
        type_name: str | None = None
        if self._match(TokenKind.COLON):
            type_tok = self._consume(TokenKind.IDENT, "Expected type name after ':'")
            if type_tok.lexeme not in SUPPORTED_TYPES:
                raise self._error(type_tok, f"Unknown type '{type_tok.lexeme}'")
            type_name = type_tok.lexeme
        self._consume(TokenKind.ASSIGN, "Expected '=' and initializer in const declaration")
        initializer = self._parse_expression()
        if require_semi:
            self._consume(TokenKind.SEMI, "Expected ';' after const declaration")
        return ConstDecl(
            name=ident.lexeme,
            initializer=initializer,
            type_name=type_name,
            line=const_tok.line,
            column=const_tok.column,
        )

    def _parse_assign_stmt(self, require_semi: bool) -> Assign:
        ident = self._consume(TokenKind.IDENT, "Expected assignment target")
        self._consume(TokenKind.ASSIGN, "Expected '=' in assignment")
        value = self._parse_expression()
        if require_semi:
            self._consume(TokenKind.SEMI, "Expected ';' after assignment")
        return Assign(name=ident.lexeme, value=value, line=ident.line, column=ident.column)

    def _parse_if_stmt(self, if_tok: Token) -> If:
        self._consume(TokenKind.LPAREN, "Expected '(' after 'if'")
        condition = self._parse_expression()
        self._consume(TokenKind.RPAREN, "Expected ')' after if condition")
        then_branch = self._parse_statement()
        else_branch: Stmt | None = None
        if self._match(TokenKind.ELSE):
            else_branch = self._parse_statement()
        return If(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            line=if_tok.line,
            column=if_tok.column,
        )

    def _parse_while_stmt(self, while_tok: Token) -> While:
        self._consume(TokenKind.LPAREN, "Expected '(' after 'while'")
        condition = self._parse_expression()
        self._consume(TokenKind.RPAREN, "Expected ')' after while condition")
        body = self._parse_statement()
        return While(condition=condition, body=body, line=while_tok.line, column=while_tok.column)

    def _parse_for_stmt(self, for_tok: Token) -> For:
        self._consume(TokenKind.LPAREN, "Expected '(' after 'for'")

        init: Stmt | Expr | None = None
        if not self._check(TokenKind.SEMI):
            try:
                if self._match(TokenKind.LET):
                    init = self._parse_let_decl(self._previous(), require_semi=False)
                elif self._match(TokenKind.CONST):
                    init = self._parse_const_decl(self._previous(), require_semi=False)
                elif self._check(TokenKind.IDENT) and self._check_next(TokenKind.ASSIGN):
                    init = self._parse_assign_stmt(require_semi=False)
                else:
                    init = self._parse_expression()
            except ParseError:
                self._recover_for_clause(TokenKind.SEMI)
        self._consume(TokenKind.SEMI, "Expected ';' after for-init")

        condition: Expr | None = None
        if not self._check(TokenKind.SEMI):
            try:
                condition = self._parse_expression()
            except ParseError:
                self._recover_for_clause(TokenKind.SEMI)
        self._consume(TokenKind.SEMI, "Expected ';' after for-condition")

        update: Expr | Assign | None = None
        if not self._check(TokenKind.RPAREN):
            try:
                if self._check(TokenKind.IDENT) and self._check_next(TokenKind.ASSIGN):
                    update = self._parse_assign_stmt(require_semi=False)
                else:
                    update = self._parse_expression()
            except ParseError:
                self._recover_for_clause(TokenKind.RPAREN)
        self._consume(TokenKind.RPAREN, "Expected ')' after for clauses")
        body = self._parse_statement()
        return For(
            init=init,
            condition=condition,
            update=update,
            body=body,
            line=for_tok.line,
            column=for_tok.column,
        )

    def _parse_block(self, lbrace: Token) -> Block:
        statements: list[Stmt] = []
        while not self._check(TokenKind.RBRACE) and not self._at_end():
            try:
                statements.append(self._parse_statement())
            except ParseError:
                self._synchronize()
        self._consume(TokenKind.RBRACE, "Expected '}' after block")
        return Block(statements=statements, line=lbrace.line, column=lbrace.column)

    def _parse_expr_stmt(self) -> ExprStmt:
        expr = self._parse_expression()
        self._consume(TokenKind.SEMI, "Expected ';' after expression statement")
        return ExprStmt(expression=expr, line=expr.line, column=expr.column)

    def _parse_expression(self, min_prec: int = PREC_OR) -> Expr:
        left = self._parse_prefix()
        while True:
            tok = self._peek()
            prec = self._infix_precedence(tok.kind)
            if prec < min_prec:
                break
            op = self._advance()
            if op.kind == TokenKind.LPAREN:
                left = self._finish_call(left, op)
                continue
            right = self._parse_expression(prec + 1)
            left = Binary(
                left=left,
                operator=op.kind,
                right=right,
                line=op.line,
                column=op.column,
            )
        return left

    def _parse_prefix(self) -> Expr:
        tok = self._advance()
        if tok.kind == TokenKind.INT_LIT:
            return Literal(value=int(tok.lexeme), line=tok.line, column=tok.column)
        if tok.kind == TokenKind.STRING_LIT:
            return Literal(value=tok.lexeme, line=tok.line, column=tok.column)
        if tok.kind == TokenKind.BOOL_LIT:
            return Literal(value=(tok.lexeme == "true"), line=tok.line, column=tok.column)
        if tok.kind == TokenKind.IDENT:
            return Identifier(name=tok.lexeme, line=tok.line, column=tok.column)
        if tok.kind in (TokenKind.BANG, TokenKind.MINUS):
            operand = self._parse_expression(PREC_UNARY)
            return Unary(operator=tok.kind, operand=operand, line=tok.line, column=tok.column)
        if tok.kind == TokenKind.LPAREN:
            expr = self._parse_expression(PREC_OR)
            self._consume(TokenKind.RPAREN, "Expected ')' after grouped expression")
            return Grouping(expression=expr, line=tok.line, column=tok.column)
        raise self._error(tok, f"Unexpected token {self._render_token(tok)} in expression")

    def _finish_call(self, callee: Expr, lparen: Token) -> Expr:
        args: list[Expr] = []
        if not self._check(TokenKind.RPAREN):
            while True:
                args.append(self._parse_expression(PREC_OR))
                if not self._match(TokenKind.COMMA):
                    break
        self._consume(TokenKind.RPAREN, "Expected ')' after call arguments")
        return Call(callee=callee, arguments=args, line=lparen.line, column=lparen.column)

    def _infix_precedence(self, kind: TokenKind) -> int:
        if kind == TokenKind.LPAREN:
            return PREC_CALL
        if kind == TokenKind.OROR:
            return PREC_OR
        if kind == TokenKind.ANDAND:
            return PREC_AND
        if kind in (TokenKind.EQEQ, TokenKind.NEQ):
            return PREC_EQUALITY
        if kind in (TokenKind.LT, TokenKind.LTE, TokenKind.GT, TokenKind.GTE):
            return PREC_COMPARISON
        if kind in (TokenKind.PLUS, TokenKind.MINUS):
            return PREC_TERM
        if kind in (TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT):
            return PREC_FACTOR
        return PREC_NONE

    def _recover_for_clause(self, stop_at: TokenKind) -> None:
        while not self._at_end() and not self._check(stop_at) and not self._check(TokenKind.RPAREN):
            self._advance()

    def _synchronize(self) -> None:
        if self._at_end():
            return
        while not self._at_end():
            if self._previous().kind == TokenKind.SEMI:
                return
            if self._peek().kind in (
                TokenKind.LET,
                TokenKind.CONST,
                TokenKind.IF,
                TokenKind.WHILE,
                TokenKind.FOR,
                TokenKind.RBRACE,
            ):
                return
            self._advance()

    def _consume(self, kind: TokenKind, message: str) -> Token:
        if self._check(kind):
            return self._advance()
        raise self._error(self._peek(), message)

    def _error(self, token: Token, message: str) -> ParseError:
        diag = Diagnostic(
            code="PARSE-001",
            message=f"{message}, got {self._render_token(token)}",
            line=token.line,
            column=token.column,
        )
        self.diagnostics.append(diag)
        return ParseError(diag)

    def _render_token(self, token: Token) -> str:
        if token.kind == TokenKind.EOF:
            return "EOF"
        return token.lexeme or token.kind.name

    def _match(self, kind: TokenKind) -> bool:
        if self._check(kind):
            self._advance()
            return True
        return False

    def _check(self, kind: TokenKind) -> bool:
        if self._at_end():
            return kind == TokenKind.EOF
        return self._peek().kind == kind

    def _check_next(self, kind: TokenKind) -> bool:
        if self.index + 1 >= len(self.tokens):
            return False
        return self.tokens[self.index + 1].kind == kind

    def _advance(self) -> Token:
        if not self._at_end():
            self.index += 1
        return self._previous()

    def _peek(self) -> Token:
        return self.tokens[self.index]

    def _previous(self) -> Token:
        return self.tokens[self.index - 1]

    def _at_end(self) -> bool:
        return self._peek().kind == TokenKind.EOF


def parse(tokens: list[Token]) -> tuple[Program, list[Diagnostic]]:
    return Parser(tokens).parse()
