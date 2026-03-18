# seme Runtime Values

このメモは Issue `#31` の軽量な設計メモであり、`seme` 実行系が共有する
runtime value の最小方針を残す。

## Goal

- VM と AST interpreter が Python 組み込み値ではなく `seme` 所有の値表現を使う
- 値の表示、型判定、演算可否判定を共有 helper に集約する
- 未初期化値や statement-only な非値を sentinel で明示する

## Current Model

- `SemeInt`
- `SemeBool`
- `SemeString`
- `UNINITIALIZED`
- `VOID`

`RuntimeValue = SemeInt | SemeBool | SemeString` とし、
実行スタックや束縛には sentinel を含む `StackValue` を使う。

## Design Notes

- 値オブジェクトは immutable な dataclass とする
- `bool` と `int` の Python 上の継承関係に引きずられないよう、
  `SemeBool` と `SemeInt` は明示的に分離する
- bytecode constant pool にも runtime value をそのまま格納する
- `print` 表示は helper 経由で行い、`true` / `false` 表記を backend 間で一致させる
- runtime helper は型不一致やゼロ除算を backend 共通メッセージで報告できるようにする
- helper API は少なくとも「生成」「型判定」「safe conversion」「formatting」を公開する

## Backend Contract

- compiler は literal を runtime value に変換して constant pool へ入れる
- VM は stack/local 上で `StackValue` を扱う
- interpreter も束縛と式評価で同じ value/sentinel を使う
- backend ごとの責務は source location を付けて `RUNTIME-001` に変換するところまで

## Near-term Follow-up

- 文字列演算や将来の runtime value 種別を追加する場合もこの module を拡張点にする
- 必要なら今後、runtime helper API と fault 方針をさらに docs に昇格させる
