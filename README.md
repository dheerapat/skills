# 🧠 Dheeto's Personal Skills & Prompts

A collection of [pi](https://pi.ai) skills, prompt templates, and reusable utilities for my coding workflow.

## 📦 Installation

```bash
# Add this skill repo
npx skills add https://github.com/dheerapat/skills --skill <skill>
```

## 🛠 3rd Party Skills

```bash
npx skills add https://github.com/elysiajs/skills --skill elysiajs
npx skills add https://bun.sh/docs
npx skills add https://github.com/oxc-project/oxc --skill migrate-oxlint
npx skills add https://github.com/oxc-project/oxc --skill migrate-oxfmt
npx skills add https://github.com/mattpocock/skills --skill tdd
npx skills add https://github.com/github/awesome-copilot --skill gh-cli
npx skills add https://github.com/dominikmartn/nothing-design-skill --skill nothing-design
npx skills add https://github.com/streamlit/agent-skills --skill developing-with-streamlit
npx skills add https://github.com/duckdb/duckdb-skills.git
```

## 📝 Prompt Templates (`prompts/`)

Type `/name` in pi's editor to invoke a template.

### Quick Reference

| Prompt | Arg | What it expects |
|---|---|---|
| **plan-first** | `$@` | **Everything** you type — the task description (e.g., `/plan-first refactor auth module`) |
| **scrutinize** | `$1` | **One PR number/URL** — the PR to review (e.g., `/scrutinize 42`) |
| **to-issue** | `$1` | **One thing** — the feature/task to break into issues (e.g., `/to-issue Dark Mode`) |
| **grill-me** | `$1` | **One topic** — the design/feature to grill you about (e.g., `/grill-me database schema`) |
| **grill-prd** | *(none)* | Starts an interactive PRD interview — no args needed |
| **grill-rfc** | *(none)* | Starts an interactive RFC interview — no args needed |
| **grill-user** | *(none)* | Starts a user research interview — no args needed |
| **handoff-chunk** | *(none)* | Breaks the current task into small handoff chunks — no args needed |
| **to-rfc** | *(none)* | Writes an RFC from your current shared understanding — no args needed |

> `$1` = single argument, `$@` = all remaining text, no var = purely interactive

### Detailed Descriptions

#### 🔍 **plan-first** — `/plan-first <task>`
Before writing any code, explore the codebase, then produce a plan and wait for approval. Uses `$@` so you can pass an entire task description.

#### 🧐 **scrutinize** — `/scrutinize <PR-number-or-URL>`
Fetches a PR via the `/gh-cli` skill and performs a thorough code review. Checks correctness, security, error handling, performance, observability, and test quality. Uses `/gh-cli` skill.

#### 🎯 **to-issue** — `/to-issue <feature>`
Break a feature/task into tracer bullet issues — thin vertical slices that cut through all integration layers. Generates issue files in `./issue/<task>/<issue>.md`.

#### 🗣️ **grill-me** — `/grill-me <topic>**
Relentless one-question-at-a-time interview about a design or feature, walking down every branch of the decision tree. Ends with a shared understanding summary.

#### 📄 **grill-prd** — `/grill-prd`
Structured interview to fully define a new feature, then outputs a complete PRD summary. Covers: Problem & goal, Users & scope, Functional & non-functional requirements, Dependencies & risks, Success metrics.

#### 🏗️ **grill-rfc** — `/grill-rfc**
Technical interview to define a refactor/improvement. Outputs a 4-section RFC: Need, Approach, Benefits, Competition/Alternatives.

#### 👤 **grill-user** — `/grill-user`
User research interview following **The Mom Test** methodology. Uncovers real behaviors, pains, and experiences. No solution pitching, no hypotheticals — only past behavior.

#### 🧩 **handoff-chunk** — `/handoff-chunk`
Breaks your current task into small, logical portions with `# HANDOFF:` markers. Hand off one chunk at a time — implement, say "next", repeat.

#### 📝 **to-rfc** — `/to-rfc`
Once you have a shared understanding of a proposal, writes a structured RFC file as `<task>-rfc.md`. Includes Need, Approach, Benefits, Competition/Alternatives sections.

## 📋 Templates

**`PROBLEM_STATEMENT.template.md`** — Problem statement format used in PRDs:
```
[user] experience [problem] when [context], which result in [negative outcome, impact]
```

## 📚 Skills (`skills/`)

| Skill | Description |
|---|---|
| **chrome-extension-capture** | Guide for building Chrome extension screenshot capture features |
| **tmux** | Tmux usage, commands, and configuration guide |

## 🔧 Additional Scripts

- [visual-explainer](https://github.com/nicobailon/visual-explainer) — generate visual diagrams to explain concepts
