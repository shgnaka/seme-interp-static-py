# seme MVP Local Spec (v0.1)

この文書は `seme-interp-static-py` におけるMVP実装の規範仕様である。
このリポジトリで実装判断に迷った場合は、必ず本仕様を優先する。

## 0. Document Metadata

- Spec Version: `0.1.0`
- Language Version: `0.1.0`
- Status: `active`
- Last Updated: `2026-02-20`
- Owner: `seme-interp-static-py`

## 1. Scope

### 1.1 In Scope

- C/JS風構文
- AST直接インタプリタ
- `let` / `const`
- `if` / `while` / `for`
- 式評価
- 静的型検査（ローカル型推論）
- CLI: `seme run`, `seme check`, `seme repl`

### 1.2 Out of Scope

- モジュールシステム
- ジェネリクス
- 最適化コンパイラ/JIT
- 独自GC実装
- 文字列連結としての `+`

## 2. Lexical Specification

### 2.1 Tokens

- Keywords: `let`, `const`, `if`, `else`, `while`, `for`, `true`, `false`
- Punctuators: `(` `)` `{` `}` `;` `,` `:`
- Operators: `=` `+` `-` `*` `/` `%` `==` `!=` `<` `<=` `>` `>=` `&&` `||` `!`
- Literals: `INT_LIT`, `STRING_LIT`, `BOOL_LIT`
- Identifiers: `[A-Za-z_][A-Za-z0-9_]*`

### 2.2 Whitespace and Comments

- Whitespace: space/tab/newline
- Comment: `//` 行コメントのみ

### 2.3 Semicolon Policy

- 文末セミコロン `;` は必須
- 自動セミコロン挿入は未対応

## 3. Syntax (EBNF)

```ebnf
program      = { statement } ;

statement    = let_decl
             | const_decl
             | assign_stmt
             | if_stmt
             | while_stmt
             | for_stmt
             | block
             | expr_stmt ;

let_decl     = "let" identifier [ ":" type ] [ "=" expression ] ";" ;
const_decl   = "const" identifier [ ":" type ] "=" expression ";" ;
assign_stmt  = identifier "=" expression ";" ;
expr_stmt    = expression ";" ;
block        = "{" { statement } "}" ;

if_stmt      = "if" "(" expression ")" statement [ "else" statement ] ;
while_stmt   = "while" "(" expression ")" statement ;
for_stmt     = "for" "(" [ for_init ] ";" [ expression ] ";" [ expression ] ")" statement ;
for_init     = let_decl_no_semi | const_decl_no_semi | assign_no_semi | expression ;

let_decl_no_semi   = "let" identifier [ ":" type ] [ "=" expression ] ;
const_decl_no_semi = "const" identifier [ ":" type ] "=" expression ;
assign_no_semi     = identifier "=" expression ;

expression   = logical_or ;
logical_or   = logical_and { "||" logical_and } ;
logical_and  = equality { "&&" equality } ;
equality     = comparison { ( "==" | "!=" ) comparison } ;
comparison   = term { ( "<" | "<=" | ">" | ">=" ) term } ;
term         = factor { ( "+" | "-" ) factor } ;
factor       = unary { ( "*" | "/" | "%" ) unary } ;
unary        = ( "!" | "-" ) unary | primary ;
primary      = INT_LIT | STRING_LIT | "true" | "false" | identifier | "(" expression ")" ;

type         = "int" | "bool" | "string" ;
```

## 4. Operator Precedence

1. Unary: `!`, unary `-`
2. Multiplicative: `*`, `/`, `%`
3. Additive: `+`, `-`
4. Comparison: `<`, `<=`, `>`, `>=`
5. Equality: `==`, `!=`
6. Logical AND: `&&`
7. Logical OR: `||`

## 5. Type System

### 5.1 Built-in Types

- `int`
- `bool`
- `string`

### 5.2 Local Type Inference

- `let x = 1;` は `x: int`
- `let y = true;` は `y: bool`
- `let z = "a";` は `z: string`

### 5.3 Declaration Rules

- `let` は再代入可能
- `const` は再代入不可
- `let` は型注釈または初期化式のどちらか必須（両方なしは `TYPE-001`）
- `const` は初期化式が必須

### 5.4 Expression Constraints

- `+ - * / %` は `int x int -> int`
- `< <= > >=` は `int x int -> bool`
- `== !=` は同型同士のみ許可、結果 `bool`
- `&& || !` は `bool` のみ
- 代入は左右型一致が必須

### 5.5 Control-Flow Constraints

- `if` / `while` / `for` の条件式は `bool` 必須

### 5.6 Scope Rules

- ブロック単位レキシカルスコープ
- 同一ブロックで再宣言禁止（`TYPE-002`）
- 未宣言変数参照禁止（`TYPE-003`）

## 6. Runtime Semantics

- パイプライン: `lex -> parse -> type-check -> eval`
- 型エラーが1件でもあれば `eval` へ進まない
- 評価順序は左から右
- 環境はスコープスタックで管理
- `for` は `init -> condition -> body -> update` 順に評価
- 組み込み: `print(expr);` は評価結果を1行出力
- `print(expr)` は文としてのみ使用可能で、値を返さない

### 6.1 Exit Codes

- 成功: `0`
- 失敗（LEX/PARSE/TYPE/RUNTIME）: `1`

## 7. CLI Contract

- `seme run <file>`: 解析・型検査・実行
- `seme check <file>`: 解析・型検査のみ
- `seme repl`: 1行単位で評価（MVPでは単一行ステートメント）

### 7.1 I/O Contract

- stdout: `print` などのプログラム出力
- stderr: 診断メッセージ

## 8. Diagnostics

### 8.1 Diagnostic Shape

```txt
Diagnostic {
  code,
  message,
  line,
  column,
  suggestion?
}
```

### 8.2 Categories

- `LEX`
- `PARSE`
- `TYPE`
- `RUNTIME`

### 8.3 Code Convention

- 形式: `<CATEGORY>-<NNN>`
- 例: `TYPE-001`, `PARSE-001`

### 8.4 Mandatory MVP Codes

- `TYPE-001`: 型推論不能宣言（型注釈なし・初期化なし）
- `TYPE-002`: 同一スコープ再宣言
- `TYPE-003`: 未宣言変数参照
- `PARSE-001`: 文法エラー
- `LEX-001`: 不正トークン
- `RUNTIME-001`: 実行時エラー

## 9. Conformance Test Format (JSON)

```json
{
  "name": "case name",
  "source": "program source code",
  "expected_stdout": "",
  "expected_exit_code": 0,
  "expected_diagnostics": [],
  "note": "optional"
}
```

### 9.1 Required Fields

- `name` (string)
- `source` (string)
- `expected_stdout` (string)
- `expected_exit_code` (number)
- `expected_diagnostics` (array)
- `note` (string, optional)

### 9.2 Diagnostic Item

```json
{
  "code": "TYPE-001",
  "message": "...",
  "line": 1,
  "column": 5,
  "suggestion": "..."
}
```

## 10. Acceptance Criteria (MVP)

- `run/check/repl` が動作する
- `let/const`, `if/while/for`, 式評価が動作する
- 必須診断コードが位置情報付きで報告される
- 成功・失敗両方のConformanceケースを処理できる

## 11. Change Management

- 仕様変更時は `Spec Version` と更新日を更新する
- 互換性破壊がある変更は `major` を上げる
- 実装差分が発生した場合は先に仕様差分を判断する
