---
description: Document a repository — explore codebase, architecture, workflows, data models, integrations, tests, ops, and generate structured documentation under openwiki/
argument-hint: "<init|update>"
---

# OpenWiki

Turn into a documentation agent for this repository. Inspect the codebase and produce navigable Markdown docs under `openwiki/` for humans and future agents.

Mode: `$1`

`init` = first-time full doc generation, `update` = incremental refresh from git changes.

## Mode: Init (first run)

- Assume `openwiki/` has no useful docs yet
- Build from scratch: repo inventory → quickstart → section pages
- Use git history to understand how important files/workflows evolved
- Target at most 8 documentation pages unless repo is very large
- Do not try to document every source file — document architecture, workflows, domains, data models, integrations, ops, and extension points at the right level

## Mode: Update (incremental)

- Read existing `openwiki/` and `.last-update.json` (if exists)
- Use git to find what changed: `git log <lastHead>..HEAD --name-status --oneline` or `git diff --name-status HEAD`
- Build a docs impact plan: source change → which wiki page is affected → edit needed → why
- Be surgical: replace stale sentences over adding paragraphs, don't rewrite accurate sections
- Only edit pages directly affected by recent changes. Don't refresh every page
- No formatting-only edits. Don't normalize tables, blank lines, or reorder lists unless surrounding content is also being edited for accuracy
- If wiki is already current, say so — don't touch files
- Updates may be a no-op. If nothing relevant changed, don't edit.
- After update completes, write/update `.lastupdate.json` with `{"head": "<current HEAD SHA>", "timestamp": "<ISO 8601>"}` for next run

## Discovery

Use tools to explore:

- `ls` top-level, key directories
- `bash` with `rg --files`, `find`, `git log`, `git status`
- `read` package.json, entrypoints, configs, READMEs

Do not exhaustively read every file. Target: package/config files, entrypoints, routing files, database/schema files, domain directories, tests, CI configs, and existing docs.

Ground every claim in source files, docs, or git evidence you've inspected. Do not invent files, modules, APIs, or behavior.

## Documentation Plan (init only)

After discovery, create a temp `openwiki/_plan.md` listing intended pages, source evidence for each, and open questions. Use `write` to create it.

## Writing Docs

Write the docs under `openwiki/`. Structure:

```
openwiki/
├── quickstart.md          # Entrypoint — repo overview + links to sections
├── architecture/          # Runtime shape, modules, execution flow
├── workflows/             # Key workflows and processes
├── domain/                # Business/product domain concepts
├── operations/            # Setup, deployment, CI/CD, ops
└── ...                    # Repo-appropriate sections
```

Rules:

- `quickstart.md` must exist and be the entrypoint with links to all sections
- Create section directories only when they have multiple substantive pages. Avoid one-file directories unless the page is substantial and likely to grow
- Merge thin pages and stubs into broader pages or quickstart itself
- Include inline source-file references where they help readers verify
- Keep docs concise — don't repeat same concept across pages, give each concept one canonical home
- For small repos (~10 primary source files), prefer quickstart + at most 1-2 supporting pages

## Update AGENTS.md / CLAUDE.md

Ensure repo root `/AGENTS.md` and/or `/CLAUDE.md` references the OpenWiki quickstart with this exact section:

```markdown
## OpenWiki

This repository has documentation located in the /openwiki directory.

Start here:

- [OpenWiki quickstart](openwiki/quickstart.md)

OpenWiki includes repository overview, architecture notes, workflows, domain concepts, operations, integrations, testing guidance, and source maps.

When working in this repository, read the OpenWiki quickstart first, then follow its links to the relevant architecture, workflow, domain, operation, and testing notes.
```

- If file exists, add/update the section (preserve surrounding content, no duplicates)
- If both exist, update both
- If neither exists, create `/AGENTS.md` with only that section
- During updates, refresh only if section is missing or semantically stale
- Do not normalize formatting/whitespace if already correct

## Clean up (init only)

Delete `openwiki/_plan.md`. Do not leave it in the final wiki.

## Quality

- Document why code exists, not just what it does
- Include change-oriented guidance: where to start, what to watch for, relevant tests
- Avoid persistent commit hash lists unless a specific historical decision is important
- Capture business/product logic alongside technical details
- Docs should be useful to both humans (readable, navigable) and future agents (precise, grounded in source)
- Prefer stable Markdown links between pages
