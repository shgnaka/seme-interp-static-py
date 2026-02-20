# seme Language Development Guide (Local)

このガイドは、`seme-interp-static-py` だけを読んでMVPを実装するための入口文書である。

## 1. Goal

- 学習重視で、仕様ブレなくMVPを完成させる
- 実装は段階開発で進める
- 実装判断はローカル仕様を優先する

## 2. Read Order

1. `docs/spec-mvp-local.md`（何を実装するか）
2. `docs/implementation-playbook.md`（どう実装するか）
3. `docs/README.md`（導線確認）

## 3. Decision Rules

- 仕様とコードが矛盾したら、先に仕様を見直す
- 仕様外機能を追加しない
- エラーは診断コードと位置情報を必ず持たせる
- フェーズ完了条件を満たすまでは先に進まない

## 4. MVP Fixed Boundary

### Included

- `let/const`, `if/while/for`
- 式評価
- 静的型検査（ローカル推論）
- `run/check/repl`

### Excluded

- 関数定義・ユーザー定義関数呼び出し
- モジュール
- ジェネリクス
- 最適化/JIT

## 5. Repository-local Self-Containment Policy

- このリポジトリの `docs/` 配下だけで実装可能であることを維持する
- 外部仕様を参照する場合は、必要事項を `spec-mvp-local.md` に取り込む
- 新規参加者が1時間以内に着手できる文書密度を維持する

## 6. Next-phase Gate (Reference)

次フェーズ（関数導入）へ進むのは、以下達成後のみ:

- MVP受け入れ条件を満たす
- 診断コードが安定している
- Conformanceケースで回帰がない

詳細仕様は次フェーズ開始時に別途定義する。
