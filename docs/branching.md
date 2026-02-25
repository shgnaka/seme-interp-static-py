# seme Branching Strategy

This document defines the git branching rules for `seme-interp-static-py`.

## 1. Branch Structure

```
main (protected)
  └── develop (protected)
        ├── phase/1/lexer
        ├── phase/2/parser
        ├── phase/3/ast
        ├── phase/4/typechecker
        ├── phase/5/interpreter
        └── phase/6/cli
```

## 2. Branch Types

### 2.1 Main Branches (Protected)

- `main`: stable integration branch
- `develop`: day-to-day integration branch for MVP work

Rules:

- Do not force push
- Merge through normal merge flow only

### 2.2 Phase Branches (Long-lived)

Format:

```
phase/<N>/<component>
```

Examples:

- `phase/1/lexer`
- `phase/4/typechecker`

Rules:

- Create from `develop`
- Keep after merge (do not delete)
- Use as the parent for date branches

### 2.3 Date Branches (Daily Work Branches)

Format:

```
phase/<N>/<component>/<YYYY-MM-DD>
```

Example:

- `phase/1/lexer/2026-02-25`

Rules:

- Create from the matching phase branch at the start of a work day
- This is the default branch for all work on that day
- At the end of the day, you may:
  - merge it back into the phase branch, or
  - keep it unmerged and continue later

### 2.4 Task Branches (Optional, Short-lived)

Format:

```
phase/<N>/<component>/<YYYY-MM-DD>/<task-name>
```

Examples:

- `phase/1/lexer/2026-02-25/tokens`
- `phase/1/lexer/2026-02-25/keyword-scan`

Rules:

- Create only when a specific task is identified
- Create from the same day branch
- Merge back into the same day branch
- Delete after merge

## 3. Merge Direction Rules

- `task` -> `date`
- `date` -> `phase`
- `phase` -> `develop`
- `develop` -> `main`

Do not skip levels in normal workflow.

## 4. Daily Workflow

### 4.1 Start the day

```bash
git checkout phase/1/lexer
git pull
git checkout -b phase/1/lexer/2026-02-25
```

### 4.2 Optional: split out a specific task

```bash
git checkout -b phase/1/lexer/2026-02-25/tokens
# work + commits
git checkout phase/1/lexer/2026-02-25
git merge phase/1/lexer/2026-02-25/tokens
git branch -d phase/1/lexer/2026-02-25/tokens
```

### 4.3 End of day decision

Merge today branch:

```bash
git checkout phase/1/lexer
git merge phase/1/lexer/2026-02-25
```

Or keep it unmerged and continue another day:

```bash
git checkout phase/1/lexer/2026-02-25
```

## 5. Naming Rules

- Date format is always `YYYY-MM-DD`
- Use lowercase for task names
- Use `-` between words in task names
- Keep task names short and concrete (`tokens`, `if-parser`, `type-errors`)

## 6. Safety Rules

- Never rewrite `main` or `develop` history
- Keep commits small and frequent
- If you are unsure, branch from the date branch before trying risky changes
