---
description: Scan a code area for tech debt, trace call sites, and identify dead code safe to delete
argument-hint: "<file-or-symbol>"
---

# Scan

Resolve `$1` (file, class/function, or module dir). Grep definitions, read the file, summarize public API + imports.

## 1. Tech Debt

Grep target + all referencing files (skip `node_modules`, `.git`, `dist`, `build`, `.next`, `out`).

Markers (case-insensitive): `TODO`, `FIXME`, `HACK`, `XXX`, `TEMP`, `OPTIMIZE`, `REVIEW`, `CLEANUP`, `WORKAROUND`

```
📄 <file>
  L<line>  <marker>  <message>  [actionable|stale]
```

Close: **`<N> debt markers found, <M> stale.`**

## 2. Call Sites

For each public symbol, grep invocations, imports, and instantiation across the codebase:

```
<symbol>
  Imports    →  <N> files
  Calls      →  <N> sites
  Instantiation → <N> (classes)
  Indirect   →  <N> (callbacks, collections)
```

Flag: only-test callers, recursive-only, dead branches, registered listeners with no emitter.

## 3. Dead Code

A symbol is dead if:

| Condition                                   | Verdict              |
|---------------------------------------------|----------------------|
| No callers anywhere                         | 🟢 Safe to delete   |
| Only in tests                               | 🟡 Production dead  |
| Recursive only / only from other dead code  | 🟢 Safe to delete   |
| Behind dead branches                        | 🟢 Safe to delete   |
| Listener but event never emitted            | 🟢 Safe to delete   |
| Live callers exist                          | 🔴 Keep             |

For listeners: grep the event name against `emit`, `dispatch`, `publish`, `next`, `trigger`, `send`. No emitter = dead.

**Deletion snippet** for each 🟢:

```
<symbol>  —  <reason>
  Defined:  <file:line>
  Delete:   definition + all references in <files>
```

Also flag: unused imports, dead branches (`if (false)`), unreachable code, orphaned exports.

## 4. Summary

```
## Scan: <target>
Tech Debt: <N> markers (<M> stale)
Call Sites: <S> symbols, <T> sites, <U> files
Dead Code: <D> safe to delete
  - <symbol> → <reason>
Recommendations:
  - <action>
```

Clean scan: `No debt, no dead code, all symbols live.`

---

## Rules

- Trace outward from target. Dead code hides in cross-file gaps.
- Skip: `node_modules`, `.git`, `dist`, `build`, `target`, `.next`, `out`, `__pycache__`, `.venv`
- Report only. Don't modify anything.
- Can't find target? Suggest alternatives.
- When in doubt → 🔴 Keep. False negatives break builds.
