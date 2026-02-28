from __future__ import annotations

from seme.diagnostics import Diagnostic
from seme.token import Token, TokenKind


KEYWORDS: dict[str, TokenKind] = {
    "let": TokenKind.LET,
    "const": TokenKind.CONST,
    "if": TokenKind.IF,
    "else": TokenKind.ELSE,
    "while": TokenKind.WHILE,
    "for": TokenKind.FOR,
}


class Lexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.length = len(source)
        self.index = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []
        self.diagnostics: list[Diagnostic] = []

    def lex(self) -> tuple[list[Token], list[Diagnostic]]:
        while not self._at_end():
            ch = self._peek()

            if ch in (" ", "\t", "\r"):
                self._advance()
                continue

            if ch == "\n":
                self._advance()
                continue

            if ch == "/" and self._peek_next() == "/":
                self._skip_line_comment()
                continue

            start_line = self.line
            start_col = self.column

            if ch.isalpha() or ch == "_":
                self._lex_identifier(start_line, start_col)
                continue

            if ch.isdigit():
                self._lex_int(start_line, start_col)
                continue

            if ch == '"':
                self._lex_string(start_line, start_col)
                continue

            if self._lex_operator_or_punctuator(start_line, start_col):
                continue

            bad = self._advance()
            self._diag("LEX-001", f"Invalid token '{bad}'", start_line, start_col)

        self.tokens.append(Token(TokenKind.EOF, "", self.line, self.column))
        return self.tokens, self.diagnostics

    def _lex_identifier(self, line: int, col: int) -> None:
        start = self.index
        while not self._at_end() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        lexeme = self.source[start:self.index]
        if lexeme in ("true", "false"):
            kind = TokenKind.BOOL_LIT
        else:
            kind = KEYWORDS.get(lexeme, TokenKind.IDENT)
        self.tokens.append(Token(kind, lexeme, line, col))

    def _lex_int(self, line: int, col: int) -> None:
        start = self.index
        while not self._at_end() and self._peek().isdigit():
            self._advance()
        self.tokens.append(Token(TokenKind.INT_LIT, self.source[start:self.index], line, col))

    def _lex_string(self, line: int, col: int) -> None:
        self._advance()  # opening quote
        start = self.index
        while not self._at_end() and self._peek() != '"' and self._peek() != "\n":
            self._advance()

        if self._at_end() or self._peek() == "\n":
            self._diag("LEX-001", "Unterminated string literal", line, col)
            return

        lexeme = self.source[start:self.index]
        self._advance()  # closing quote
        self.tokens.append(Token(TokenKind.STRING_LIT, lexeme, line, col))

    def _lex_operator_or_punctuator(self, line: int, col: int) -> bool:
        multi_ops = {
            "==": TokenKind.EQEQ,
            "!=": TokenKind.NEQ,
            "<=": TokenKind.LTE,
            ">=": TokenKind.GTE,
            "&&": TokenKind.ANDAND,
            "||": TokenKind.OROR,
        }
        two = self._peek() + self._peek_next()
        if two in multi_ops:
            self._advance()
            self._advance()
            self.tokens.append(Token(multi_ops[two], two, line, col))
            return True

        single = {
            "(": TokenKind.LPAREN,
            ")": TokenKind.RPAREN,
            "{": TokenKind.LBRACE,
            "}": TokenKind.RBRACE,
            ";": TokenKind.SEMI,
            ",": TokenKind.COMMA,
            ":": TokenKind.COLON,
            "=": TokenKind.ASSIGN,
            "+": TokenKind.PLUS,
            "-": TokenKind.MINUS,
            "*": TokenKind.STAR,
            "/": TokenKind.SLASH,
            "%": TokenKind.PERCENT,
            "<": TokenKind.LT,
            ">": TokenKind.GT,
            "!": TokenKind.BANG,
        }
        ch = self._peek()
        if ch in single:
            self._advance()
            self.tokens.append(Token(single[ch], ch, line, col))
            return True

        return False

    def _skip_line_comment(self) -> None:
        while not self._at_end() and self._peek() != "\n":
            self._advance()

    def _diag(self, code: str, message: str, line: int, column: int) -> None:
        self.diagnostics.append(Diagnostic(code=code, message=message, line=line, column=column))

    def _peek(self) -> str:
        if self._at_end():
            return "\0"
        return self.source[self.index]

    def _peek_next(self) -> str:
        if self.index + 1 >= self.length:
            return "\0"
        return self.source[self.index + 1]

    def _advance(self) -> str:
        ch = self.source[self.index]
        self.index += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _at_end(self) -> bool:
        return self.index >= self.length


def lex(source: str) -> tuple[list[Token], list[Diagnostic]]:
    return Lexer(source).lex()
