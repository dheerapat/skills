---
name: flue-agent
description: Create and manage Flue agents — a TypeScript framework for building AI agents with harness-driven architecture. Use when creating Flue projects, running npx flue commands, editing flue.config.ts or agent modules, writing defineAgent() code, or deploying Flue agents to Node.js/Cloudflare targets.
---

# Flue Framework Skill

Comprehensive knowledge base for **Flue** — the TypeScript framework for building autonomous AI agents and workflows. Flue uses a harness-driven architecture: define agents by filling a harness with instructions, tools, skills, sessions, and a sandbox, then point a model at it.

**Version reference:** v0.x (as of May–Jun 2026)
**Source:** https://flueframework.com/docs/
**Reference docs:** `./reference/` directory

______________________________________________________________________

## Table of Contents

1. [Core Concepts](#core-concepts)
1. [Getting Started](#getting-started)
1. [Project Layout](#project-layout)
1. [Agents](#agents)
1. [Workflows](#workflows)
1. [Actions](#actions)
1. [Tools](#tools)
1. [Skills](#skills)
1. [Subagents](#subagents)
1. [Sandboxes](#sandboxes)
1. [Models & Providers](#models--providers)
1. [Routing](#routing)
1. [Database](#database)
1. [Channels](#channels)
1. [Schedules](#schedules)
1. [Evals](#evals)
1. [Observability](#observability)
1. [React Frontend](#react-frontend)
1. [CLI Reference](#cli-reference)
1. [SDK Reference](#sdk-reference)
1. [Deployment Targets](#deployment-targets)
1. [Ecosystem](#ecosystem)

______________________________________________________________________

## Core Concepts

### Harness Architecture

An LLM alone is a "brain in a jar" — extraordinary at reasoning, no memory, no hands, no senses. Flue's core insight: **an agent = a model + a harness**.

The harness provides:

- **Filesystem** — so the agent keeps its work
- **Tools** — so the agent acts, not just describes
- **Sandbox** — safe execution boundary
- **Context** — sharp across long work
- **Subagents** — multi-tasking

```ts
import { defineAgent } from '@flue/runtime';
import { local } from '@flue/runtime/node';

export default defineAgent(() => ({
  model: 'anthropic/claude-sonnet-4-6',
  instructions,  // who the agent is and how it works
  tools,         // what it can do
  skills,        // expertise it can load on demand
  sandbox: local(), // where it runs, safely
}));
```

### Design Principles

1. **Harness-first** — fill a harness with context, point a model at it, no scripting required.
1. **Open by default** — open models, sandboxes, deploys. No lock-in.
1. **AI-first** — designed to be used with your coding agent (Claude Code, Codex, etc.).

### Headless Agents

A Flue agent is **programmable** (you assemble and drive it in code) and **headless** (no CLI/chat UI of its own). You call agents from your own code, via HTTP, or through application-owned dispatch.

______________________________________________________________________

## Getting Started

### Prerequisites

- **Node.js** `>=22.19.0`
- **LLM** — model specifier (e.g., `anthropic/claude-sonnet-4-6`)
- **API key** for your chosen provider

### Quick Install

```bash
mkdir my-agent && cd my-agent
npm install @flue/runtime
npm install --save-dev @flue/cli
echo 'ANTHROPIC_API_KEY="your-api-key"' > .env
npx flue init --target node  # or: --target cloudflare
```

Add `.env` to `.gitignore`.

### First Agent

Create `src/agents/hello-world.ts` (or `.flue/agents/` for `.flue` layout):

```ts
import { defineAgent } from '@flue/runtime';

export default defineAgent(() => ({
  model: 'anthropic/claude-sonnet-4-6',
  instructions: 'Tell a funny "hello world" engineering joke.',
}));
```

### Run It

```bash
npx flue run hello-world --input '{"message":"Tell me a joke."}'
```

______________________________________________________________________

## Project Layout

Flue discovers entrypoints from one source directory (first-existing wins):

1. `.flue/` — self-contained Flue area in a larger app
1. `src/` — **recommended** for new projects
1. Project root — compact layout

### Files and Directories

| Path            | Purpose                                            | Docs       |
| --------------- | -------------------------------------------------- | ---------- |
| `app.ts`        | Optional custom HTTP entrypoint (Hono app)         | Routing    |
| `db.ts`         | Optional Node.js persistence adapter               | Database   |
| `cloudflare.ts` | Cloudflare-only Worker exports & non-HTTP handlers | Cloudflare |
| `agents/`       | Addressable agents (filename = agent name)         | Agents     |
| `workflows/`    | Finite operations (filename = workflow name)       | Workflows  |
| `channels/`     | Provider HTTP integrations                         | Channels   |

### Source Directory Rules

- Flue does **not** merge layouts — only one source directory discovered
- Nested files inside `agents/`, `workflows/`, `channels/` are NOT discovered
- Use `lower-kebab-case` filenames for portability

### Output Directory

`dist/` is default. Configure in `flue.config.ts`:

```ts
import { defineConfig } from '@flue/cli/config';

export default defineConfig({
  output: './build',
});
```

Full reference: `./reference/docs_guide_project-layout_index.md`

______________________________________________________________________

## Agents

### Creating an Agent

File in `src/agents/<name>.ts` with a default export from `defineAgent(...)`:

```ts
import { defineAgent, type AgentRouteHandler } from '@flue/runtime';

export const description = 'Tells a short joke in response to each message.';

export const route: AgentRouteHandler = async (_c, next) => next();

export default defineAgent(() => ({
  model: 'anthropic/claude-haiku-4-5',
  instructions: 'Tell a short joke in response to each message.',
}));
```

### Agent Configuration

The object returned by `defineAgent(...)` defines:

| Field           | Type             | Description                    |
| --------------- | ---------------- | ------------------------------ |
| `model`         | string           | Model specifier (required)     |
| `instructions`  | string           | System prompt / instructions   |
| `tools`         | ToolDefinition[] | Custom tools                   |
| `skills`        | SkillReference[] | Agent Skills                   |
| `actions`       | Action[]         | Finite agent-backed operations |
| `subagents`     | AgentProfile[]   | Named delegation targets       |
| `sandbox`       | SandboxFactory   | Execution environment          |
| `cwd`           | string           | Working directory              |
| `profile`       | AgentProfile     | Reusable behavior profile      |
| `thinkingLevel` | string           | Reasoning effort level         |

### Agent Profiles

Reusable behavior without creating a public agent:

```ts
import { defineAgent, defineAgentProfile } from '@flue/runtime';

const support = defineAgentProfile({
  model: 'anthropic/claude-haiku-4-5',
  instructions: 'Answer customer support questions clearly.',
  tools: supportTools,
});

export default defineAgent(() => ({
  profile: support,
}));
```

Profile fields can be overridden by `defineAgent(...)`.

### Agent ID

Each agent instance identified by `id`. Passed to `defineAgent(({ id }) => ...)` for resource scoping.

```text
POST /agents/support-assistant/ticket-8472
                               └── id ──┘
```

### Interaction

- **HTTP**: `POST /agents/<name>/<id>` with `{ "message": "...", "images": [...] }`
- **`dispatch()`**: Asynchronous input from application code
- **`route` export**: Controls HTTP access (middleware pattern)

### `dispatch()`

```ts
import { dispatch } from '@flue/runtime';
import supportAssistant from './agents/support-assistant.ts';

const receipt = await dispatch(supportAssistant, {
  id: event.ticketId,
  input: { type: 'support.comment.created', text: event.text },
});
```

Full reference: `./reference/docs_guide_building-agents_index.md`

______________________________________________________________________

## Workflows

Workflows are **finite, inspectable operations** with a single run, result, and event history.

### Create a Workflow

File in `src/workflows/<name>.ts`:

```ts
import { defineAgent, defineWorkflow } from '@flue/runtime';
import * as v from 'valibot';

export default defineWorkflow({
  agent: defineAgent(() => ({ model: 'anthropic/claude-haiku-4-5' })),
  input: v.object({ text: v.string() }),
  output: v.object({ summary: v.string() }),

  async run({ harness, input }) {
    const session = await harness.session();
    const response = await session.prompt(input.text);
    return { summary: response.text };
  },
});
```

### Using an Action

```ts
import { defineAgent, defineWorkflow } from '@flue/runtime';
import { summarize } from '../actions/summarize.ts';

export default defineWorkflow({
  agent: defineAgent(() => ({ model: 'anthropic/claude-haiku-4-5' })),
  action: summarize,  // owns input, output, handler
});
```

### Invoking

- **CLI**: `npx flue run summarize --input '{"text":"..."}'`
- **Code**: `invoke(workflow, { input: { ... } })`
- **HTTP**: With `route` export, at `POST /workflows/<name>`

### HTTP Exposure

Two independent exports:

```ts
import type { WorkflowRouteHandler, WorkflowRunsHandler } from '@flue/runtime';

export const route: WorkflowRouteHandler = async (c, next) => { /* auth */ await next(); };
export const runs: WorkflowRunsHandler = async (c, next) => { /* auth */ await next(); };
```

- `route` — controls invocation at `POST /workflows/<name>`
- `runs` — controls run inspection at `/runs/<runId>`

Full reference: `./reference/docs_guide_workflows_index.md`

______________________________________________________________________

## Actions

Actions are reusable logic that orchestrates an agent harness in a deterministic way.

### Define

```ts
import { defineAction } from '@flue/runtime';
import * as v from 'valibot';

export const summarize = defineAction({
  name: 'summarize_document',
  description: 'Summarize a document clearly.',
  input: v.object({ text: v.string() }),
  output: v.object({ summary: v.string() }),

  async run({ harness, input, log }) {
    const session = await harness.session();
    const response = await session.prompt(`Summarize:\n\n${input.text}`);
    return { summary: response.text };
  },
});
```

### Usage

- **In workflows**: Bind via `action: summarize` in `defineWorkflow`
- **In agents**: Add to `actions: [summarize]` in `defineAgent`

Actions share the model-facing namespace with tools, so every active capability needs a distinct name.

Full reference: `./reference/docs_guide_actions_index.md`

______________________________________________________________________

## Tools

Tools let agents retrieve information or perform actions. Use `defineTool(...)`.

### Define

```ts
import { defineTool } from '@flue/runtime';
import * as v from 'valibot';

export const lookupOrderStatus = defineTool({
  name: 'lookup_order_status',
  description: 'Look up fulfillment status for one order ID.',
  input: v.object({ orderId: v.string() }),
  output: v.object({ status: v.nullable(v.string()) }),
  async run({ input, signal }) {
    const status = await db.getOrderStatus(input.orderId);
    return { status };
  },
});
```

### Tool Security

Model-selected parameters are NOT an authorization boundary. Use the agent `id` to scope access:

```ts
export default defineAgent(({ id: customerId }) => ({
  tools: [defineTool({
    name: 'lookup_customer_order',
    async run({ input }) {
      const status = await orders.getStatus(customerId, input.orderId); // scoped
      return status;
    },
  })],
}));
```

### MCP Servers

```ts
import { connectMcpServer } from '@flue/runtime';

const inventory = await connectMcpServer('inventory', {
  url: process.env.INVENTORY_MCP_URL!,
  headers: { Authorization: `Bearer ${process.env.INVENTORY_MCP_TOKEN}` },
});

// Tools become available as inventory.tools
// MCP tool names get prefixed: mcp__inventory__lookup_item
```

Full reference: `./reference/docs_guide_tools_index.md`

______________________________________________________________________

## Skills

Flue supports [Agent Skills](https://agentskills.io/specification): reusable instructions + supporting resources.

### Adding a Skill

Directory structure:

```
src/skills/review/
├── SKILL.md
└── references/
    └── checklist.md
```

### Import

```ts
import { defineAgent } from '@flue/runtime';
import review from '../skills/review/SKILL.md' with { type: 'skill' };

export default defineAgent(() => ({
  model: 'anthropic/claude-sonnet-4-6',
  skills: [review],
}));
```

### Workspace Discovery

Skills under `<cwd>/.agents/skills/` are auto-discovered without imports.

### Invoking

In workflows, use `session.skill(name, { args, result })`:

```ts
const response = await (await harness.session()).skill('review', {
  args: { change: input.change },
  result: v.object({ approved: v.boolean(), summary: v.string() }),
});
```

### SKILL.md Frontmatter

| Field           | Required | Notes                         |
| --------------- | -------- | ----------------------------- |
| `name`          | Yes      | lowercase, hyphens, ≤64 chars |
| `description`   | Yes      | ≤1024 chars                   |
| `license`       | No       | Informational                 |
| `compatibility` | No       | ≤500 chars                    |
| `metadata`      | No       | string-to-string map          |
| `allowed-tools` | No       | Accepted, not enforced        |

Full reference: `./reference/docs_guide_skills_index.md`

______________________________________________________________________

## Subagents

Subagents let an agent delegate focused work to a named specialist.

### Define

```ts
import { defineAgent, defineAgentProfile } from '@flue/runtime';

const issueClassifier = defineAgentProfile({
  name: 'issue_classifier',
  description: 'Classifies support issues for routing.',
  instructions: 'Return the likely product area and urgency.',
});

export default defineAgent(() => ({
  model: 'anthropic/claude-sonnet-4-6',
  subagents: [issueClassifier],
}));
```

### Inheritance Rules

| Field                                          | Behavior                                 |
| ---------------------------------------------- | ---------------------------------------- |
| `instructions`, `tools`, `skills`, `subagents` | Profile-owned. Omitted = none.           |
| `model`, `thinkingLevel`                       | Inherits from parent as default          |
| `durability`                                   | Rejected — delegation runs inside parent |

### Programmatic Task

```ts
const response = await (await harness.session()).task(input.change, {
  agent: 'reviewer',
  result: Review,
});
```

Full reference: `./reference/docs_guide_subagents_index.md`

______________________________________________________________________

## Sandboxes

Sandboxes give agents a workspace to read, write, and run commands.

### Virtual Sandbox (Default)

- Lightweight, in-memory workspace via [just-bash](https://justbash.dev/)
- No `sandbox` field needed
- Data lost after execution
- Not a network isolation boundary

### Local Sandbox (Node.js only)

```ts
import { defineAgent } from '@flue/runtime';
import { local } from '@flue/runtime/node';

export default defineAgent(() => ({
  model: 'anthropic/claude-sonnet-4-6',
  sandbox: local(),
  cwd: '/srv/checkouts/catalog-service',
}));
```

- Direct host filesystem and shell access
- Environment variables deliberately limited
- Use only in trusted environments

### Remote Sandboxes

For isolation, Linux toolchain, or provider-managed workspaces. Integrations: Daytona, E2B, Modal, Cloudflare Sandbox, Vercel Sandbox, etc.

Full reference: `./reference/docs_guide_sandboxes_index.md`

______________________________________________________________________

## Models & Providers

### Model Specifier

Format: `<provider-id>/<model-id>`

| Specifier                             | Provider   | Model                    |
| ------------------------------------- | ---------- | ------------------------ |
| `anthropic/claude-sonnet-4-6`         | anthropic  | claude-sonnet-4-6        |
| `openai/gpt-5.5`                      | openai     | gpt-5.5                  |
| `cloudflare/@cf/moonshotai/kimi-k2.6` | cloudflare | @cf/moonshotai/kimi-k2.6 |

### Reasoning Effort (`thinkingLevel`)

| Value       | Intent                  |
| ----------- | ----------------------- |
| `'off'`     | No additional reasoning |
| `'minimal'` | Smallest effort         |
| `'low'`     | Lower cost/latency      |
| `'medium'`  | Default balance         |
| `'high'`    | More careful reasoning  |
| `'xhigh'`   | Highest exposed tier    |

### Built-in Providers

| Provider   | Env Variable         |
| ---------- | -------------------- |
| anthropic  | `ANTHROPIC_API_KEY`  |
| openai     | `OPENAI_API_KEY`     |
| openrouter | `OPENROUTER_API_KEY` |

### Custom/Override Providers

```ts
import { registerProvider } from '@flue/runtime';

// Override existing provider (e.g., AI gateway)
registerProvider('anthropic', {
  baseUrl: process.env.ANTHROPIC_GATEWAY_URL,
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// Register custom provider
registerProvider('ollama', {
  api: 'openai-completions',
  baseUrl: 'http://localhost:11434/v1',
});
```

Full reference: `./reference/docs_guide_models_index.md`

______________________________________________________________________

## Routing

`src/app.ts` is an optional Hono application entrypoint for custom HTTP routing.

### Basic Usage

```ts
import { flue } from '@flue/runtime/routing';
import { Hono, type MiddlewareHandler } from 'hono';
import { authenticate } from './auth.ts';

const requireUser: MiddlewareHandler = async (c, next) => {
  const user = await authenticate(c.req.raw);
  if (!user) return c.json({ error: 'Unauthorized' }, 401);
  await next();
};

const app = new Hono();

app.get('/health', (c) => c.json({ ok: true }));
app.use('/agents/*', requireUser);
app.use('/workflows/*', requireUser);
app.route('/', flue());

export default app;
```

### Mount Prefix

```ts
app.route('/api', flue());  // /api/agents/..., /api/workflows/...
```

### Workflow Run Authorization

```ts
export const runs: WorkflowRunsHandler = async (c, next) => {
  const token = c.req.header('authorization');
  if (!(await verifyRunToken(token))) return c.json({ error: 'Not found' }, 404);
  await next();
};
```

Full reference: `./reference/docs_guide_routing_index.md`

______________________________________________________________________

## Database

Flue stores canonical conversation streams, attachments, submissions, and workflow-run records.

### Node.js

```ts
import { sqlite } from '@flue/runtime/node';

export default sqlite('./data/flue.db');  // file-backed
// export default sqlite();              // in-memory
```

Postgres adapter: `@flue/postgres`

```ts
import { postgres } from '@flue/postgres';
export default postgres(process.env.DATABASE_URL!);
```

### Cloudflare

Durable Objects use SQLite automatically. No `db.ts` — Cloudflare builds reject it.

### What's Stored

| Stored                     | Not Stored            |
| -------------------------- | --------------------- |
| Agent conversation streams | Sandbox files         |
| Attachments                | External side effects |
| Submissions                | Business data         |
| Workflow runs & events     | Provider credentials  |

Full reference: `./reference/docs_guide_database_index.md`

______________________________________________________________________

## Channels

Channels bring provider HTTP events (Slack, GitHub, Stripe, etc.) into Flue.

### Adding a Channel

```bash
flue add channel slack --print | codex
```

### Channel Module

```ts
import { createSlackChannel } from '@flue/slack';
import { WebClient } from '@slack/web-api';

export const client = new WebClient(process.env.SLACK_BOT_TOKEN);

export const channel = createSlackChannel({
  signingSecret: process.env.SLACK_SIGNING_SECRET!,
  async events({ payload }) {
    if (payload.type !== 'event_callback') return;
    // Handle event
  },
});
```

### Ownership Boundary

| Concern                             | Owner           |
| ----------------------------------- | --------------- |
| Request verification                | Channel package |
| Provider SDK & outbound credentials | Application     |
| Agent tools & auth policy           | Application     |

### File-Based Routing

```
src/channels/github.ts -> /channels/github/webhook
src/channels/slack.ts  -> /channels/slack/events
                           /channels/slack/interactions
```

Full reference: `./reference/docs_guide_channels_index.md`

______________________________________________________________________

## Schedules

Schedules invoke workflows or dispatch agent input on a timer.

### Cloudflare Cron

```jsonc
// wrangler.jsonc
{ "triggers": { "crons": ["0 9 * * *"] } }
```

```ts
// src/cloudflare.ts
import { invoke } from '@flue/runtime';
import dailySummary from './workflows/daily-summary.ts';

export default {
  async scheduled(controller: ScheduledController) {
    await invoke(dailySummary, { input: { prompt: '...' } });
  },
};
```

### Node.js (using Croner)

```ts
import { Cron } from 'croner';

new Cron('0 9 * * *', { protect: true }, async () => {
  await invoke(dailySummary, { input: { prompt: '...' } });
});
```

### Dispatch to Agent

```ts
import { dispatch } from '@flue/runtime';
import dailySummary from './agents/daily-summary.ts';

await dispatch(dailySummary, {
  id: 'daily-summary',
  input: { type: 'schedule', scheduledAt: new Date().toISOString() },
});
```

Full reference: `./reference/docs_guide_schedules_index.md`

______________________________________________________________________

## Evals

Use [vitest-evals](https://vitest-evals.sentry.dev/docs) for repeatable agent evaluation.

### Setup

```bash
flue add tooling vitest-evals
```

### Write an Eval

```ts
import { describeEval, toolCalls } from 'vitest-evals';
import { createFlueAgentHarness } from './harness.ts';

const harness = createFlueAgentHarness({ agentName: 'service-status' });

describeEval('Service status agent', { harness }, (it) => {
  it('checks live status before answering', async ({ run }) => {
    const result = await run('Is checkout operational?');
    expect(result.output).toContain('operational');
    expect(toolCalls(result).map(c => c.name)).toContain('get_service_status');
  });
});
```

### Run

```bash
pnpm exec flue dev    # terminal 1
pnpm run evals        # terminal 2
```

Full reference: `./reference/docs_guide_evals_index.md`

______________________________________________________________________

## Observability

### Inspect Workflow Runs

Use `log.info/warn/error` in Actions:

```ts
async run({ harness, log, input }) {
  log.info('Summarization requested', { characters: input.text.length });
  // ...
  log.info('Completed', { tokens: response.usage.totalTokens });
}
```

### Observe Application Activity

```ts
import { observe } from '@flue/runtime';

observe((event) => {
  if (event.type === 'run_end' && event.isError) {
    console.error('Workflow failed', event.runId, event.error);
  }
  if (event.type === 'operation' && event.durationMs > 5000) {
    console.warn('Slow operation', event.operationKind, event.durationMs);
  }
});
```

### Providers

| Provider      | Use When                                  |
| ------------- | ----------------------------------------- |
| OpenTelemetry | Vendor-neutral traces                     |
| Braintrust    | Content-bearing traces + costs            |
| Sentry        | Actionable failures without model content |

Full reference: `./reference/docs_guide_observability_index.md`

______________________________________________________________________

## React Frontend

`@flue/react` turns durable event streams into React state.

### Setup

```tsx
import { FlueProvider } from '@flue/react';
import { createFlueClient } from '@flue/sdk';

const client = createFlueClient({ baseUrl: '/api' });

createRoot(document.getElementById('root')!).render(
  <FlueProvider client={client}>
    <App />
  </FlueProvider>,
);
```

### Agent Chat

```tsx
import { useFlueAgent } from '@flue/react';

function Chat({ conversationId }: { conversationId: string }) {
  const agent = useFlueAgent({ name: 'support-assistant', id: conversationId });

  return (
    <div>
      {agent.messages.map(msg => (
        <article key={msg.id}>
          <strong>{msg.role}</strong>
          {msg.parts.filter(p => p.type === 'text').map(p => <p>{p.text}</p>)}
        </article>
      ))}
      <form onSubmit={e => { e.preventDefault(); agent.sendMessage(input); }}>
        <input value={input} onChange={e => setInput(e.target.value)} />
      </form>
    </div>
  );
}
```

### Workflow Observer

```tsx
const run = useFlueWorkflow({ runId });
// run.status, run.logs, run.result, run.error
```

Full reference: `./reference/docs_guide_react_index.md`

______________________________________________________________________

## CLI Reference

| Command                           | Description                             |
| --------------------------------- | --------------------------------------- |
| `flue init`                       | Create `flue.config.ts`                 |
| `flue dev`                        | Serve + watch local app                 |
| `flue run <name> --input '{...}'` | Execute one agent/workflow              |
| `flue build`                      | Create deployable artifacts             |
| `flue add <type>`                 | Fetch blueprints (sandbox, channel, db) |
| `flue update`                     | Refresh blueprints                      |
| `flue docs [search\|read]`        | Offline documentation                   |

### `flue dev`

- Default port: 3583
- Watches source files, rebuilds on change
- Supports `--target node` and `--target cloudflare`

### `flue run`

- Without `--server`: starts temporary runtime, executes `app.ts` + middleware
- With `--server <path>`: uses a non-root mount (e.g., `/api/flue`)
- With `--server <url>`: attaches to external server

Full reference: `./reference/docs_cli_overview_index.md`

______________________________________________________________________

## SDK Reference

`@flue/sdk` for consuming deployed Flue applications.

```ts
import { createFlueClient } from '@flue/sdk';

const client = createFlueClient({
  baseUrl: 'https://example.com/api',
  token: process.env.FLUE_TOKEN,
});
```

### API Namespaces

| Namespace          | Methods                                   |
| ------------------ | ----------------------------------------- |
| `client.agents`    | `prompt(...)`, `send(...)`, `stream(...)` |
| `client.workflows` | `invoke(...)`                             |
| `client.runs`      | `get(...)`, `events(...)`, `stream(...)`  |

Full reference: `./reference/docs_sdk_overview_index.md`

______________________________________________________________________

## Deployment Targets

### Node.js

```bash
npx flue build --target node
node dist/server.mjs
```

- Default port: 3000 (set `PORT` env)
- `flue dev` default: 3583
- `local()` sandbox for host filesystem access
- Durable adapters: SQLite, Postgres

### Cloudflare

```bash
npx flue build --target cloudflare
npx wrangler deploy
```

- Agents run inside Durable Objects (SQLite)
- `cloudflare/...` provider for Workers AI
- Requires `wrangler.jsonc` with `nodejs_compat` flag
- Generated DO classes: `Flue<Name>Agent`, `Flue<Name>Workflow`
- Durable Streams for event streaming

#### Wrangler Migrations

```jsonc
{
  "migrations": [
    { "tag": "v1", "new_sqlite_classes": ["FlueRegistry", "FlueSupportChatAgent"] },
    { "tag": "v2", "new_sqlite_classes": ["FlueTranslateWorkflow"] },
    { "tag": "v3", "deleted_classes": ["FlueSupportChatAgent"] },
  ]
}
```

#### Cloudflare Extension API

```ts
import { extend } from '@flue/runtime/cloudflare';

export const cloudflare = extend({
  base: (Base) => class extends Base {
    async onStart() {
      await this.scheduleEvery(60, 'heartbeat');
    }
  },
});
```

Full references:

- `./reference/docs_guide_targets_node_index.md`
- `./reference/docs_guide_targets_cloudflare_index.md`

______________________________________________________________________

## Ecosystem

### Channels (17+ providers)

Discord, Facebook, GitHub, Google Chat, Intercom, Linear, MS Teams, Notion, Resend, Salesforce, Shopify, Slack, Stripe, Telegram, Twilio, WhatsApp, Zendesk

### Sandboxes

Cloudflare Sandbox, Cloudflare Shell, Daytona, E2B, Modal, Vercel Sandbox, boxd, exe.dev, islo, Mirage, smolvm

### Deploy Targets

AWS, Cloudflare, Docker, Fly.io, GitHub Actions, GitLab CI/CD, Node.js, Railway, Render, SST

### Databases

libSQL, MongoDB, MySQL, Postgres, Redis, Supabase, Turso, Valkey

### Tooling

Braintrust, OpenTelemetry, Sentry, Vitest Evals

Full reference: `./reference/docs_ecosystem_index.md`

______________________________________________________________________

## Durable Agents

### Platform Comparison

| Feature              | Cloudflare             | Node (no db.ts) | Node (durable db.ts)  |
| -------------------- | ---------------------- | --------------- | --------------------- |
| State survival       | Durable Object SQLite  | Lost on restart | File/DB survives      |
| Recovery trigger     | Object startup, wake   | None            | Startup + lease scans |
| Ownership            | DO routing (one owner) | Process-local   | One live Node owner   |
| Interrupted workflow | Terminalizes run       | Lost            | Orphaned (active)     |

### Recovery Rules

- Recognizes already-completed output
- Reuses completed tool results
- Records interruption vs. retry
- Tool call with no durable result = interrupted (not retried)
- At-most-once recovery (at-least-once for prompts without observable effect)

Full reference: `./reference/docs_concepts_durable-execution_index.md`
