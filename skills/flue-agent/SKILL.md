---
name: flue-agent
description: Create and manage Flue agents — a TypeScript framework for building AI agents with a React-like hooks API and harness-driven architecture. Use when creating Flue projects, running npx flue / vite commands, editing flue.config.ts, agent modules, app.ts routing, or writing hooks-based agent code for Node.js/Cloudflare targets.
---

# Flue Framework Skill (v2)

Comprehensive knowledge base for **Flue** — the TypeScript framework for building autonomous AI agents. v2 uses a React-like **agent function + hooks** model: an agent is a plain exported function marked with the `'use agent'` directive; its return string is the system prompt; hooks (`useModel`, `useTool`, …) declare capabilities. Build/dev is Vite-based (`vite dev`, `vite build`); the CLI (`flue init/run/add/update/docs`) scaffolds and runs single agents.

**Version reference:** v2.0.x (as of Aug 2026)
**Source:** https://flueframework.com/docs/
**Reference docs:** `./reference/` directory (downloaded mirror of the live docs)

______________________________________________________________________

## Table of Contents

1. [Core Concepts](#core-concepts)
1. [Getting Started](#getting-started)
1. [Project Layout](#project-layout)
1. [Agents](#agents)
1. [Agent Hooks](#agent-hooks)
1. [Models](#models--providers)
1. [Tools](#tools)
1. [MCP](#mcp)
1. [Skills](#skills)
1. [Subagents](#subagents)
1. [Sandboxes](#sandboxes)
1. [Routing](#routing)
1. [Database](#database)
1. [Durability](#durability)
1. [Channels](#channels)
1. [Schedules](#schedules)
1. [Workflows](#workflows)
1. [Evals](#evals)
1. [Observability](#observability)
1. [React Frontend](#react-frontend)
1. [CLI Reference](#cli-reference)
1. [SDK Reference](#sdk-reference)
1. [Deployment Targets](#deployment-targets)
1. [Ecosystem](#ecosystem)

______________________________________________________________________

## Core Concepts

### Agent function + hooks

An agent is a **plain synchronous function** that returns its system-prompt instructions. Mark its module with the `'use agent'` directive (a string literal at the top of the file, before imports) and export the function — every exported **capitalized** function in a marked module is registered as an agent. The function name (or an `agentName` static) is the agent's durable identity.

```ts
'use agent';
import { useModel, useSandbox, useSkill, useTool } from '@flue/runtime';
import { local } from '@flue/runtime/node';
import { searchIssues } from '../tools/search-issues.ts';
import reviewChecklist from '../skills/review-checklist/SKILL.md';

export function TriageAgent() {
  useModel('anthropic/claude-sonnet-4-6');
  useSandbox(local());
  useTool(searchIssues);
  useSkill(reviewChecklist);
  return 'Investigate the reported issue and recommend the next action.';
}
```

- The agent function **re-renders before every model call** (like a React render). The returned string always reflects current state.
- Hooks may be **conditional**: a tool/skill/subagent/sandbox that appears or disappears between renders is added/removed at the next turn boundary and narrated to the model as a signal.
- **Rules**: functions must be synchronous and return a string or `undefined`; `useModel()` is required exactly once per render; duplicate names (tools, skills, subagents, state, data writers) within one render throw; renders never nest (delegation is via `useSubagent`).
- Renders are pure reads — write functions (state setters, data writers, dispatchers) throw if called during a render; call them from tool `run` and other callbacks.

### Headless agents

A Flue agent is **programmable** and **headless**: you interact via CLI (`flue run`), in-process JS (`init()`/`dispatch()`), or HTTP routes mounted in `app.ts` (`POST/GET /agents/<name>/<id>`).

Full reference: `./reference/docs_guide_building-agents_index.md`, `./reference/docs_reference_agent-api_index.md`

______________________________________________________________________

## Getting Started

### Prerequisites

- **Node.js** `>=22.19.0` (native TS type-stripping for `flue.config.ts`)
- **LLM** API key for a Pi-supported provider (e.g. `ANTHROPIC_API_KEY`)

### Quick Install

```bash
mkdir my-agent && cd my-agent
npm install @flue/runtime @flue/cli
npx flue init --target node   # or: --target cloudflare
echo 'ANTHROPIC_API_KEY="your-api-key"' > .env
```

### First Agent

`npx flue init` scaffolds `src/agents/hello.ts` with a ready `'use agent'` agent — no `defineAgent()` needed:

```ts
'use agent';
import { useModel } from '@flue/runtime';

export function Assistant() {
  useModel('anthropic/claude-haiku-4-5');
  return 'You are a helpful assistant. Keep replies short.';
}
```

### Run It

```bash
npx flue run src/agents/assistant.ts --message "Say hello in five words or fewer."
# Persistent conversations: reuse --id
npx flue run src/agents/assistant.ts --id hello-1 --message "Give me three more."
```

### Serve It (HTTP)

```bash
npm install @flue/vite hono vite
```

`vite.config.ts`:

```ts
import { flue } from '@flue/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [flue()], // Cloudflare: plugins: [flue(), cloudflare()]
});
```

`src/app.ts` (required route map):

```ts
import { createAgentRouter } from '@flue/runtime/routing';
import { Hono } from 'hono';
import { Assistant } from './agents/assistant.ts';

const app = new Hono();
app.route('/agents/assistant', createAgentRouter(Assistant));
export default app;
```

```bash
npx vite dev   # serves on http://localhost:5173
curl -X POST http://localhost:5173/agents/assistant/hello-1 \
  -H 'content-type: application/json' \
  -d '{"kind":"user","body":"Tell me a joke."}'
```

Full reference: `./reference/docs_guide_getting-started_index.md`

______________________________________________________________________

## Project Layout

Flue selects one source directory (first existing wins): `.flue/` (self-contained area in a larger app) → `src/` (recommended) → project root. Layouts are not merged.

| Path                | Purpose                                                  | Docs       |
| ------------------- | -------------------------------------------------------- | ---------- |
| `src/app.ts`        | HTTP route map, server entrypoint (**required**)         | Routing    |
| `src/db.ts`         | Optional persistence adapter (Node only)                 | Database   |
| `src/cloudflare.ts` | Optional CF handlers: `scheduled`, `queue`, …            | Cloudflare |
| `src/agents/*.ts`   | `'use agent'` modules (any file works, not just agents/) | Agents     |
| `flue.config.ts`    | Optional project config (`target`, `providers`, …)       | Config     |
| `vite.config.ts`    | Vite config with `flue()` plugin (required for serving)  | Deploy     |
| `wrangler.jsonc`    | Cloudflare config; migrations must be user-authored      | Cloudflare |

### `flue.config.ts`

```ts
import { defineConfig } from '@flue/runtime/config'; // note: @flue/runtime/config, NOT @flue/cli/config

export default defineConfig({
  target: 'node', // 'node' | 'cloudflare'; auto-detected from cloudflare() plugin when unset
  providers: ['anthropic', 'openai'], // exhaustive built-in provider list (bundle slimming)
  // app, db, cloudflare: entry paths; agents: glob; tracing: boolean (CF)
});
```

Output dir `dist/` is set in `vite.config.ts`. No file-based routing: everything HTTP is mounted explicitly in `app.ts`.

Full reference: `./reference/docs_guide_project-layout_index.md`, `./reference/docs_reference_configuration_index.md`

______________________________________________________________________

## Agents

### Statics on the function

The platform reads these without running the function (all optional, plain property assignments):

```ts
export function IssueTriage() { /* ... */ }
IssueTriage.agentName = 'issue-triage';        // durable identity override (kebab-case, AGENT_IDENTITY_PATTERN)
IssueTriage.initialData = v.object({ issue: v.pipe(v.number(), v.integer()) }); // creation-data schema
IssueTriage.durability = { maxAttempts: 5, timeoutMs: 7_200_000 }; // retry policy
```

### Props and data

- `({ id }: AgentProps)` — the root function receives the instance id (`:id` URL segment, `--id`, or `dispatch` id). Constant for the instance's life. Only the root agent gets props.
- `useInitialData()` reads validated creation data (`flue run --data '<json>'`, dispatch `initialData`, HTTP `initialData` sibling). Recorded once at creation; ignored on continues.
- `useDelivery()` reads the `DeliveredMessage` currently in front of the model.

### `DeliveredMessage`

The unified input shape for every delivery surface (dispatch, init handle, direct HTTP body):

```ts
type DeliveredMessage =
  | { kind: 'user'; body: string; attachments?: DeliveredAttachment[] } // real chat turn; images only attachments
  | { kind: 'signal'; type: string; body: string; attributes?: Record<string, string>; tagName?: string };
// bare string = shorthand for { kind: 'user', body }
```

`signal` = everything beyond a 1:1 chat (channels, webhooks, schedules): sender identity + metadata in flat string `attributes`; renders as an XML-tagged block in model context. `user` = direct user chat turn.

### Interacting

| Surface    | How                                                                            |
| ---------- | ------------------------------------------------------------------------------ |
| CLI        | `npx flue run <path> --message "..." [--id x] [--new] [--data '{}'] [--json]`  |
| HTTP       | `POST /agents/<name>/<id>` — fire-and-forget, `202` admission; read via `GET`  |
| In-process | `dispatch(Agent, { id, message })` — fire-and-forget; `init()` handle to await |
| Standalone | `start({ agents, db })` boots the runtime in your own Node process             |

```ts
import { init } from '@flue/runtime';
import { sqlite, start } from '@flue/runtime/node';
import { Reporter } from '../src/agents/reporter.ts';

await using flue = await start({ agents: [Reporter], db: sqlite('./nightly.db') });

const reporter = init(Reporter, { id: 'nightly-2026-07-16' });
const receipt = await reporter.dispatch('Produce the nightly report.');
const reply = await reporter.read(receipt);
console.log(reply.text);
```

**Conditional sends** via `uid` (the instance's ETag): omit → create-or-continue; `uid: '<string>'` → continue only that incarnation (`409`/`AgentInstanceNotFoundError` on miss); `uid: null` → create-only (`409`/`AgentInstanceExistsError` on hit, `.uid` carries existing incarnation — perfect for exactly-once CI with `--new`).

Full references: `./reference/docs_guide_building-agents_index.md`, `./reference/docs_reference_agent-api_index.md`

______________________________________________________________________

## Agent Hooks

All exported from `@flue/runtime`. Call them only during the agent render (body or custom `use*` fn). Throwing when called elsewhere: `[flue] <hook>() was called outside an agent function.`

| Hook                                               | Purpose                                                                                         |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `useModel(model, { thinkingLevel?, compaction? })` | Declare the LLM. Required, exactly once                                                         |
| `useSandbox(factory, { cwd? })`                    | Attach the execution environment (opt-in)                                                       |
| `useTool(tool)`                                    | Mount a model-callable tool                                                                     |
| `useMcpConnection(def)`                            | Declare a remote MCP server (tools mount as `mcp__<server>__<tool>`)                            |
| `useSkill(skill)`                                  | Mount a skill into the disclosure catalog                                                       |
| `useSubagent(def)`                                 | Declare a `task`-tool delegate                                                                  |
| `useInstruction(text)`                             | Append raw instruction text (low-level escape hatch)                                            |
| `usePersistentState(name, default?)`               | Durable per-instance state, React-style `[value, setter]`                                       |
| `useInitialData<T>()`                              | Read instance-creation data                                                                     |
| `useDelivery()`                                    | Read the message in front of the model                                                          |
| `useDispatchMessage()`                             | Dispatcher bound to this instance                                                               |
| `useDataWriter(name, { schema? })`                 | Stream named data parts to clients                                                              |
| `useAgentStart(cb)`                                | Async callback when work starts on a delivered message (async OK; loads data before model runs) |
| `useAgentFinish(cb)`                               | Callback at every would-stop point; `ctx.append(signal)` sends model back to work               |
| `useResponseStart(fn)`                             | Sync observer at response true start; returns metadata merged onto response                     |
| `useResponseFinish(fn)`                            | Sync observer at response true end; final `response.usage` / `toolCalls`                        |

### Persisted state (gates capabilities)

```ts
'use agent';
import { useModel, usePersistentState, useTool } from '@flue/runtime';

export function SupportAgent() {
  useModel('anthropic/claude-haiku-4-5');
  const [escalated, setEscalated] = usePersistentState('escalated', false);

  useTool({
    name: 'escalate',
    description: 'Escalate when the customer needs a refund.',
    async run() {
      setEscalated(true);
      return 'Escalated. The refund tool is now available.';
    },
  });

  if (escalated) { useTool(refundTool); } // conditional capability unlock
  return 'Answer customer support questions clearly and accurately.';
}
```

- Values are JSON-serializable; setter throws on `undefined`/non-serializable; updater form `set((prev) => ...)` resolves at call time (safe read-modify-write).
- Writes are silent (never wake the agent); next render reads latest values.
- Interpolate state into instructions (`return \`Phase: ${phase}.\`\`) for multi-step behavior.

### Event hooks

- `useAgentStart(async ({ harness, append, log, signal }) => {...})` — intake seam; load data, dispatch signals, write state.
- `useAgentFinish(({ response, append, harness }) => {...})` — enforcement seam: `append({ kind: 'signal', type, body, attributes })` steers the same response; settles only when no appends and no queued input. Max 32 continuations (unconfigurable).
- `useResponseStart/Finish(() => ({ startedAt: Date.now() }))` — sync, return plain object merged onto response `metadata`.

### Data writers

```ts
const writeOrderCard = useDataWriter('orderCard', {
  schema: v.object({ orderId: v.string(), status: v.picklist(['loading', 'loaded']) }),
});
writeOrderCard({ orderId: data.orderId, status: 'loaded' }); // in tool run
```

Arrives on the wire as a `data-orderCard` part; the model never sees it. Names must be declared identically every render.

### Custom hooks

Plain functions prefixed `use` that call other hooks — composition with no registration:

```ts
function useEscalation() {
  useTool(escalateCase);
  return 'Escalate to a specialist only after confirming the account and issue.';
}
```

Full reference: `./reference/docs_guide_agent-hooks_index.md`, `./reference/docs_reference_agent-hooks-api_index.md`

______________________________________________________________________

## Models & Providers

### `useModel()`

```ts
useModel('anthropic/claude-sonnet-4-6', {
  thinkingLevel: 'high',  // 'off'|'minimal'|'low'|'medium'|'high'|'xhigh' (default 'medium')
  compaction: { keepRecentTokens: 16000, reserveTokens: 30000, model: 'anthropic/claude-haiku-4-5' },
});
```

- Specifier: `'<provider-id>/<model-id>'` — everything before the first `/` is the provider (`openrouter/moonshotai/kimi-k2.6`, `cloudflare/@cf/...`).
- Values are **submission-scoped** (computed from state → takes effect next submission). The model can change mid-conversation (escalation pattern).
- `compaction: false` disables only threshold-triggered compaction. Defaults: reserve model-aware ≤20000, keepRecent 8000.
- Unresolvable specifier fails fast at submission initialization.

### Providers

- Built-in set comes from Pi (`anthropic`, `openai`, `google`, `groq`, `mistral`, `xai`, `deepseek`, `cerebras`, `together`, `fireworks`, `openrouter`, and more). Env vars like `ANTHROPIC_API_KEY`.
- **`providers: ['anthropic', 'openai']`** in config = exhaustive bundle (real deploy weight savings). `'cloudflare'` = Workers AI binding provider (CF only; error on Node).
- Custom providers are pi-ai `Provider` objects via `setProvider()`, built with `createProvider(...)` / built-in factories from `@earendil-works/pi-ai` (a direct dependency). `registerProvider`/`registerApiProvider` are gone.

Full reference: `./reference/docs_guide_models_index.md`, `./reference/docs_reference_provider-api_index.md`

______________________________________________________________________

## Tools

### `defineTool()`

```ts
import { defineTool } from '@flue/runtime';
import * as v from 'valibot';

export const lookupOrder = defineTool({
  name: 'lookup_order',
  description: 'Look up one order by id and return its current status.',
  input: v.object({ orderId: v.string() }),     // optional Valibot object schema
  output: v.object({ status: v.string(), eta: v.string() }), // optional
  async run({ data, signal, log, toolCallId }) {
    const order = await orders.get(data.orderId);
    return { output: { status: order.status } }; // envelope: { output?, terminate? }
    // bare string = { output: <string> }; terminate: true ends the turn
  },
});
```

- **context**: `{ data, signal, log, toolCallId }` — `data` = schema-parsed args; `signal` = AbortSignal (abandoned on abort); `log.info/warn/error` stream as conversation events (model never sees them).
- Mount with `useTool(lookupOrder)` or inline. Validation failure → tool error the model sees (it can retry). A throw inside `run` never fails the submission.
- Duplicate/framework-reserved names (`task`, `activate_skill`, `read_skill_resource`) throw at assembly.

### Harness tools (`harness: true`)

Reach the agent's own runtime in `run({ harness })`:

```ts
async run({ harness, data }) {
  await harness.sandbox.writeFile('contract.md', data.contract);
  const { data: report } = await harness.prompt('Review contract.md for risk.', { result: Report });
  return { output: report };
}
```

- `harness.sandbox` — live `SessionEnv` (`exec`, `readFile`, `writeFile`, `stat`, `readdir`, `mkdir`, `rm`, `cwd`, `resolvePath`); never recorded in the conversation; throws when no sandbox declared.
- `harness.prompt(text, { result?, tools?, model?, thinkingLevel?, signal?, images? })` — scratch-conversation model op; `result` (Valibot schema) requires structured output via a framework `finish` tool. Repeated calls continue one conversation.
- `harness.compact()` — compact the scratch conversation. Count against the delegation-depth cap.

### Durable tools (`durable: true`)

For work that must complete across crashes. `run` receives `step`:

```ts
const tenant = await step.do('create-tenant', () => billing.createTenant(data.customerId));
```

- `step.do(name, fn)` runs `fn` once per name per call; completed values are durably recorded and replayed on recovery (exactly-once-recorded, at-least-once-executed — keep steps idempotent).
- Interrupted ordinary tools settle with an unknown-outcome error the model sees; durable tools re-execute.
- Flags compose: `durable: true, harness: true` gets both.

### Conditional tools

Wrap `useTool` in a condition (e.g. on `usePersistentState`) — an unmounted tool can't be called. Set changes are narrated via `resources` signals without invalidating the prompt cache.

### Tool security

Model-selected args are not an authorization boundary. Carry the trusted identifier in the delivered signal's `attributes` and read with `useDelivery()`:

```ts
const delivery = useDelivery();
const customerId = delivery.kind === 'signal' ? delivery.attributes?.customerId : undefined;
```

Full reference: `./reference/docs_guide_tools_index.md`

______________________________________________________________________

## MCP

```ts
'use agent';
import { useMcpConnection, useModel } from '@flue/runtime';

export function ProjectAssistant() {
  useModel('anthropic/claude-sonnet-4-6');
  useMcpConnection({
    name: 'linear',
    url: 'https://mcp.linear.app/mcp',
    auth: process.env.LINEAR_API_KEY,          // static bearer, or () => token for rotating/ per-user
    tools: ['create_issue', 'search_issues'],  // allowlist (omit = all)
  });
  return 'Manage Linear issues and projects for the team.';
}
```

- Tools mount as `mcp__<server>__<tool>`; connections are runtime-owned and reused for the instance's lifetime.
- Transport: `'streamable-http'` (default) or `'sse'`. `headers` set-wins over `requestInit`.
- `optional: true` — a failed server mounts zero tools and tells the model, instead of failing the submission.
- `defineMcpConnection(def)` — validating/freezing helper for exportable units (spread for per-mount overrides). `createMcpConnection(def)` — async imperative factory (Node only; CF Workers prohibit top-level network I/O — use the hook there).
- OAuth/token storage is application-owned; Flue never stores tokens.

Full reference: `./reference/docs_guide_mcp_index.md`

______________________________________________________________________

## Skills

Open [Agent Skills](https://agentskills.io) format — reusable instructions, progressively disclosed (one catalog line per skill; body loads on `activate_skill`).

### Author & mount

```text
src/skills/refunds/
├─ SKILL.md        # frontmatter + instructions
└─ POLICY.md       # supporting file, loaded only when read
```

```ts
'use agent';
import { useModel, useSkill } from '@flue/runtime';
import refunds from '../skills/refunds/SKILL.md';  // static import only!

export function SupportAgent() {
  useModel('anthropic/claude-haiku-4-5');
  useSkill(refunds);
  return 'Answer customer support questions clearly and accurately.';
}
```

- Any path resolving to a `SKILL.md` packages the whole directory; any other `.md` import yields plain text (hand to `useInstruction` or `defineSkill`). No import attributes (`with { type: 'skill' }` gone).
- Import specifiers are resolved by Vite: local dirs, npm and workspace packages.

### Frontmatter

`name` (required: lowercase letters/numbers/single hyphens, ≤64 chars, matches dir name), `description` (required, ≤1024 chars — the routing decision), plus optional `license`, `compatibility`, `metadata`, `allowed-tools` (accepted, not enforced). Unknown fields ignored.

### `defineSkill()`

Inline, code-defined skills:

```ts
import { defineSkill } from '@flue/runtime';

export const escalation = defineSkill({
  name: 'escalation',
  description: 'Escalate an unresolved case to a human specialist. Use when the customer asks for a human.',
  instructions: 'Summarize the case, tag it, and hand off with the `escalate_case` tool.',
  files: { 'POLICY.md': checklistText }, // optional supporting resources
});
```

- Packaging happens lazily; `instructions` is required (a skill is its content).
- **Workspace skills**: `SKILL.md` dirs under `<cwd>/.agents/skills/` of a sandbox are auto-discovered; the model activates by name.
- Packaging refuses secrets (`.env`, private keys, symlinks — hard errors) and warns on >1MB files.
- Skills are conditional-able like tools; catalog changes narrated via `resources` signals.

Full reference: `./reference/docs_guide_skills_index.md`

______________________________________________________________________

## Subagents

Named delegation targets for the built-in `task` tool. Only declared subagents resolve.

```ts
import { defineSubagent } from '@flue/runtime';

export const issueClassifier = defineSubagent({
  name: 'issue_classifier',
  description: 'Classifies support issues for routing.',
  agent: IssueClassifier,          // a plain agent function
  model: 'anthropic/claude-haiku-4-5', // optional; inherits parent when omitted
});

// Mount:
useSubagent(issueClassifier);
// Or with override: useSubagent({ ...issueClassifier, model: 'anthropic/claude-opus-4-6' });
```

- The delegate's function is rendered fresh per task, in its own frame. It gets the shared environment (sandbox, filesystem tools), none of the parent's instructions/tools/skills.
- `GeneralSubagent` — exported blank delegate (reserved name `flue-general`); gives a fresh context with just the shared environment (opt-in).
- Children have no durable identity/state/persistent instance — a real registered agent + `dispatch()` is the pattern for addressable long-lived conversations.
- Use when: context isolation, parallel work, different model/instructions per phase. Interrupted tasks resume from their own durable transcripts on recovery.

Full reference: `./reference/docs_guide_subagents_index.md`

______________________________________________________________________

## Sandboxes

**Opt-in.** No `useSandbox()` = no file/shell tools, no workspace context, `harness.sandbox` throws. Assets: file+shell tools (`read`, `write`, `edit`, `bash`, `grep`, `glob`), workspace context (cwd listing, `AGENTS.md`), workspace skills (`.agents/skills/`), subagent sharing.

### Virtual (`bash()` + just-bash)

In-memory filesystem + emulated bash (no real processes). Isolated from host; network opt-in.

```ts
import { bash, useModel, useSandbox } from '@flue/runtime';
import { Bash, InMemoryFs } from 'just-bash';   // add just-bash to dependencies

export function ScratchWorker() {
  useModel('anthropic/claude-haiku-4-5');
  useSandbox(bash(() => new Bash({
    fs: new InMemoryFs({ '/data/catalog.csv': exportCatalogCsv() }),
    network: { allowedUrlPrefixes: ['https://api.example.com/'] },
  })));
  return 'Answer questions about the product catalog in /data/catalog.csv.';
}
```

Ephemeral — rebuilt per initialization; keep durable knowledge in `usePersistentState`.

### Local (`local()`, Node only)

Real host filesystem + shell via `child_process`. Trusted environments only (dev tools, CI, coding agents).

```ts
import { local } from '@flue/runtime/node';
useSandbox(local({ cwd: '/srv/checkouts/catalog-service', env: { GH_TOKEN: process.env.GH_TOKEN } }));
```

- Shell gets only an allowlist (PATH, HOME, USER, LANG, TERM, TMPDIR…) — **never API keys**. `env` is explicit per-variable opt-in; `env: { ...process.env }` leaks everything — trusted envs only.
- Snapshot taken once at sandbox construction.

### Remote & rules

- Remote adapters: `flue add sandbox e2b` (Daytona, E2B, Modal, Cloudflare Sandbox/Shell, Vercel, …).
- At most one `useSandbox` per render; lazy factory (`createSessionEnv()` runs once at init); `cwd` resolves once at init; may be conditional (presence flips swap env at turn boundary, narrated as an `environment` signal).
- Subagent renders throw — delegates share the parent environment.

Full reference: `./reference/docs_guide_sandboxes_index.md`

______________________________________________________________________

## Routing

**No automatic mounting.** Every route is explicit in `app.ts` (a Hono app or any fetch-compatible object).

### Mount an agent

```ts
import { createAgentRouter } from '@flue/runtime/routing'; // pure factory, no side effects
app.route('/agents/support', createAgentRouter(Support));
```

- Mount path is pure routing — conversations key on the durable identity, never the URL. One agent can be mounted at two paths.
- `'use agent'` scan = registration; dispatch-only agents need no mount.
- Routes relative to mount: `POST /:id` (202 admission), `GET|HEAD /:id` (snapshot/updates/stream), `POST /:id/abort`, `GET /:id/attachments/:attachmentId`.

### Conversation URL protocol

- POST body is the `DeliveredMessage` (+ optional `initialData`/`uid` siblings). **Fire-and-forget**: `202` with `{ streamUrl, offset, submissionId }` — there is no wait mode; read the reply from the conversation.
- `GET ?view=history` → snapshot; `?view=updates&offset=...` → changes (long-poll or SSE). Wire protocol: `./reference/docs_reference_streaming-protocol_index.md`.

### Protect your agents

No built-in auth. Layer middleware in `app.ts` — both **authentication** (who) and **authorization** (may access *this conversation id*):

```ts
app.use('/agents/support/*', async (c, next) => {
  const user = await verifySession(c.req.raw);
  if (!user) return c.json({ error: 'unauthorized' }, 401);
  const [conversationId] = c.req.path.slice('/agents/support/'.length).split('/');
  if (!(await canAccessTicket(user, conversationId))) return c.json({ error: 'forbidden' }, 403);
  return next();
});
app.route('/agents/support', createAgentRouter(Support));
```

CORS is an application concern; expose `Stream-Next-Offset`, `Stream-Up-To-Date`, `Location` headers for SDK reconnects. `vite dev`/`vite preview` apply permissive dev defaults.

### Channels

`app.route('/channels/slack', slack.route())` — channel routers serve verified provider ingress (no extra auth middleware; provider-signature verification is the auth).

Full reference: `./reference/docs_guide_routing_index.md`

______________________________________________________________________

## Database

Flue stores its own durable state: canonical conversation streams, accepted submissions (+ claims/leases), persisted state, attachment payloads. Not stored: sandbox files, provider credentials, business data.

### `db.ts` (Node)

```ts
import { sqlite } from '@flue/runtime/node';
export default sqlite('./data/flue.db');  // file-backed, WAL mode; sqlite() / ':memory:' = in-memory
```

- No `db.ts` → in-memory SQLite (lost on restart). Dev defaults: `vite dev` → `node_modules/.cache/flue/dev.db`; `flue run` → `node_modules/.cache/flue/run.db` (persistent across invocations).
- `start({ db })` scripts pass adapters directly; they don't read `db.ts`.

### Ecosystem adapters (bring-your-own-driver)

| Backend                          | Package                                     |
| -------------------------------- | ------------------------------------------- |
| Postgres / Supabase              | `@flue/postgres`                            |
| libSQL / Turso                   | `@flue/libsql`                              |
| MySQL / MongoDB / Redis / Valkey | `@flue/mysql` `@flue/mongodb` `@flue/redis` |

```ts
import { postgres } from '@flue/postgres';
import { Pool } from 'pg';
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
export default postgres({
  query: async (text, params) => (await pool.query(text, params)).rows,
  transaction: async (fn) => { /* BEGIN/COMMIT/ROLLBACK around fn */ },
  close: () => pool.end(),
});
```

Blueprints: `flue add database postgres`. `migrate()` provisions idempotently at boot; format versions are stamped (incompatible DBs refuse to start). Shared DB ≠ active-active: each conversation needs one live Node owner.

### Cloudflare

Nothing to configure — Durable Object SQLite per agent; a `db.ts` is a build error.

### Custom adapters

`PersistenceAdapter` contract in `@flue/runtime/adapter` (`connect()` → submissionStore, conversationStreamStore, attachmentStore; optional `migrate()`/`close()`); run `@flue/runtime/test-utils` contract suites.

Full reference: `./reference/docs_guide_database_index.md`

______________________________________________________________________

## Durability

**The accepted-work contract**: every admitted submission reaches exactly one durable terminal outcome (`completed` | `failed` | `aborted`) through crashes, restarts, and redeploys. Outcomes land as `submission_settled` records in the conversation stream.

- Submissions queue per conversation in admission order; busy instances join the live response at turn boundaries; queued messages are never lost.
- **Recovery** classifies from durable evidence: never-persisted input → requeue; completed response → settle; partial text → continue from durable partial; unresolved tool calls → repair the batch (preserving recorded results, marking unknown outcomes); abort intent → settle aborted.
- **At-least-once execution, exactly-once recording.** Committed work never re-runs; interrupted work re-runs. Guard external side effects (emails, pages) with persistent state.
- **Retry budget**: `IssueTriage.durability = { maxAttempts: 10, timeoutMs: 3_600_000 }` (defaults). Timeout is total wall-clock from first attempt.
- **Durable tools** (`durable: true` + `step.do`) re-execute with recorded steps replayed. **Delegated tasks** resume from their own transcripts under the parent's budget.
- **Abort**: `POST /:id/abort` / SDK `abort()` / `handle.abort()` records durable intent; settles distinct `aborted` outcome.
- Per-target: Cloudflare = Durable Object wake/alarm (platform observability sees one invocation per response); Node = one live owner per conversation + lease-scan recovery.

Full reference: `./reference/docs_guide_durability_index.md`

______________________________________________________________________

## Channels

Verified provider ingress → route provider-native payloads into agent conversations via `dispatch()`. Inbound-only; outbound uses the provider's own SDK.

```bash
npx flue add channel slack   # blueprint: installs @flue/slack + @slack/web-api, wires src/channels/slack.ts
```

```ts
// src/channels/slack.ts
export const channel = createSlackChannel({
  signingSecret: process.env.SLACK_SIGNING_SECRET!,
  async events({ payload }) {
    if (payload.type !== 'event_callback' || payload.event.type !== 'app_mention') return;
    await dispatch(Assistant, {
      id: channel.instanceId({ teamId: payload.team_id, channelId: payload.event.channel, threadTs: payload.event.thread_ts ?? payload.event.ts }),
      idempotencyKey: payload.event_id,   // provider redelivery convergence — at most one answer
      initialData: { channelId: thread.channelId, threadTs: thread.threadTs },
      message: { kind: 'signal', type: 'slack.app_mention', body: payload.event.text, attributes: { eventId: payload.event_id } },
    });
  },
});
```

Patterns:

- One agent conversation per provider destination (`instanceId()` derives canonical ids; `parseInstanceId` is an escape hatch — prefer `initialData`).
- Channels are stateless; pass the provider's redelivery-stable id as `idempotencyKey` (reuse w/ different payload → 409 `submission_conflict`).
- Acknowledge quickly (dispatch resolves at admission); don't await agent output in handlers.
- Providers: Discord, Facebook/Messenger, GitHub, Google Chat, Intercom, Linear, MS Teams, Notion, Resend, Salesforce, Shopify, Slack, Stripe, Telegram, Twilio, WhatsApp, Zendesk — each ships as a blueprint (`flue add channel <name>`).

Full reference: `./reference/docs_guide_channels_index.md`

______________________________________________________________________

## Schedules

Flue has no scheduler; each target pairs its cron mechanism with `dispatch()`.

### Node (in-process cron in `app.ts`)

```ts
import { dispatch } from '@flue/runtime';
import { Cron } from 'croner';   // example library

new Cron('0 9 * * *', { timezone: 'America/New_York', protect: true,
  catch: (e) => console.error('Scheduled dispatch failed', e) },
  async () => {
    await dispatch(Reporter, {
      id: 'daily-summary',
      message: { kind: 'signal', type: 'schedule', body: 'Review recent activity.', attributes: { scheduledAt: new Date().toISOString() } },
    });
  });
```

### Cloudflare (Cron Trigger → `cloudflare.ts`)

```jsonc
// wrangler.jsonc
{ "triggers": { "crons": ["0 9 * * *"] } }   // UTC only
```

```ts
// src/cloudflare.ts
import { dispatch } from '@flue/runtime';

export default {
  async scheduled(controller) {
    await dispatch(Reporter, { id: 'daily-summary', message: { kind: 'signal', type: 'schedule', body: '...', attributes: { cron: controller.cron } } });
  },
};
```

- Scheduled agents need no HTTP mount (dispatch-only). A fire delivers as `kind: 'signal'`.
- In-DO timers: Agents SDK `schedule()`/`scheduleEvery()` via the `cloudflare.ts` `extend()` extension API.

Full reference: `./reference/docs_guide_schedules_index.md`

______________________________________________________________________

## Workflows

In v2, a "workflow" is **any program that drives an agent** — there is no framework workflow abstraction (`defineWorkflow`/`invoke`/run stores were removed). Pick by where the code runs:

| Approach                                                          | Use when                                                |
| ----------------------------------------------------------------- | ------------------------------------------------------- |
| `npx flue run <path> -m "..."`                                    | CI / shell / terminal one-shots                         |
| `start()` + `init()` JS API                                       | Node scripts, cron jobs, tests                          |
| `@flue/sdk` over HTTP                                             | talking to a hosted agent                               |
| External durable engine (Cloudflare Workflows, Inngest, Temporal) | multi-step orchestration that must survive interruption |

**Durable workflow pattern** — checkpoint the dispatch receipt in one step, read the settled reply in another (a completed dispatch step never re-sends; a crashed read step re-attaches):

```ts
// Cloudflare Workflows / Inngest both follow this shape
const receipt = await step.do('dispatch review', () => agent.dispatch('Review the findings.'));
const review = await step.do('read review', async () => {
  const reply = await agent.read(receipt);
  return { text: reply.text, data: reply.data };
});
```

The one crash window is inside the dispatch step: an unconditional re-send duplicates but coalesces onto the same reply; `uid: null` (create-only) rejects with `AgentInstanceExistsError` — your signal to fail the run.

Full reference: `./reference/docs_guide_workflows_index.md`

______________________________________________________________________

## Evals

Flue has no eval framework: an eval is a Vitest test that drives the agent through public surfaces and asserts behavior. Nondeterministic → assert the behavioral contract (tool calls, key facts, data shape), not exact strings.

```ts
// vitest.evals.config.ts: include ['src/evals/**/*.eval.ts'], testTimeout 60_000
import { init } from '@flue/runtime';
import { start } from '@flue/runtime/node';
import { afterAll, expect, it } from 'vitest';
import { ServiceStatus } from '../agents/service-status.ts';

const flue = await start({ agents: [ServiceStatus] });
afterAll(() => flue.stop());

it('checks live status before answering', async () => {
  const toolsCalled: string[] = [];
  const agent = init(ServiceStatus); // no id = fresh conversation per case
  const receipt = await agent.dispatch('Is checkout operational?');
  const reply = await agent.read(receipt, {
    onEvent: (chunk) => { if (chunk.type === 'tool-input') toolsCalled.push(chunk.toolName); },
  });
  expect(reply.text).toContain('operational');
  expect(toolsCalled).toContain('get_service_status');
});
```

- One `start()` per test file (one runtime per process); stop it in `afterAll`.
- Agents using build-resolved imports (`SKILL.md` imports) need the Flue build → evaluate over HTTP instead (`createFlueClient`).
- `vitest-evals` tooling layers harnesses/judges/CI reporting. Script: `"evals": "vitest run --config vitest.evals.config.ts"`.

Full reference: `./reference/docs_guide_evals_index.md`

______________________________________________________________________

## Observability

Two distinct surfaces:

1. **Conversation stream** — product surface: one conversation's durable render-ready messages/data parts/settlements (`@flue/sdk` `observe()`/`history()`, `GET /agents/:name/:id`).
1. **Runtime event stream** — operational surface: live activity across all agents in-process via `observe()` from `@flue/runtime` (typed `FlueEvent`s, `v: 3`).

```ts
import { observe } from '@flue/runtime';

observe((event) => {
  if (event.type === 'submission_settled' && event.outcome === 'failed') {
    console.error(`[${event.agentName}] ${event.submissionId} failed:`, event.error?.message);
  }
});
```

- Event families: `agent_start/end/idle`, `submission_settled` (the reliable terminal signal — alert on it), `operation_start/operation`, `turn_start/turn_request/turn/turn_messages`, `message_*`/`text_delta`/`thinking_*`, `tool_start/tool`, `task_start/task`, `compaction_start/compaction`, `log`.
- Token usage on `turn` events: `response.usage` = `{ input, output, cacheRead, cacheWrite, totalTokens, cost }`.
- **Subscriber rules**: stay cheap (sync emission path), read-only, contained failures.
- **Logging in tools**: `log.info/warn/error(message, attributes)` — streams into the conversation as `log` events; model never sees them.
- Exporters: Sentry, Braintrust, OpenTelemetry (via `setInstrumentation`-family APIs and the ecosystem tooling pages). Cloudflare: auto `createCloudflareTracing()` (Workers Traces), one platform invocation per response.

Full reference: `./reference/docs_guide_observability_index.md`, `./reference/docs_reference_events_index.md`

______________________________________________________________________

## React Frontend

`@flue/react` turns conversation streams into live React state. One conversation per hook by URL; no provider required.

```tsx
import { useFlueAgent } from '@flue/react';
import { useState } from 'react';

function Chat({ conversationId }: { conversationId: string }) {
  const [input, setInput] = useState('');
  const agent = useFlueAgent({ url: `/api/agents/support-assistant/${conversationId}` });

  return (
    <>
      {agent.messages.map((message) => (
        <article key={message.id}>
          <strong>{message.role}</strong>
          {message.parts.map((part) =>
            part.type === 'text' ? <p key={part.text}>{part.text}</p> : null)}
        </article>
      ))}
      <form onSubmit={(e) => { e.preventDefault(); agent.sendMessage(input); setInput(''); }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} />
      </form>
    </>
  );
}
```

- `sendMessage()` resolves at admission (optimistic message reconciled in place). `status`, `historyReady`, `refresh()` (re-check for out-of-band creation) available.
- Message parts: `text`, `reasoning`, `dynamic-tool` (validated tool output on `output`), `file` (durable URLs / optimistic `data:` previews), custom `data-<name>` parts from `useDataWriter`.
- Live updates default SSE (fall back to long-poll; `live: 'long-poll'` opts in). Flue's own types — not AI SDK types.
- Custom auth: pass a memoized `createFlueClient({ url, token })` as `useFlueAgent({ client })` — share one client with programmatic `observe()`/`wait()`/`read()`.
- SSR-safe: dormant during server render; relative `url` resolves on the browser origin after hydration.

Full reference: `./reference/docs_guide_react_index.md`

______________________________________________________________________

## CLI Reference

`@flue/cli` requires Node ≥22.19. **The CLI is not the build tool** — `vite dev`/`vite build` (with `flue()` from `@flue/vite`) own dev servers and builds. `flue dev`/`flue build` were removed and error with pointers.

| Command                                                                                                                        | Description                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `flue init [dir] [--target node\|cloudflare] [--deploy] [--force]`                                                             | Scaffold a starter project (writes files only — run `npm install` after). `--deploy` adds server setup (implied for cloudflare)                                                                                                                                                                  |
| `flue run <path> --message <text> [--name <agent>] [--id <id>] [--data <json>] [--uid <uid> \| --new] [--env <path>] [--json]` | Run one agent module locally, no server. Reply → stdout; everything else → stderr; `--json` prints one `{ id, agent, submissionId, outcome, message\|error, uid }` envelope. Exit: 0 completed / 1 failed / 130 aborted. `--new` = create-only, `--uid` = continue-only; `--data` only on create |
| `flue add [kind] [name\|url]`                                                                                                  | Fetch a blueprint guide (channel, database, sandbox) for your coding agent; no args lists blueprints                                                                                                                                                                                             |
| `flue update <kind> <name\|url>`                                                                                               | Fetch the same guide with upgrade instructions for an existing integration                                                                                                                                                                                                                       |
| `flue docs [read\|search]`                                                                                                     | Browse the bundled documentation offline (`flue docs read <path>`, `flue docs search <query>`)                                                                                                                                                                                                   |

Global flags: `--help/-h`, `--version/-v` only. Primary payload → stdout, everything else → stderr (piping-safe).

Full references: `./reference/docs_cli_overview_index.md`, `./reference/docs_cli_run_index.md`, `./reference/docs_cli_init_index.md`

______________________________________________________________________

## SDK Reference

`@flue/sdk` — TypeScript client for **one conversation URL** of a deployed app. ESM-only, runs anywhere `fetch` exists; one dependency (`@durable-streams/client`).

```ts
import { createFlueClient } from '@flue/sdk';

const conversation = createFlueClient({
  url: 'https://example.com/agents/support/ticket-8472',
  token: process.env.FLUE_TOKEN,   // or headers: {...}
});

const admission = await conversation.send({
  message: { kind: 'user', body: 'Summarize the open issues in my case.' },
});
const reply = await conversation.read(admission); // waits for settlement; throws FlueExecutionError
```

| Method            | Route                       | Purpose                                                                         |
| ----------------- | --------------------------- | ------------------------------------------------------------------------------- |
| `send()`          | `POST <url>`                | Admit a message (202; body = `DeliveredMessage` + optional `initialData`/`uid`) |
| `wait()`          | `GET ?view=updates`         | Resolve on submission settlement (resolves `void`; throws on failure/abort)     |
| `read()`          | wait + `?view=history`      | Settlement + extract that submission's reply                                    |
| `history()`       | `GET ?view=history`         | One materialized conversation snapshot                                          |
| `observe()`       | history + updates           | Live view with reconnection/rehydration/dedup                                   |
| `abort()`         | `POST <url>/abort`          | Durable abort of in-flight + queued work                                        |
| `attachmentUrl()` | `GET <url>/attachments/:id` | Resolve a `file` part's bytes                                                   |

- One conversation per client — no deployment-wide addressing, no enumeration. New conversation = fresh id appended to the mount URL.
- Errors: `FlueApiError` (HTTP), `FlueExecutionError` (failed/aborted settlements — `.failure` `'aborted'` | `'failed'`).
- Cloudflare service binding: point the client's `fetch` option at the binding (baseUrl host never dialed).

Full references: `./reference/docs_sdk_overview_index.md`, `./reference/docs_sdk_flue-client_index.md`

______________________________________________________________________

## Deployment Targets

### Node.js

```bash
npx vite build
node dist/server.mjs        # port 3000 (set PORT); reads only the supplied env — no .env loading
```

- `dist/server.mjs` (self-starting) + `dist/app.mjs` (importable chunk, served by `vite preview`).
- Dependencies are externalized — deploy alongside `node_modules` or in a container.
- `local()` sandbox, `sqlite()`/ecosystem DB, one live owner per conversation.

### Cloudflare

```bash
npm install @cloudflare/vite-plugin
npx vite build && npx wrangler deploy
```

- `vite.config.ts`: `plugins: [flue(), cloudflare()]` — **flue() first** (wrong order = diagnosed error). `flueWorkerConfig()` customizer keeps `wrangler.jsonc` user-owned; nothing generated into the tree beyond `.flue-vite/` (gitignore it).
- One generated Durable Object class per agent: `SupportChat` → `FlueSupportChatAgent` / binding `env.FLUE_SUPPORT_CHAT_AGENT`. SQLite storage is automatic. **No `db.ts`.**
- `wrangler.jsonc` must declare `nodejs_compat` compatibility flag + user-authored migrations: add an agent = `new_sqlite_classes` with a unique tag; removals = `deleted_classes`; identity renames = `renamed_classes` (preserves stored conversations). Never rewrite deployed migration entries.
- `cloudflare/...` model specifiers run on Workers AI with no API keys. `createCloudflareTracing()` (auto-installed; disable with `tracing: false`).
- Private agents over service bindings: SDK `fetch` option → binding.
- `cloudflare.ts` entrypoint extension: `extend({ base, wrap })` for Agents SDK hooks (schedules, Sentry `wrap`).

Full references: `./reference/docs_guide_deploy_index.md`, `./reference/docs_guide_node-target_index.md`, `./reference/docs_guide_cloudflare-target_index.md`

______________________________________________________________________

## Ecosystem

**Channels (17):** Discord, Facebook/Messenger, GitHub, Google Chat, Intercom, Linear, MS Teams, Notion, Resend, Salesforce, Shopify, Slack, Stripe, Telegram, Twilio, WhatsApp, Zendesk — all blueprints (`flue add channel <name>`)

**Sandboxes:** Cloudflare Sandbox, Cloudflare Shell, Daytona, E2B, Modal, Vercel Sandbox, boxd, exe.dev, islo, Mirage, smolvm

**Deploy:** AWS, Cloudflare, Docker, Fly.io, GitHub Actions, GitLab CI/CD, Node.js, Railway, Render, SST

**Databases:** libSQL, MongoDB, MySQL, Postgres, Redis, Supabase, Turso, Valkey (driver-free, bring-your-own-driver adapters)

**Tooling:** Braintrust, OpenTelemetry, Sentry, Vitest Evals

Full reference: `./reference/docs_ecosystem_index.md`

______________________________________________________________________

## v2 Migration Cheat Sheet (from v0.x/1.x)

| Was (v0.x/1.x)                                                     | Is (v2)                                                                                       |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| `defineAgent(() => ({ model, instructions, tools, ... }))`         | `'use agent'` + exported function + hooks (`useModel`, `useTool`, …)                          |
| `defineWorkflow`, `invoke()`, run stores, `/runs/:runId`           | Removed — drive agents via `flue run`, `start()`/`init()`, SDK, or external durable engines   |
| `defineAgentProfile` / `profile`                                   | Subagents are `defineSubagent({ name, description, agent })` values                           |
| `dispatch({ input })`                                              | `dispatch({ id, message: DeliveredMessage, initialData?, uid? })`                             |
| `defineTool({ parameters, execute })`                              | `defineTool({ input, output, run({ data, signal, log }) })`, return `{ output?, terminate? }` |
| `connectMcpServer(name, opts)`                                     | `useMcpConnection(def)` / `defineMcpConnection` / `createMcpConnection`                       |
| `SKILL.md with { type: 'skill' }`                                  | Plain static `SKILL.md` import; other `.md` = text; `defineSkill` for inline                  |
| Implicit virtual sandbox                                           | Opt-in `useSandbox(...)` — no sandbox, no file/shell tools                                    |
| `registerProvider(id, opts)`                                       | `setProvider(piProvider)`; `providers: [...]` config; pi-ai `createProvider`                  |
| `flue dev` / `flue build`                                          | `vite dev` / `vite build` with `flue()` plugin from `@flue/vite`                              |
| File-based routing (`agents/`, `channels/`, named `route` exports) | Explicit `app.ts` mounts: `createAgentRouter`, `channel.route()`                              |
| `@flue/sdk` `client.agents.prompt(...)` / baseUrl                  | `createFlueClient({ url })`: `send()` + `read()`/`wait()`/`history()`                         |
| `@flue/react` `useFlueAgent({ name, id })`                         | `useFlueAgent({ url })`                                                                       |
| `flue run <name> --input '...'`                                    | `flue run <path> --message "..." [--id] [--data] [--new]`                                     |

Full before/after: `./reference/docs_guide_migration_index.md`
