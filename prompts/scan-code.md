---
description: Scan a code area for tech debt, trace call sites, and identify dead code safe to delete
argument-hint: "<file-or-symbol>"
---

Resolve `$1` (file, class/function, or module dir). Grep definitions, read the file, summarize public API + imports.

## 1. Tech Debt

Grep target + all referencing files (skip `node_modules`, `.git`, `dist`, `build`, `.next`, `out`).

Markers (case-insensitive): `TODO`, `FIXME`, `HACK`, `XXX`, `TEMP`, `OPTIMIZE`, `REVIEW`, `CLEANUP`, `WORKAROUND`

```
📄 <file>
  L<line>  <marker>  <message>  [actionable|stale]
```

Close: **`<N> debt markers found, <M> stale.`**

For each public symbol, also report direct callers for context:

```
<symbol>
  Imports    →  <N> files
  Calls      →  <N> sites
  Instantiation → <N> (classes)
  Indirect   →  <N> (callbacks, collections)
```

## 3. Dead Code (Root-Outward Reachability)

Don't just ask "does anything call this?" — ask "does anything **live** call this?" A function called only by other dead functions is itself dead.

### Step 1: Identify Roots

App entry points that are always live:
- `main()`, `index.*`, `App.*`, `app.*`
- Exported symbols from package entry (`exports` in `package.json`, barrel files)
- Registered routes (`router.get`, `app.post`, etc.)
- Registered event listeners (`on`, `addEventListener`, `subscribe`)
- Command handlers, middleware, plugin registrations
- Test-only roots (describe/it blocks) — separate bucket

### Step 2: Walk the Graph

From each root, transitively follow: calls, imports, instantiations, method references. Mark every reached symbol as **LIVE**.

### Step 3: Everything Unreached is Dead

| Condition                                            | Verdict              |
|------------------------------------------------------|----------------------|
| Never reached from any root                          | 🟢 Safe to delete   |
| Reached only from test roots                         | 🟡 Production dead  |
| Reached only from other 🟢 dead symbols             | 🟢 Safe to delete   |
| Behind dead branches (`if (false)`, unreachable)     | 🟢 Safe to delete   |
| Listener but event never emitted from live code      | 🟢 Safe to delete   |
| Reached from live root                               | 🔴 Keep             |

For listeners: grep event name against `emit`, `dispatch`, `publish`, `next`, `trigger`, `send`. Emitter exists in live code = live. No emitter or emitter is dead = dead.

### Deletion Snippet

For each 🟢:

```
<symbol>  —  <reason>
  Defined:   <file:line>
  Called by:  <caller> (also dead) | nobody
  Delete:    definition + all references in <files>
```

Also flag: unused imports, dead branches, unreachable code, orphaned exports.

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

## Rules

- Trace outward from target using root-outward reachability. Dead code hides in call chains where every caller is also dead.
- Skip: `node_modules`, `.git`, `dist`, `build`, `target`, `.next`, `out`, `__pycache__`, `.venv`
- Report only. Don't modify anything.
- Can't find target? Suggest alternatives.
- When in doubt → 🔴 Keep. False negatives break builds.
