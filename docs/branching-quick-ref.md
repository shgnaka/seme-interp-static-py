# Branching Quick Reference

Use this as a copy-paste command sheet for daily work.

## 1) One-time setup from `develop`

```bash
git checkout develop
git checkout -b phase/1/lexer
git checkout develop
git checkout -b phase/2/parser
git checkout develop
git checkout -b phase/3/ast
git checkout develop
git checkout -b phase/4/typechecker
git checkout develop
git checkout -b phase/5/interpreter
git checkout develop
git checkout -b phase/6/cli
```

## 2) Start daily work (date branch)

```bash
git checkout phase/1/lexer
git pull
git checkout -b phase/1/lexer/2026-02-25
```

## 3) Optional task split from date branch

```bash
git checkout phase/1/lexer/2026-02-25
git checkout -b phase/1/lexer/2026-02-25/tokens
# work and commit
git checkout phase/1/lexer/2026-02-25
git merge phase/1/lexer/2026-02-25/tokens
git branch -d phase/1/lexer/2026-02-25/tokens
```

## 4) End-of-day choices

Merge date branch into phase branch:

```bash
git checkout phase/1/lexer
git merge phase/1/lexer/2026-02-25
```

Keep date branch unmerged for later:

```bash
git checkout phase/1/lexer/2026-02-25
```

## 5) Phase completion flow

```bash
git checkout develop
git merge phase/1/lexer
```

## 6) Naming templates

- Phase: `phase/<N>/<component>`
- Date: `phase/<N>/<component>/<YYYY-MM-DD>`
- Task: `phase/<N>/<component>/<YYYY-MM-DD>/<task-name>`

## 7) Merge direction

- `task -> date -> phase -> develop -> main`
