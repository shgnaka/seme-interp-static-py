# seme Bytecode/VM Execution Plan

この文書は Issue `#17` の実装計画であり、`seme` を AST 直接実行から
bytecode compile + VM run へ段階的に拡張するための方針を定義する。

## 1. Goals

- 現行パイプライン `lex -> parse -> type-check -> eval` に対し、
  `lex -> parse -> type-check -> compile -> vm-run` を追加する
- AST インタプリタは VM が機能同等になるまで参照実装として残す
- CLI 利用者の挙動を大きく崩さず、段階的に切り替え可能にする

## 2. Non-Goals

- JIT や最適化パスの導入
- 仕様外機能の追加
- MVP の型システムや構文の変更

## 3. Current Baseline

現状の `seme` は次の構成になっている。

- `src/seme/pipeline.py`: `run_check`, `run_execute` が AST interpreter を呼ぶ
- `src/seme/interpreter.py`: AST を直接評価する参照実装
- `tests/unit/test_interpreter.py`, `tests/unit/test_run_pipeline.py`,
  `tests/cli/test_run_cli.py`: 実行系の回帰テスト

bytecode 化では、型検査済み AST を入力として compiler が chunk を生成し、
VM が chunk を実行する。

## 4. Target Architecture

### 4.1 Execution Modes

- `interpreter`: 既存の AST evaluator
- `vm`: 新しい bytecode compiler + VM runtime

内部 API では execution mode を切り替え可能にして、
CLI の `run` は既定で `vm` を使う。`interpreter` は parity 比較と
移行中の参照実装として維持する。

### 4.2 Proposed Modules

- `src/seme/bytecode.py`: opcode, instruction, chunk, constant pool
- `src/seme/compiler.py`: AST -> bytecode 変換
- `src/seme/vm.py`: stack-based virtual machine
- `src/seme/pipeline.py`: compile/vm-run 統合と mode 切り替え

## 4.3 Initial Instruction Set

MVP で必要な opcode は次の通り。

| Opcode | Operands | Purpose |
| --- | --- | --- |
| `LOAD_CONST` | `const_index` | 定数プールから値を積む |
| `LOAD_UNINITIALIZED` | なし | 未初期化 local 用 sentinel を積む |
| `LOAD_LOCAL` | `slot` | local slot の値を積む |
| `STORE_LOCAL` | `slot` | local slot に値を書き戻す |
| `POP` | なし | スタックトップを捨てる |
| `POP_N` | `count` | block exit 時などに複数値を捨てる |
| `ADD` `SUB` `MUL` `DIV` `MOD` | なし | 整数演算 |
| `NEGATE` | なし | 単項 `-` |
| `NOT` | なし | 論理否定 |
| `EQUAL` `NOT_EQUAL` | なし | 同型比較 |
| `LESS` `LESS_EQUAL` `GREATER` `GREATER_EQUAL` | なし | 整数比較 |
| `JUMP` | `target_offset` | 無条件分岐 |
| `JUMP_IF_FALSE` | `target_offset` | 条件 false 時分岐 |
| `PRINT` | なし | 値を 1 行出力 |
| `RETURN` | なし | chunk 実行終了 |

補足:

- local 変数は compiler が slot 番号へ解決する
- `&&` と `||` は short-circuit を保つため jump 命令の組み合わせで表現する
- scope 終了時の local cleanup は `POP_N` で表現する

## 4.4 Chunk Format

chunk は次の 3 要素を持つ。

- `instructions`: opcode と operand 列
- `constants`: `SemeInt | SemeBool | SemeString` を格納する定数プール
- `source_map`: 各 instruction offset に対応する `line` / `column`

この形により compiler と VM は同じ実行単位を共有でき、runtime fault 発生時も
instruction pointer から元ソース位置を逆引きできる。

runtime value の詳細方針は `docs/runtime-values.md` を参照する。

## 5. Milestones

### 5.1 Issue `#18`: Instruction set and chunk format

- 命令セットを最小 MVP 構文に合わせて定義する
- 定数テーブル、命令列、ソース位置の保持方法を決める
- 診断やデバッグに必要な逆引き情報を持たせる

完了条件:

- int / bool / string の定数ロードを表現できる
- 変数 load/store、算術、比較、分岐、jump、print、return を表現できる
- 命令とソース位置の対応がテスト可能

### 5.2 Issue `#19`: Compiler scaffolding and labels

- compiler state, scope metadata, symbol slots を導入する
- 前方 jump のための label / patching utility を実装する
- 変数解決を VM 用 slot 番号へ写像できるようにする

完了条件:

- block/scope ごとのローカル変数数を追跡できる
- 未解決 jump を後から patch できる
- compiler 単体で chunk 生成の骨格がテスト可能

### 5.3 Issue `#20`: Expressions and basic statements

- literal, unary, binary, grouping, identifier を compile する
- `let`, `const`, assignment, expr stmt, `print` を compile する
- 型検査済み AST を前提に、VM 実行可能な chunk を生成する

完了条件:

- 直線的なプログラムが VM で実行できる
- 算術・比較・論理演算の結果が interpreter と一致する

### 5.4 Issue `#21`: Control-flow and blocks

- `if`, `while`, `for`, block を compile する
- block exit 時の slot cleanup を明示する
- loop back-edge と conditional jump を扱えるようにする

完了条件:

- 制御構文を含むサンプルが VM で実行できる
- スコープ境界をまたぐ変数解決が interpreter と一致する

### 5.5 Issue `#22`: Stack-based VM runtime

- operand stack, call-free frame model, locals storage を実装する
- opcode dispatch と runtime diagnostics を実装する
- `RUNTIME-001` の表現を既存 CLI 契約へ合わせる

完了条件:

- compiler が出した chunk を最後まで実行できる
- 実行時エラー時に位置付き診断を返せる

### 5.6 Issue `#23`: Pipeline and CLI integration

- `pipeline.py` に compile/vm-run 経路を追加する
- interpreter と vm の切替点を内部 API に導入する
- 必要であれば CLI に実験用 mode 切替を追加する

完了条件:

- `check` は従来どおり type-check まで
- `run` は mode に応じて interpreter または vm を使える
- 既存 CLI 契約を壊さない

### 5.7 Issue `#24`: Parity and focused tests

- bytecode chunk 単体テストを追加する
- VM 命令実行テストを追加する
- interpreter / vm parity テストを追加する

完了条件:

- 同じソースで interpreter と vm の stdout / diagnostics が一致する
- 主要 opcode と制御構文に回帰テストがある

## 6. Design Constraints

### 6.1 Type checker stays before compilation

compiler は型検査済み AST を前提とし、型規則の再検証は行わない。
これにより compiler/VM は runtime semantics に集中できる。

### 6.2 Source locations are first-class

既存 CLI は位置付き診断を前提にしているため、bytecode 命令から元ソース位置を
追跡できなければならない。各 instruction offset に line/column を結び付ける。

### 6.3 AST interpreter remains the oracle

移行中の正しさ判定は既存 interpreter を基準にする。
VM 実装中に仕様解釈が揺れた場合は `docs/spec-mvp-local.md` を優先し、
必要に応じて interpreter 側も揃えて修正する。

## 7. Testing Strategy

- unit:
  `bytecode.py`, `compiler.py`, `vm.py` の局所テスト
- integration:
  `pipeline.py` 経由で compile/vm-run を検証
- parity:
  同一ソースを interpreter と vm の両方で実行し、stdout/diagnostics を比較

優先ケース:

- 直線的な算術と代入
- `if/else`, `while`, `for`
- block shadowing
- `const` 再代入や不正 runtime の診断位置

## 8. Rollout Plan

1. bytecode 形式と compiler 基盤を追加する
2. 式と単純文を VM で動かす
3. 制御構文を VM へ拡張する
4. pipeline に mode 切替を入れる
5. parity テストで interpreter と比較する
6. 既定実行系を VM に切り替える

## 9. Exit Criteria for Closing Issue `#17`

- 本計画がリポジトリに追加されている
- 後続 Issue `#18` から `#24` の責務分割が明文化されている
- AST interpreter を残した段階的移行方針が明記されている
