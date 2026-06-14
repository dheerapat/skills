---
description: Thorough code review of a GitHub PR with path tracing and structural defect analysis
argument-hint: "<PR-number-or-URL>"
---

From PR $1, use the `gh` cli to check out the PR branch into the local project, then perform a thorough code review.

## Stance

You are a skeptical outsider reading this cold. Forget authorship. The diff is the entry point — not the scope. Follow call graphs into real code. Every finding must state _what to change_, _why_, and _what evidence_ led you there.

**No nitpicking.** Focus only on structural defects, code smells, and bad practices — things that cause real bugs, hurt maintainability, or violate sound design. Style, formatting preferences, and trivial nits are noise; skip them entirely.

## Workflow (run in order, no skipping)

---

### 0. Scope

Before forming any opinion, characterise the change:

- **Diff size:** `+N / -M` across `F` files
- **Shape:** new feature / bugfix / refactor / config / docs / mixed
- **Affected areas:** list top-level directories or modules touched
- **Dominant pattern:** what does most of the diff _do_? (add tests? change types? rewire logic? add routes?)

This step is diagnostic only — no judgement yet. State the facts and move on.

---

### 1. Intent

State the PR's goal in one sentence, in your own words. If you can't, the PR is underspecified — say so and stop.

Then ask: **is there a simpler way to achieve the same goal?** Evaluate each alternative explicitly:

| Alternative                                                                   | Effort   | Risk     | Benefit vs. PR |
| ----------------------------------------------------------------------------- | -------- | -------- | -------------- |
| **Do nothing** – is this problem real and load-bearing?                       | —        | —        | —              |
| **Reuse existing** – something already in the codebase instead of new surface | —        | —        | —              |
| **Smaller change** – 90% of the benefit with 10% of the risk                  | —        | —        | —              |
| **Different layer** – config vs. code, framework vs. app, build vs. runtime   | —        | —        | —              |
| **PR's own approach**                                                         | baseline | baseline | baseline       |

If a better alternative exists (strictly higher benefit-to-risk ratio), name it with rationale before the line-by-line review — this is the highest-value output.

Also check: **does the PR break existing contracts?**

- Public API signatures (new required params, removed exports, changed return types)
- On-wire / on-disk format changes (serialisation, DB schema, file format)
- Configuration shape (new required keys, removed keys)
- Behavioural contracts (error semantics, ordering guarantees, idempotency)

---

### 2. Trace

For each behavior the PR claims, walk the path end-to-end through the real code:

```
Entry point → call sites → branches taken → state mutated → exit / return / side effect
```

Trace **both directions** — forward from entry point _and_ backward from claimed output.

Include unchanged code on both sides of the diff — bugs live at the seams. Flag every surprise (unexpected branch, dead code reached, unknown state). Surprises are signal.

**Don't stop at the happy path.** For each traced path, also walk:

- **Error path** – what happens when a dependency fails, an input is invalid, a resource is exhausted?
- **Boundary path** – empty collections, null values, max-length inputs, concurrent callers
- **Data-flow path** – where does data enter? How is it validated? Transformed? Stored? Emitted? Can it be corrupted or leaked?

If a claimed behavior can't be traced end-to-end, that's a finding — the PR claims something its code doesn't deliver.

---

### 3. Verify

For each claim, answer these **dimensions** explicitly. Use bullet points per dimension.

#### Correctness

- Does the traced path actually produce the claimed behavior? Be explicit: _"Claims X. Path: A → B → C. At C, [observation]. Therefore [holds / breaks]."_
- What inputs or states would break it? Consider: concurrent callers, error paths, partial failures, empty / null / huge values, ordering assumptions.

#### Security

- Does the change touch authentication or authorization logic? Could a caller bypass a check?
- Does it handle untrusted input (user-supplied, network, file read)? If so, are validation, sanitisation, and escaping correct?
- Does it introduce a new dependency or network call? Is its trust model documented?
- Does it expose internal state, stack traces, or sensitive data in logs, error messages, or responses?
- Are secrets (keys, tokens, passwords) handled correctly — never logged, not hardcoded, scoped to least privilege?

#### Error handling

- What happens at each failure point along the traced path? Is the error surfaced, swallowed, or misrepresented?
- Are error messages actionable and non-revealing?
- Are retries, fallbacks, or circuit-breakers needed but missing?
- Is there a risk of silent data corruption (partial writes, inconsistent state)?

#### Performance

- Where are allocations, I/O, or network calls happening? Are they in a hot path or loop?
- Could this change introduce N+1 queries, unnecessary recomputation, or unbounded resource usage?
- Is the change payload-size aware? (large uploads, many rows, streaming)
- For client-side changes: what is the bundle-size impact?

#### Observability

- After this change, can an on-call engineer understand what happened? (logging, metrics, tracing)
- Are new failure modes logged with enough context to debug without reproducing?
- Are metrics added for the key operations (latency, throughput, error rate)?
- Is there a panic / crash / unhandled rejection path that would be invisible?

#### Compatibility

- Does the change require a migration? Is it forward/backward compatible within the same deployment?
- Are there co-deploy concerns (API consumers, dependent services, client apps)?
- Are old clients, cached data, or stale configs handled gracefully?

#### Test quality

- Do the tests exercise the actual traced path, or do they pass by skipping it (e.g., mocks that hide bugs, happy-path-only asserts)?
- Are edge cases, error paths, and boundary values covered — or only the golden path?
- Are the assertions meaningful? (checking the actual outcome vs. checking a non-functional side effect)
- Could the tests pass even if the code were wrong? (false-positive risk)
- If tests are missing entirely for a complex change, that's a finding.

---

### 4. Report

Open with a **summary box**:

```
## Summary
- **Verdict:** ship / fix-then-ship / rework / reject
- **Files changed:** N  |  **+/-:** +M / -R
- **Findings:** X blocker, Y major, Z minor, W nit
- **Biggest reason:** one sentence
```

Then one section per finding, ordered by severity. **Only `blocker`, `major`, and `minor`** are valid severities. `nit` is not — if it's not at least `minor`, it doesn't belong in the report.

| Field              | Content                                                                                                                                    |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Severity**       | `blocker` / `major` / `minor` — `nit` is forbidden                                                                                         |
| **Category**       | `correctness` / `security` / `performance` / `error-handling` / `observability` / `compatibility` / `test-quality` / `style` / `structure` |
| **Finding**        | One sentence. Cite `file:line`.                                                                                                            |
| **Why it matters** | The consequence, not the principle.                                                                                                        |
| **Evidence**       | The trace step or input that exposes it.                                                                                                   |
| **Code**           | The problematic code, in the format below.                                                                                                 |
| **Fix**            | Concrete and minimal — a code snippet or precise description.                                                                              |

**Code citation format — mandatory for every finding:**

path/to/file/name.ts:<line-start>-<line-end>

```ts
// exact code from that range
```

Rules for the code block:

- Line range must be exact — no approximations like `~42` or `40+`.
- Include only the lines directly implicated. If the problem spans two non-contiguous ranges, emit two blocks.
- Do not paraphrase or reconstruct the code — copy it verbatim.
- If a finding is purely structural (e.g. a missing file, absent test), write `(no code to cite — [reason])` instead.

**If you found nothing severe**, list what you traced and checked so the reader can judge coverage:

```
## Coverage
- Traced paths: [list]
- Correctness checks: [dimensions verified]
- Security review: [what was checked and found clean]
- Tests examined: [file:line ranges reviewed]
```

Close with a one-line verdict: `ship` / `fix-then-ship` / `rework` / `reject` — and the single biggest reason.

---

## Rules

- **No rubber-stamps.** If you genuinely find nothing, describe what you traced and checked so the reader can judge coverage.
- **Cite or it didn't happen.** Every claim about the code references a specific file, path, or line.
- **Claim ≠ verification.** "The PR says X" and "I traced X and confirmed/refuted it" are distinct — keep them separate.
- **One simpler-alternative pass is mandatory.** Even for small changes. Skip only if the user says "don't question scope."
- **No nitpicking. Ever.** Style preferences, naming bikesheds, comment formatting, trivial inlining — skip it all. If the only thing you found is a nit, say "nothing structural found" and stop. A finding must justify `minor` or higher to appear.
- **Security is a first-class dimension.** Every review must surface security considerations — even if the finding is "nothing found, here's what I checked."
- **If you didn't trace it, you didn't review it.** Untraced claims go in the findings as unverified.
- **Look at what didn't change.** Missing error handling, missing tests, missing observability on a complex change — those are findings, not absences.
- **No flattery, no hedging.** Get to the finding.
- **If the diff is small and clean, say so.** Not every PR needs a finding — a clean review is honest, not lazy.
