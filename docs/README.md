# seme-interp-static-py docs

このディレクトリは、`seme-interp-static-py` のMVP実装を自己完結で進めるための文書セット。

## Getting Started

このリポジトリには `seme` CLI の定義が含まれているが、最初からシェルで
`seme` コマンドが使えるわけではない。通常のコマンドとして使いたい場合は、
リポジトリルートで開発用インストールを行う。

```bash
python3 -m pip install -e .
```

インストール後は次のように使える。

```bash
seme check hello.seme
seme run hello.seme
seme repl
```

インストールせずに試したい場合は、`src` を `PYTHONPATH` に追加して
Python から直接 CLI モジュールを起動する。

```bash
PYTHONPATH=src python3 -m seme.cli check hello.seme
PYTHONPATH=src python3 -m seme.cli run hello.seme
PYTHONPATH=src python3 -m seme.cli repl
```

`hello.seme` の例:

```text
print(1);
```

## Documents

- `docs/language-guide.md`: 開発原則と適用範囲の入口
- `docs/spec-mvp-local.md`: 実装判断の規範仕様
- `docs/implementation-playbook.md`: フェーズ別実装手順と受け入れ条件
- `docs/branching.md`: ブランチ運用ルール
- `docs/branching-quick-ref.md`: ブランチ運用クイックリファレンス

## Recommended Flow

1. `docs/language-guide.md` を読む
2. `docs/spec-mvp-local.md` で仕様を固定する
3. `docs/implementation-playbook.md` に従って実装する

## Quick Decisions

- 仕様曖昧時: `spec-mvp-local.md` を優先
- 実装順序: `implementation-playbook.md` のPhase順を厳守
- 仕様追加: MVP完了までは行わない
