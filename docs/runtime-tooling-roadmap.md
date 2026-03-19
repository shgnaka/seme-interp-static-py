# seme Runtime Tooling and Observability Roadmap

この文書は Issue `#42` の追跡メモであり、`seme` runtime の安全性・観測性・
ツール群を別トラックとして整理する。

## Goal

- bytecode 実行の安全性と可観測性を runtime 機能として強化する
- validation / tracing / inspection / profiling / serialization を
  それぞれ独立した子 issue に分ける
- language surface の変更と runtime tooling を混線させない

## Non-Goals

- この段階で最適化や JIT を導入すること
- 言語仕様や AST/bytecode 命令セットを増やすこと
- 既存の `run` / `check` の契約を壊すこと

## Current Baseline

現状の runtime には次の要素がある。

- `src/seme/bytecode.py`: opcode, instruction, chunk, source map
- `src/seme/compiler.py`: AST から bytecode への変換
- `src/seme/vm.py`: stack-based execution と runtime diagnostics
- `src/seme/pipeline.py`: `vm` / `interpreter` の切り替え
- `src/seme/cli.py`: `run`, `check`, `repl`

また、`docs/bytecode-vm-plan.md` で VM 実行本体の作業はほぼ整理済みであり、
`#42` はその上に載る tooling を対象とする。

## Workstreams

### 1. Bytecode Safety

- bytecode chunk の validator を追加する
- validator を compile/run のどこで呼ぶかを決める
- invalid chunk を早期に失敗させる

### 2. Inspection Tools

- bytecode disassembler を追加する
- CLI から chunk を閲覧する debug entry point を追加する
- source map を見やすく表示できるようにする

### 3. Runtime Tracing

- VM execution trace hooks を追加する
- opcode step, stack effect, source location を観測可能にする
- tracing は通常実行の stdout/stderr 契約と分離する

### 4. Persistence and Cache

- bytecode serialization / deserialization を追加する
- build cache の層を検討する
- cache invalidation の単位を source / chunk / version で整理する

### 5. Profiling and Metrics

- runtime execution metrics を収集できるようにする
- profiling hooks を追加する
- 収集データの公開範囲を限定する
- `VMMetrics` のような集約型 summary を返せるようにする
- wall-clock duration, instruction count, peak depths, opcode counts を扱う

### 6. Diagnostics and Source Mapping

- source mapping の精度を runtime diagnostics に合わせて強化する
- validator / tracer / profiler が同じ source map を参照できるようにする
- future tooling にも流用できる共通表示を作る
- source location resolution の shared helper を導入する
- broken chunk や incomplete map でも安全な fallback を定義する

### 7. Optimization Primitives

- peephole optimization を bytecode レベルで導入する
- 現状は literal folding と dead stack churn の削減を行う post-pass として実装済み
- 最適化は tooling の安全性と分離して進める

## Child Issues

- Add a bytecode validator for seme chunks
- Integrate bytecode validation into compile/run execution flow
- Add a bytecode disassembler for seme
- Add VM execution tracing hooks
- Add CLI/debug entry points for bytecode inspection
- Add bytecode serialization and deserialization support
- Add a bytecode cache layer for seme builds
- Add runtime execution metrics and profiling hooks
- Add peephole optimization support for seme bytecode (implemented)
- Strengthen source mapping for bytecode/runtime diagnostics
- Add tests for validation, tracing, serialization, and tooling

## Suggested Order

1. validator
2. source map strengthening
3. disassembler and debug entry points
4. tracing hooks
5. serialization / cache
6. profiling / metrics
7. peephole optimization
8. tests for the above

## Testing Strategy

- unit: validator, disassembler, serializer, tracer
- integration: CLI debug entry points and compile/run validation flow
- parity: ensure observability features do not change execution stdout/stderr

## Exit Criteria

- runtime tooling work is split into focused issues
- validation and observability are scoped separately from language semantics
- source mapping and diagnostics are clearly shared across tools
- there is a clear path from bytecode inspection to runtime metrics
