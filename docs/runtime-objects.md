# seme Runtime Objects

この文書は Issue `#36` の設計メモであり、`seme` runtime における
heap-managed object の最小モデルを定義する。

## Goal

- 現在の immediate value (`SemeInt`, `SemeBool`, `SemeString`) と将来の
  heap object を明示的に区別できるようにする
- object identity と ownership の責務を runtime 側へ集約する
- `#35` の allocation helper と `#33` の GC hook 準備にそのまま使える
  土台を決める

## Non-Goals

- この段階で GC を実装すること
- すぐに全ての runtime value を heap object 化すること
- MVP 仕様にない compound value や user-defined function を導入すること

## Current Baseline

現状の runtime value は次の immediate value のみである。

- `SemeInt`
- `SemeBool`
- `SemeString`
- sentinel: `UNINITIALIZED`, `VOID`

これらは immutable で、Python object の寿命に実装上は乗っている。
一方で runtime 自身は heap ownership をまだ明示していない。

## Proposed Model

### 1. Value Split

runtime 上の値は次の 2 層に分ける。

- immediate value:
  `SemeInt`, `SemeBool` のように軽量でコピー可能な値
- heap object handle:
  runtime が所有する heap object を参照する値

当面は `int` と `bool` を immediate のまま維持し、
将来の拡張性を優先して `string` を最初の heap-managed 候補とする。

理由:

- 文字列は長さ可変で、将来 intern / concat / slice などの拡張点になりやすい
- `int` / `bool` は immediate のままの方が MVP 実装を保ちやすい
- object identity を導入する最初の対象として扱いやすい

### 2. Object Shape

heap object は runtime 所有の record として管理する。

最小構造:

- `object_id`: runtime 内で一意な識別子
- `kind`: object kind (`string` から開始)
- `payload`: kind ごとの実データ
- `marked` または同等の GC 用 flag を将来追加可能な形にする

公開 API からは Python の生オブジェクトではなく、
runtime value としての handle 経由で参照する。

### 3. Ownership Rules

object の生存は runtime が管理し、次の root から到達可能であることを前提にする。

- VM operand stack
- active frame locals
- global storage
- constant pool
- builtin 呼び出し中の一時引数

この root set は `#33` の GC hook でそのまま列挙対象になる。

### 4. Equality and Formatting

- immediate value 同士の equality は現行ルールを維持する
- heap object 同士は、kind ごとの value equality を基本にする
- object identity は runtime 内部では保持するが、
  MVP の言語仕様としては identity 比較演算子はまだ導入しない
- `print` や diagnostic 表示は object kind ごとの formatter に委譲する

つまり language surface では「文字列として等しいか」を維持しつつ、
runtime 内部では object identity を持てるようにする。

### 5. API Direction

`#35` で追加したい API の方向性は次のとおり。

- `allocate_string(value: str) -> RuntimeValue`
- `is_heap_object(value: RuntimeValue) -> bool`
- `object_kind(value: RuntimeValue) -> str | None`
- `format_runtime_value(value: RuntimeValue) -> str`
- `runtime_equal(...)` は heap object を含んでも backend 共通で動く
- execution state は `gc_root_values()` のような hook で root 値を列挙できる
- `RuntimeHeap.live_object_ids(...)` のような helper で後段の GC が参照集合を作れる

重要なのは allocation を runtime module / allocator API の背後に隠し、
他 module に ownership 詳細を漏らさないこと。

## Initial Rollout

導入順は次のとおり。

1. object handle 型と runtime-owned object table を定義する
2. string を object allocation API 経由で生成可能にする
3. formatting / equality helper を heap object 対応にする
4. root set 列挙 hook を追加する
5. compound value や closure はその後に載せる

## Design Constraints

- backend 間で object 表現は共有する
- compiler / VM / interpreter から Python の生 `str` を直接所有しない
- constant pool に heap object を置く場合も、ownership は chunk ではなく
  runtime が把握できる形に寄せる
- immediate value と object handle を混在させても `RUNTIME-001` の契約は崩さない

## Open Questions

- string literal を compile 時に object 化するか、runtime 開始時に materialize するか
- string interning を最初から入れるか、後段に回すか
- object handle を整数 id にするか、専用 dataclass にするか
- constant pool ownership を chunk と runtime のどちらが持つか

現時点では、専用 handle dataclass を使い、literal materialization は runtime 開始時に
寄せる案が保守しやすい。

## Exit Criteria

- heap-managed にする最初の対象が明確である
- stack value と heap object の責務分離が明確である
- formatting / equality / ownership の扱いが実装可能な粒度で整理されている
- `#35` と `#33` の前提が文書化されている
