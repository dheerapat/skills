---
name: flue-agent
description: Create and manage Flue agents — a TypeScript framework for building AI agents with harness-driven architecture. Use when creating Flue projects, running npx flue commands, editing flue.config.ts or agent modules, writing defineAgent() code, or deploying Flue agents to Node.js/Cloudflare targets.
---

# Flue Agent Skill

Reference for building and running [Flue](https://flueframework.com) agents. Content sourced from the [quickstart guide](https://flueframework.com/docs/getting-started/quickstart/index.md), last updated May 29, 2026.

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

### Automatic installation (recommended)

Copy this prompt into a coding agent:

> Read https://flueframework.com/start.md then help create my first agent...

The coding agent guides setup in a new or existing project and answers questions along the way.

### Manual setup

**Note:** The AI-guided prompt is recommended for most users. Follow the manual steps if you prefer to set things up yourself.

#### 1. Install Flue

In a new directory, install Flue and initialize your target. `flue init` creates `flue.config.ts`; add an agent module in the next step.

```bash
npm install @flue/runtime
npm install --save-dev @flue/cli
echo 'ANTHROPIC_API_KEY="your-api-key"' > .env
npx flue init --target node   # or: --target cloudflare
```

Add `.env` to `.gitignore`. Do not commit provider credentials. Any LLM provider Pi supports works — see [Pi's Providers docs](https://pi.dev/docs/latest/providers#api-keys).

#### 2. Create your first agent module

Create `agents/hello-world.ts`. The default export registers the agent, and the filename makes it available in Flue as `hello-world`.

```ts
import { defineAgent } from '@flue/runtime';

export default defineAgent(() => ({
    model: 'anthropic/claude-sonnet-4-6',
    instructions: 'Tell a funny "hello world" engineering joke.',
}));
```

You can choose any [supported model](https://pi.dev/models) and configure its provider credentials.

#### 3. Run your agent locally

```bash
npx flue run hello-world --input '{"message":"Tell me a joke."}'
```

The command starts your configured Node.js or Cloudflare runtime, invokes the agent through the application, prints its response, and exits.

From here, shape the agent's behavior, add capabilities, or deploy it as part of an application.

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
