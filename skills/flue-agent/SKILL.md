---
name: flue-agent
description: Create and manage Flue agents — a TypeScript framework for building AI agents with harness-driven architecture. Use when creating Flue projects, running npx flue commands, editing flue.config.ts or agent modules, writing defineAgent() code, or deploying Flue agents to Node.js/Cloudflare targets.
---

# Flue Agent Skill

Reference for building and running [Flue](https://flueframework.com) agents. Content sourced from the [quickstart guide](https://flueframework.com/docs/getting-started/quickstart/index.md).

## Update

To update this skill from the upstream quickstart:

```bash
curl -sL 'https://flueframework.com/docs/getting-started/quickstart/index.md'
```

Compare the fetched content against the reference sections below. Apply surgical edits — replace stale lines, add new steps, remove obsolete instructions. Do not reformat unchanged sections. If nothing material changed, say so and don't touch the file.

---

## Reference

### Prerequisites

- **Node.js** — `>=22.19.0` minimum required version
- **LLM** — At least one model specifier (e.g. `anthropic/claude-sonnet-4-6` or `cloudflare/@cf/moonshotai/kimi-k2.6`)
- **LLM Provider** — API key(s) for your model provider. Cloudflare provides built-in `cloudflare/*` model access, no API keys required
- **A coding agent (recommended)** — Several Flue features assume a coding agent available locally
- **A container sandbox (optional)** — Flue includes a built-in virtual sandbox. For a real VM, use a [container sandbox](https://flueframework.com/docs/ecosystem/#sandboxes)

### Quick setup (recommended)

Copy this prompt into a coding agent:

> Read https://flueframework.com/start.md then help create my first agent...

### Manual setup

#### 1. Install Flue

```bash
npm install @flue/runtime
npm install --save-dev @flue/cli
echo 'ANTHROPIC_API_KEY="your-api-key"' > .env
npx flue init --target node   # or: --target cloudflare
```

Add `.env` to `.gitignore`. Do not commit provider credentials. Any LLM provider Pi supports works — see [Pi's Providers docs](https://pi.dev/docs/latest/providers#api-keys).

#### 2. Create first agent module

Create `agents/<name>.ts`. The filename becomes the agent name.

```ts
import { defineAgent } from '@flue/runtime';

export default defineAgent(() => ({
    model: 'anthropic/claude-sonnet-4-6',
    instructions: 'Tell a funny "hello world" engineering joke.',
}));
```

#### 3. Run agent locally

```bash
npx flue run <agent-name> --input '{"message":"Tell me a joke."}'
```

Starts the configured runtime, invokes the agent, prints response, exits.

### Next steps

- [Deploy on Cloudflare](https://flueframework.com/docs/ecosystem/deploy/cloudflare/) — configure and run Workers
- [Agents](https://flueframework.com/docs/concepts/agents/) — continuing interactions
- [Workflows](https://flueframework.com/docs/guide/workflows/) — bounded operations around agents
- [Configuration](https://flueframework.com/docs/reference/configuration/) — targets and local behavior
- [Sandboxes](https://flueframework.com/docs/guide/sandboxes/) — execution capabilities

---

## Docs index

Full documentation tree from the Flue docs navigation.

### Sections

- [Guide](https://flueframework.com/docs/getting-started/quickstart/)
- [Reference](https://flueframework.com/docs/api/agent-api/)
- [CLI](https://flueframework.com/docs/cli/overview/)
- [SDK](https://flueframework.com/docs/sdk/overview/)
- [Ecosystem](https://flueframework.com/docs/ecosystem/)

### Introduction

- [Getting Started](https://flueframework.com/docs/getting-started/quickstart/)
- [Why Flue?](https://flueframework.com/docs/introduction/why-flue/)
- [What is an agent?](https://flueframework.com/docs/concepts/agents/)
- [Durable Agents](https://flueframework.com/docs/concepts/durable-execution/)
- [Changelog](https://github.com/withastro/flue/blob/main/CHANGELOG.md)

### Guides

- [Project Layout](https://flueframework.com/docs/guide/project-layout/)
- [Routing](https://flueframework.com/docs/guide/routing/)
- [Database](https://flueframework.com/docs/guide/database/)
- [Agents](https://flueframework.com/docs/guide/building-agents/)
- [Workflows](https://flueframework.com/docs/guide/workflows/)
- [Actions](https://flueframework.com/docs/guide/actions/)
- [LLM](https://flueframework.com/docs/guide/models/)
- [Tools](https://flueframework.com/docs/guide/tools/)
- [Skills](https://flueframework.com/docs/guide/skills/)
- [Subagents](https://flueframework.com/docs/guide/subagents/)
- [Sandboxes](https://flueframework.com/docs/guide/sandboxes/)
- [Schedules](https://flueframework.com/docs/guide/schedules/)
- [Channels](https://flueframework.com/docs/guide/channels/)
- [Evals](https://flueframework.com/docs/guide/evals/)
- [Observability](https://flueframework.com/docs/guide/observability/)

### Frontend

- [React](https://flueframework.com/docs/guide/react/)

### Targets

- [Cloudflare](https://flueframework.com/docs/guide/targets/cloudflare/)
- [Node.js](https://flueframework.com/docs/guide/targets/node/)
