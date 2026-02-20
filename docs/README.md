# seme-interp-static-py docs

このディレクトリは、`seme-interp-static-py` のMVP実装を自己完結で進めるための文書セット。

## Documents

- `docs/language-guide.md`: 開発原則と適用範囲の入口
- `docs/spec-mvp-local.md`: 実装判断の規範仕様
- `docs/implementation-playbook.md`: フェーズ別実装手順と受け入れ条件

## Recommended Flow

1. `docs/language-guide.md` を読む
2. `docs/spec-mvp-local.md` で仕様を固定する
3. `docs/implementation-playbook.md` に従って実装する

## Quick Decisions

- 仕様曖昧時: `spec-mvp-local.md` を優先
- 実装順序: `implementation-playbook.md` のPhase順を厳守
- 仕様追加: MVP完了までは行わない
