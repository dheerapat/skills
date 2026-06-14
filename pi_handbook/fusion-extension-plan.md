# Pi Fusion Extension — Implementation Plan

Simulates OpenRouter's Fusion feature: a panel of models respond to the same prompt in parallel, then a judge model synthesizes their responses into a comprehensive final answer.

---

## Architecture

```
/fusion:config          → Configure panel + judge + scope + active toggle
/fusion <prompt>        → Run fusion on a prompt using the active config
```

No LLM-callable tool. User invokes fusion directly.

---

## Repository Structure

```
pi-fusion/
├── package.json          # Pi package manifest
├── extensions/
│   └── fusion.ts         # Extension entry point (single file)
└── README.md             # Usage instructions
```

Installable via:
```bash
pi install git:github.com/user/pi-fusion
```

## Config File Locations

Config files live in the user's filesystem, not the package:

| File | Purpose |
|---|---|
| `~/.pi/agent/fusion.json` | Global config (user scope) |
| `.pi/fusion.json` | Project config (overrides global) |

## package.json

```json
{
  "name": "pi-fusion",
  "version": "1.0.0",
  "description": "Query a panel of models in parallel, then synthesize responses with a judge model — simulates OpenRouter Fusion",
  "keywords": ["pi-package"],
  "pi": {
    "extensions": ["./extensions"]
  },
  "peerDependencies": {
    "@earendil-works/pi-coding-agent": "*",
    "@earendil-works/pi-ai": "*",
    "@earendil-works/pi-tui": "*",
    "typebox": "*"
  }
}
```

- `pi-package` keyword enables discoverability on [pi.dev/packages](https://pi.dev/packages)
- `peerDependencies` lists Pi's bundled packages (not bundled in this repo)
- No `dependencies` — only uses Pi's built-in packages + Node.js built-ins

---

## Config File Format

```json
{
  "active": true,
  "panel": [
    {
      "provider": "google",
      "modelId": "gemini-3-flash-preview",
      "modelName": "Gemini 3 Flash"
    },
    {
      "provider": "deepseek",
      "modelId": "deepseek-v4-pro",
      "modelName": "DeepSeek V4 Pro"
    }
  ],
  "judge": {
    "provider": "opencode-go",
    "modelId": "deepseek-v4-pro",
    "modelName": "DeepSeek V4 Pro"
  }
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `active` | `boolean` | Whether this config is active. `/fusion` only runs when `active: true` |
| `panel` | `array` | List of models to query in parallel (min 1) |
| `panel[].provider` | `string` | Provider name (e.g., `"google"`, `"opencode-go"`) |
| `panel[].modelId` | `string` | Model ID (e.g., `"gemini-3-flash-preview"`) |
| `panel[].modelName` | `string` | Display name (e.g., `"Gemini 3 Flash"`) |
| `judge` | `object` | The model that synthesizes panel responses |
| `judge.provider` | `string` | Provider name |
| `judge.modelId` | `string` | Model ID |
| `judge.modelName` | `string` | Display name |

### Resolution

1. If `.pi/fusion.json` exists in the project → use it
2. Otherwise → use `~/.pi/agent/fusion.json`
3. If neither exists → `/fusion` tells user to run `/fusion:config` first

---

## Commands

### `/fusion:config`

Opens a custom TUI component to configure fusion settings.

**UI Layout:**

```
┌─ Fusion Config ──────────────────────────────┐
│                                               │
│  Status: ● Active  ○ Disabled                 │
│  Scope:  ● Global  ○ Project                  │
│                                               │
│  Panel Models:                                │
│  • google/gemini-3-flash-preview     [remove] │
│  • moonshotai/kimi-k2.6              [remove] │
│  [+ Add Model]                                │
│                                               │
│  Judge: opencode-go/deepseek-v4-pro  [change] │
│                                               │
│  [Save]  [Cancel]                             │
└───────────────────────────────────────────────┘
```

**Behavior:**

- **Status (Active/Disabled):** Toggle with Enter. Controls the `active` field in JSON.
- **Scope (Global/Project):** Toggle with Enter. Determines which file to write to:
  - Global → `~/.pi/agent/fusion.json`
  - Project → `.pi/fusion.json`
- **Panel Models:** Shows current selections with `[remove]` option. `[+ Add Model]` opens a `SelectList` of available models from `ctx.modelRegistry.getAvailable()`.
- **Judge:** Shows current judge model with `[change]` option. Opens same `SelectList`.
- **Save:** Writes config to the selected scope's JSON file (creates directory if needed).
- **Cancel:** Discards changes.

**Model selection source:** `ctx.modelRegistry.getAvailable()` — only models with configured API keys appear.

**On open:** Loads existing config from project file (priority) or global file to pre-fill the UI.

---

### `/fusion <prompt>`

Runs the fusion pipeline on the given prompt.

**Flow:**

```
1. Load config
   ├─ .pi/fusion.json exists? → use it
   └─ else → use ~/.pi/agent/fusion.json
   
2. Validate
   ├─ No config? → notify "No fusion config. Run /fusion:config"
   ├─ active: false? → notify "Fusion is disabled. Run /fusion:config"
   └─ panel empty? → notify "No panel models configured"
   
3. Dispatch to panel (parallel, max 4 concurrent)
   │
   ├─ For each panel model:
   │   ├─ ctx.modelRegistry.find(provider, modelId)
   │   ├─ ctx.modelRegistry.getApiKeyAndHeaders(model)
   │   └─ complete(model, { messages: [{ role: "user", content: prompt }] }, { apiKey, headers })
   │
   └─ Collect: response text + usage stats per model

4. Build synthesis prompt for judge
   │
   │  "You are a judge synthesizing responses from multiple AI models.
   │   Analyze the following responses for:
   │   - Consensus points (what all models agree on)
   │   - Contradictions (where models disagree)
   │   - Unique insights (valuable points only one model made)
   │   - Blind spots (important aspects all models missed)
   │   
   │   Then produce a comprehensive final answer that integrates
   │   the best of all perspectives.
   │   
   │   --- Panel Responses ---
   │   [Model A]: ...
   │   [Model B]: ...
   │   [Model C]: ..."
   
5. Call judge model
   │
   └─ complete(judgeModel, { messages: [{ role: "user", content: synthesisPrompt }] }, { apiKey, headers })

6. Render result in TUI
```

**Rendering:**

Collapsed view (default):
```
✓ Fusion · 3 panel models · judge: DeepSeek V4 Pro
  Key finding: All models agree carbon taxes reduce emissions
  efficiently but disagree on optimal revenue recycling...
  (Ctrl+O to expand)
```

Expanded view (Ctrl+O):
```
┌─ Fusion Result ──────────────────────────────┐
│ Panel: Gemini 3 Flash, Kimi K2.6, DeepSeek   │
│ Judge: DeepSeek V4 Pro                        │
│                                               │
│ ── Consensus ──                               │
│ • Carbon taxes are economically efficient     │
│                                               │
│ ── Contradictions ──                          │
│ • Gemini: dividend approach                   │
│ • DeepSeek: green investment                  │
│                                               │
│ ── Unique Insights ──                         │
│ • Kimi: border adjustment mechanisms          │
│                                               │
│ ── Blind Spots ──                             │
│ • None addressed developing nations           │
│                                               │
│ ── Final Answer ──                            │
│ [judge's comprehensive synthesis...]          │
│                                               │
│ Usage: ↑12K ↓8K $0.023                        │
└───────────────────────────────────────────────┘
```

---

## Extension Implementation

**File:** `extensions/fusion.ts` (inside the `pi-fusion` repo)

At runtime, Pi loads this from the installed package directory (e.g., `~/.pi/agent/git/github.com/user/pi-fusion/extensions/fusion.ts`).

### Imports

```typescript
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import type { ExtensionAPI, ExtensionCommandContext } from "@earendil-works/pi-coding-agent";
import { getAgentDir, getMarkdownTheme, DynamicBorder } from "@earendil-works/pi-coding-agent";
import { type Model, type Api, complete } from "@earendil-works/pi-ai";
import { Container, Markdown, SelectList, type SelectItem, Spacer, Text } from "@earendil-works/pi-tui";
```

### Data Types

```typescript
interface ModelRef {
  provider: string;
  modelId: string;
  modelName: string;
}

interface FusionConfig {
  active: boolean;
  panel: ModelRef[];
  judge: ModelRef;
}
```

### Extension Structure

```
export default function (pi: ExtensionAPI) {
  // ── State ──
  // In-memory config (loaded from file on session_start)
  // No session persistence needed — file is authoritative
  
  // ── Helpers ──
  // loadConfig(cwd): FusionConfig | null
  //   Tries .pi/fusion.json first, then ~/.pi/agent/fusion.json
  
  // saveConfig(cwd, scope, config): void
  //   Writes to .pi/fusion.json (project) or ~/.pi/agent/fusion.json (global)
  
  // ── /fusion:config ──
  // pi.registerCommand("fusion:config", { ... })
  //   Opens custom TUI:
  //     - Toggle active/disabled
  //     - Toggle global/project scope
  //     - List panel models with add/remove
  //     - Select judge model
  //     - Save/Cancel
  //
  //   Uses SelectList for model picking
  //   Uses custom Container + Text for the config display
  
  // ── /fusion ──
  // pi.registerCommand("fusion", { ... })
  //   1. Load config from file
  //   2. Validate
  //   3. Map panel models → complete() in parallel (Promise.all with concurrency 4)
  //   4. Build synthesis prompt
  //   5. Call judge model
  //   6. Show result in custom TUI (Container + Markdown)
  
  // ── session_start ──
  // Load config to populate in-memory state
}
```

### Key Implementation Details

**Parallel execution with concurrency limit:**

```typescript
async function runWithConcurrency<T, R>(
  items: T[],
  limit: number,
  fn: (item: T, i: number) => Promise<R>
): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let next = 0;
  const workers = Array(limit).fill(null).map(async () => {
    while (next < items.length) {
      const i = next++;
      results[i] = await fn(items[i], i);
    }
  });
  await Promise.all(workers);
  return results;
}
```

**Calling a model:**

```typescript
async function callModel(
  model: Model<Api>,
  prompt: string,
  ctx: ExtensionCommandContext
): Promise<{ text: string; usage: { input: number; output: number; cost: number } }> {
  const auth = await ctx.modelRegistry.getApiKeyAndHeaders(model);
  if (!auth.ok) throw new Error(auth.error);
  
  const response = await complete(
    model,
    { messages: [{ role: "user", content: [{ type: "text", text: prompt }], timestamp: Date.now() }] },
    { apiKey: auth.apiKey, headers: auth.headers }
  );
  
  const text = response.content
    .filter((c): c is { type: "text"; text: string } => c.type === "text")
    .map(c => c.text)
    .join("\n");
  
  return {
    text,
    usage: {
      input: response.usage?.input ?? 0,
      output: response.usage?.output ?? 0,
      cost: response.usage?.cost?.total ?? 0,
    },
  };
}
```

**Synthesis prompt template:**

```typescript
function buildSynthesisPrompt(prompt: string, responses: Array<{ model: string; text: string }>): string {
  const responsesBlock = responses
    .map(r => `### ${r.model}\n\n${r.text}`)
    .join("\n\n---\n\n");
  
  return [
    "You are a judge synthesizing responses from multiple AI models to the same question.",
    "",
    "Analyze the following responses and identify:",
    "- **Consensus points**: what all models agree on",
    "- **Contradictions**: where models disagree, and the nature of the disagreement",
    "- **Unique insights**: valuable points or perspectives only one model made",
    "- **Blind spots**: important aspects, considerations, or angles that all models missed",
    "",
    "Then produce a comprehensive final answer that integrates the best of all perspectives,",
    "resolves contradictions where possible, and fills in blind spots.",
    "",
    "---",
    "",
    `**Original question:** ${prompt}`,
    "",
    "---",
    "",
    "**Panel responses:**",
    "",
    responsesBlock,
    "",
    "---",
    "",
    "Now provide your synthesis. Structure your response with clear sections",
    "for Consensus, Contradictions, Unique Insights, Blind Spots, and Final Answer.",
  ].join("\n");
}
```

### TUI Rendering (Fusion Result)

```typescript
function showFusionResult(
  result: {
    prompt: string;
    panelResults: Array<{ model: string; text: string; usage: {...} }>;
    synthesis: string;
    totalUsage: { input: number; output: number; cost: number };
  },
  ctx: ExtensionCommandContext
): Promise<void> {
  // Use ctx.ui.custom() with Container + Markdown to render:
  // - Header with panel models and judge
  // - Consensus section
  // - Contradictions section
  // - Unique Insights section
  // - Blind Spots section
  // - Final Answer (Markdown rendered)
  // - Usage stats
}
```

---

## Edge Cases

| Case | Behavior |
|---|---|
| No config file exists | `/fusion` notifies: "No fusion config. Run /fusion:config first" |
| `active: false` | `/fusion` notifies: "Fusion is disabled. Run /fusion:config to enable" |
| Panel empty | `/fusion` notifies: "No panel models configured" |
| Model no longer available | Skip with warning, continue with remaining panel models |
| API key missing for model | Skip with warning, continue with remaining panel models |
| All panel models fail | Return error: "All panel models failed" |
| Judge model fails | Return error with panel results shown but no synthesis |
| Single panel model | Still run fusion (synthesis adds value via structured analysis) |
| Concurrency > panel size | Clamp to panel size |

---

## What's NOT Included

- ❌ No LLM-callable tool (user invokes `/fusion` directly)
- ❌ No multiple named configs (just one active config)
- ❌ No chained/sequential panel mode
- ❌ No web search integration
- ❌ No session persistence for config (file is authoritative)
- ❌ No CLI flag for fusion
- ❌ No npm dependencies (uses only Pi's bundled packages)

---

## Installation & Usage

```bash
# Install from GitHub
pi install git:github.com/user/pi-fusion

# Configure (pick panel models + judge)
/fusion:config

# Run fusion on a prompt
/fusion What are the strongest arguments for and against carbon taxes?
```

## Estimated Size

~250 lines in a single `extensions/fusion.ts` file. Total repo: 4 files (package.json, extensions/fusion.ts, README.md, .gitignore).
