# seme Implementation Playbook (MVP)

この文書は `docs/spec-mvp-local.md` を実装に落とすための手順書である。
実装中に仕様と食い違いが出た場合は、先に仕様側の更新要否を検討する。

## 0. Principles

- 実装順序は固定: `Lexer -> Parser -> AST -> TypeChecker -> Interpreter -> CLI`
- フェーズ完了条件（DoD）を満たすまで次に進まない
- 先に失敗ケース（診断）を定義してから実装する

## 1. Phase 1: Lexer

### Input / Output

- Input: source string
- Output: `Token[]`（各tokenに `kind`, `lexeme`, `line`, `column`）

### Must Support

- keyword / operator / punctuator / identifier / int / string / bool
- whitespaceと`//`コメントのスキップ
- `LEX-001` の生成

### Definition of Done

- 正常入力でtoken列が壊れない
- 不正文字で `LEX-001` を位置付きで返す

### Minimum Tests

- `let x = 1;`
- `if (true) { print(1); }`
- `@` を含む不正入力

## 2. Phase 2: Parser

### Input / Output

- Input: `Token[]`
- Output: `Program` AST

### Must Support

- `let/const`, 代入, 式文, `if/while/for`, block
- 優先順位付き式解析（Prattまたは同等）
- `PARSE-001` の生成

### Definition of Done

- EBNFで定義された全ステートメントをAST化できる
- 欠落セミコロン等で `PARSE-001` を返す

### Minimum Tests

- `let x = 1; x = x + 1;`
- `while (x < 10) { x = x + 1; }`
- `let x = 1`（セミコロン欠落）

## 3. Phase 3: AST and Core Types

### Required Nodes

- Stmt: `LetDecl`, `ConstDecl`, `Assign`, `If`, `While`, `For`, `Block`, `ExprStmt`
- Expr: `Binary`, `Unary`, `Literal`, `Identifier`, `Grouping`, `Call`（`print` 用）

### Must Fix Here

- ASTノードに位置情報を保持する
- 以降フェーズはASTを唯一の入力にする

### Definition of Done

- Parser出力ASTが型検査と実行に直接渡せる

## 4. Phase 4: Type Checker

### Input / Output

- Input: AST
- Output: `Diagnostic[]`（0件なら型検査成功）

### Must Support

- 型環境（スコープスタック）
- 局所型推論
- `TYPE-001`, `TYPE-002`, `TYPE-003`
- 演算子制約、代入型一致、条件式bool制約
- `const` 再代入禁止（`TYPE-004` を追加してもよい）

### Definition of Done

- 仕様の型規則違反を診断で検出できる
- 1件以上の型エラー時に実行フェーズに進まない

### Minimum Tests

- `let x;` -> `TYPE-001`
- `{ let x = 1; let x = 2; }` -> `TYPE-002`
- `x = 1;` -> `TYPE-003`
- `if (1) {}` -> 条件型エラー

## 5. Phase 5: Interpreter

### Input / Output

- Input: AST（型検査成功済み）
- Output: stdout文字列 / runtime diagnostics

### Must Support

- 式評価（算術・比較・等価・論理）
- スコープ管理
- `if/while/for`
- `print(expr)`
- `RUNTIME-001` の最小実装

### Definition of Done

- 正常系の例が期待stdoutを返す
- 実行時例外を `RUNTIME-001` に変換できる

### Minimum Tests

- ループでの加算
- 条件分岐
- `print` 出力

## 6. Phase 6: CLI

### Commands

- `seme run <file>`
- `seme check <file>`
- `seme repl`

### Contract

- `run`: lex/parse/type-check/eval
- `check`: lex/parse/type-check
- `repl`: 1行ステートメント評価
- 成功終了 `0`, 失敗終了 `1`

### Definition of Done

- 失敗時にstderrへ診断出力
- 成功時にstdoutのみ出力

## 7. Conformance-first Test Workflow

1. 仕様に沿ってJSONテストケースを作成
2. `check`系ケースを先に通す
3. `run`系ケースを追加
4. 診断は少なくとも `code`, `message`, `line`, `column` を比較

## 8. MVP Acceptance Checklist

- Lexer/Parser/TypeChecker/Interpreter/CLI の全DoD達成
- 必須診断コードが実装済み
- 成功/失敗ケースを継続実行できる
- 仕様未定義機能（Out of Scope）を誤って実装していない
