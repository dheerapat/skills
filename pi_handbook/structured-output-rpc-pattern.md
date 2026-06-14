# Pi RPC + Structured Output: Server-Orchestrated Action Pattern

How to run pi in headless RPC mode, give it a custom tool that signals
"server, do something now," and orchestrate multi-turn conversations. Covers
two patterns: (1) human-in-the-loop approval, and (2) bridge server as a data
gateway where the server auto-resolves tool calls without a human.

---

## The Pattern in One Sentence

> A server spawns pi in RPC mode, injects domain data, and watches stdout for
> a custom tool call. When that tool fires, pi pauses (`terminate: true`),
> the server shows a review UI to a human, then feeds the human's decision
> back into pi as the next prompt.

---

## Architecture

```
┌──────────┐         ┌──────────────┐          ┌──────────────────┐
│  Human   │◄───────►│   Server     │◄────────►│  pi (RPC mode)   │
│  (web/   │  click  │  (your app)  │  stdin   │  --no-session    │
│  mobile) │  accept │              │  stdout  │  extension.ts    │
└──────────┘         └──────────────┘          └──────────────────┘
```

The server is the orchestrator. pi never talks to the human directly.
pi only talks to the server via stdin/stdout JSON. The server translates
between pi's protocol and the human's UI.

---

## Full Sequence (Medical Example)

```
Human                 Server                        pi (RPC)
  │                     │                              │
  │ "What medication    │                              │
  │  for this patient?" │                              │
  │────────────────────►│                              │
  │                     │ {"type":"prompt",             │
  │                     │  "message":"Patient: 45M,    │
  │                     │   BP 140/90, Hx HTN..."}     │
  │                     │─────────────────────────────►│
  │                     │                              │── agent_start
  │                     │                              │── message_update (text streaming)
  │                     │                              │── tool_execution_start
  │                     │                              │     toolName: "suggest_medication"
  │                     │                              │── tool_execution_end
  │                     │◄── result.details: {          │     result: {
  │                     │      medication, dosage,      │       details: {...},
  │                     │      reasoning, warnings      │       terminate: true
  │                     │    }                          │     }
  │   ◄── Show UI ─────│                              │── agent_end (stops here, no extra turn)
  │   Lisinopril 10mg   │                              │
  │   [Accept] [Reject] │                              │
  │                     │                              │
  │   clicks "Accept"   │                              │
  │────────────────────►│                              │
  │                     │ {"type":"prompt",             │
  │                     │  "message":"User ACCEPTED    │
  │                     │   Lisinopril 10mg. Proceed   │
  │                     │   with prescribing."}         │
  │                     │─────────────────────────────►│
  │                     │                              │── agent_start (new turn)
  │                     │                              │── continues: writes rx, checks interactions
  │                     │                              │── agent_end
  │   ◄── Show result ──│◄─────────────────────────────│
```

---

## Step 1: The Custom Tool (Extension)

Create `~/.pi/agent/extensions/suggest-medication.ts`:

```typescript
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Text } from "@earendil-works/pi-tui";
import { Type } from "typebox";

interface MedicationDetails {
  medicationName: string;
  dosage: string;
  reasoning: string;
  warnings: string[];
  alternatives?: string[];
}

const suggestMedicationTool = defineTool({
  name: "suggest_medication",
  label: "Suggest Medication",
  description:
    "Suggest a medication for the patient. The user will review and accept or reject this suggestion.",
  promptSnippet: "Suggest a medication for the patient and pause for review",
  promptGuidelines: [
    "When you determine a specific medication is indicated for the patient, call suggest_medication with your recommendation.",
    "Include your clinical reasoning and any relevant warnings or precautions.",
    "After calling suggest_medication, STOP. The user will review your suggestion and respond with accept or reject.",
    "If the user rejects, be ready to suggest an alternative medication.",
    "Do NOT write a prescription or proceed until the user has explicitly accepted.",
  ],
  parameters: Type.Object({
    medicationName: Type.String({ description: "Generic or brand name of the medication" }),
    dosage: Type.String({ description: "Dosage and frequency (e.g., '10mg once daily')" }),
    reasoning: Type.String({ description: "Clinical reasoning for this choice" }),
    warnings: Type.Array(Type.String(), {
      description: "Warnings, contraindications, or monitoring needed",
    }),
    alternatives: Type.Optional(
      Type.Array(Type.String(), {
        description: "Alternative medications if this one is rejected",
      })
    ),
  }),

  async execute(_toolCallId, params) {
    return {
      content: [
        {
          type: "text",
          text: `Suggested medication: ${params.medicationName} ${params.dosage}. Awaiting user review.`,
        },
      ],
      details: {
        medicationName: params.medicationName,
        dosage: params.dosage,
        reasoning: params.reasoning,
        warnings: params.warnings,
        alternatives: params.alternatives,
      } satisfies MedicationDetails,
      terminate: true, // <-- critical: stops the agent so the server can interject
    };
  },

  renderResult(result, _options, theme) {
    const details = result.details as MedicationDetails | undefined;
    if (!details) {
      const text = result.content[0];
      return new Text(text?.type === "text" ? text.text : "", 0, 0);
    }
    const lines = [
      theme.fg("toolTitle", theme.bold(`💊 ${details.medicationName} ${details.dosage}`)),
      "",
      theme.fg("text", details.reasoning),
      "",
      theme.fg("warning", "⚠ Warnings:"),
      ...details.warnings.map((w) => theme.fg("muted", `  • ${w}`)),
      "",
      theme.fg("muted", "Awaiting user review..."),
    ];
    return new Text(lines.join("\n"), 0, 0);
  },
});

export default function (pi: ExtensionAPI) {
  pi.registerTool(suggestMedicationTool);
}
```

**Key point:** `terminate: true` in the return value tells pi "don't ask the LLM for another
follow-up message — end the turn here." This saves one API call and lets the server take
control immediately.

---

## Step 2: The Server (RPC Client)

A minimal Python server that spawns pi, injects patient data, and handles the
accept/reject cycle:

```python
import json
import subprocess
import sys

def spawn_pi():
    """Spawn pi in RPC mode with the medication extension."""
    return subprocess.Popen(
        [
            "pi",
            "--mode", "rpc",
            "--no-session",
            "--extension", "~/.pi/agent/extensions/suggest-medication.ts",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
    )

def send(proc, command: dict):
    """Send a JSON command to pi on stdin."""
    proc.stdin.write(json.dumps(command) + "\n")
    proc.stdin.flush()

def read_events(proc):
    """Generator that yields parsed JSON events from pi's stdout."""
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        event = json.loads(line)
        yield event

def show_medication_ui(details: dict) -> str:
    """
    Show UI to the human and return "accept" or "reject".
    Replace this with your actual web/mobile UI.
    """
    print(f"\n{'='*50}")
    print(f"💊 MEDICATION SUGGESTION")
    print(f"{'='*50}")
    print(f"Medication: {details['medicationName']} {details['dosage']}")
    print(f"Reasoning:  {details['reasoning']}")
    print(f"Warnings:   {', '.join(details['warnings'])}")
    if details.get("alternatives"):
        print(f"Alternatives: {', '.join(details['alternatives'])}")
    print(f"{'='*50}")

    while True:
        choice = input("[A]ccept or [R]eject? ").strip().lower()
        if choice in ("a", "accept"):
            return "accept"
        if choice in ("r", "reject"):
            return "reject"

def main():
    proc = spawn_pi()

    # Inject patient data as the first prompt
    patient_data = """
    Patient: 45-year-old male. BP 140/90 mmHg. History of hypertension (diagnosed 2 years ago).
    Current medications: none. Allergies: none known.
    Labs: Creatinine 1.1 mg/dL, Potassium 4.2 mmol/L.
    No other significant medical history.
    What medication do you recommend for managing this patient's hypertension?
    """

    send(proc, {"type": "prompt", "message": patient_data.strip()})

    for event in read_events(proc):
        etype = event.get("type", "")

        # --- Streaming text from the LLM ---
        if etype == "message_update":
            delta = event.get("assistantMessageEvent", {}).get("delta")
            if delta:
                print(delta, end="", flush=True)

        # --- Medication suggestion fired ---
        if etype == "tool_execution_end" and event.get("toolName") == "suggest_medication":
            details = event["result"]["details"]
            decision = show_medication_ui(details)

            if decision == "accept":
                msg = (
                    f"User ACCEPTED your suggestion: {details['medicationName']} "
                    f"{details['dosage']}. Proceed with prescribing and any next steps."
                )
            else:
                msg = (
                    f"User REJECTED your suggestion: {details['medicationName']}. "
                    f"Suggest a different medication or alternative approach."
                )

            send(proc, {"type": "prompt", "message": msg})

        # --- Agent done ---
        if etype == "agent_end":
            # Could break here if you're done, or keep listening for the next turn
            # For a single interaction, break. For ongoing conversation, keep looping.
            pass

        # --- Final messages from agent ---
        if etype == "message_end":
            msg = event.get("message", {})
            role = msg.get("role")
            if role == "assistant":
                content_blocks = msg.get("content", [])
                for block in content_blocks:
                    if block.get("type") == "text":
                        print(f"\n[Assistant] {block['text']}")

    proc.stdin.close()
    proc.wait()

if __name__ == "__main__":
    main()
```

---

## Step 3: The RPC Events That Matter

| Event | What it means for the server |
|---|---|
| `tool_execution_start` | pi is about to call a tool. Check `toolName`. |
| `tool_execution_end` | Tool finished. If `toolName` matches your action tool, extract `result.details` and show UI. |
| `agent_end` | The current turn is done. If you sent a prompt and got `agent_end` with no tool call in between, the LLM answered directly. |
| `message_update` | Streaming text from the LLM. Show it to the human if desired. |

**What the server does NOT need to handle:**
- `extension_ui_request` — that's for pi extensions to prompt the RPC client. You ARE the client and have your own UI.
- `compaction_start/end` — not relevant for `--no-session` ephemeral runs.
- `turn_start/end` — `agent_end` is usually a better boundary for server-side logic.

---

## Extending the Pattern

The same architecture works for any domain where an AI suggests an action
and a human must approve it before execution:

| Domain | Tool name | Fields | Human decision |
|---|---|---|---|
| Medical | `suggest_medication` | medication, dosage, reasoning, warnings | Accept / Reject |
| Legal | `suggest_clause` | clause_text, rationale, risks | Accept / Reject / Edit |
| DevOps | `suggest_deploy` | service, version, rollback_plan | Approve / Deny |
| Finance | `suggest_trade` | symbol, quantity, reasoning | Execute / Cancel |
| Content | `suggest_post` | text, platforms, schedule | Publish / Revise |

Each follows the same pattern:
1. Custom tool with domain-specific schema
2. `terminate: true` to pause after suggestion
3. Server owns the review UI
4. Human decision fed back as next prompt

---

## Data Proxy Pattern: Bridge Server as Gateway

### The Pattern in One Sentence

> When pi needs data from an external system it can't reach directly (FHIR,
> private APIs, internal databases), the bridge server acts as a data gateway.
> pi requests data via a custom tool, and the server fulfills the request
> without human involvement.

### Two Approaches

| Factor | A: Terminate-and-Continue | B: Direct HTTP Callback |
|---|---|---|
| How it works | Tool returns `terminate: true`. Server intercepts stdout, fetches data, sends new prompt. | Tool's `execute()` calls bridge HTTP API, returns data as tool result. |
| Conversation flow | Data arrives as a user message | Data is a normal tool result |
| Latency per request | +1 round-trip (terminate → prompt) | Single HTTP call inside tool |
| Bridge agency | Bridge decides by watching stdout | Bridge responds to HTTP requests |
| Network | None beyond stdin/stdout | pi must reach bridge over HTTP |
| Sequential requests | Latency compounds per request | Normal tool chaining |

Choose A when the bridge server is on a private network pi can't reach over
HTTP, or when the server must hold all decision authority (audit, access
control, rate-limiting before every data access). Choose B for lower latency
and a cleaner LLM conversation.

### Approach A: Server-Intercepted (Terminate-and-Continue)

Same `terminate: true` mechanism as the human-in-the-loop pattern above,
but the server auto-resolves the request — no UI, no human wait.

#### Full Sequence

```
Bridge (FHIR)       Server                        pi (RPC)
  │                   │                              │
  │                   │ {"type":"prompt",             │
  │                   │  "message":"Patient 123      │
  │                   │   admitted with chest pain.  │
  │                   │   Check recent labs and      │
  │                   │   suggest treatment."}        │
  │                   │─────────────────────────────►│
  │                   │                              │── agent_start
  │                   │                              │── message_update (text streaming)
  │                   │                              │── tool_execution_start
  │                   │                              │     toolName: "fetch_patient_labs"
  │                   │                              │── tool_execution_end
  │                   │◄── result.details: {          │     result: {
  │                   │      patientId: "123",        │       details: {...},
  │                   │      resource: "Observation"  │       terminate: true
  │                   │    }                          │     }
  │   GET /Patient/   │                              │── agent_end (stops, no extra turn)
  │   123/Observation │                              │
  │◄──────────────────│                              │
  │   { labs data }   │                              │
  │──────────────────►│                              │
  │                   │ {"type":"prompt",             │
  │                   │  "message":"FHIR data for    │
  │                   │   patient 123: Troponin      │
  │                   │   0.04 ng/mL, ECG normal..."} │
  │                   │─────────────────────────────►│
  │                   │                              │── agent_start (new turn)
  │                   │                              │── analyzes labs, suggests treatment
  │                   │                              │── agent_end
```

No human sees a UI. The server sees `fetch_patient_labs` on stdout, knows it's
a data-request tool (not a human-review tool), fetches from FHIR, and feeds
the result back as the next prompt — all automatically.

#### Custom Tool

```typescript
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

interface FhirRequest {
  patientId: string;
  resource: string;
}

const fetchPatientLabsTool = defineTool({
  name: "fetch_patient_labs",
  label: "Fetch Patient Labs",
  description:
    "Request lab results or clinical data for a patient from the FHIR server via the bridge.",
  promptSnippet: "Fetch patient data from FHIR",
  promptGuidelines: [
    "When you need lab results, vitals, medications, or other clinical data for a patient, call fetch_patient_labs.",
    "Specify the patient ID and the FHIR resource type needed (e.g., Observation, MedicationRequest).",
    "After calling fetch_patient_labs, STOP. The server will provide the data.",
    "Do not fabricate lab values — always fetch them first.",
  ],
  parameters: Type.Object({
    patientId: Type.String({ description: "Patient identifier" }),
    resource: Type.String({ description: "FHIR resource type (e.g., Observation, Condition, MedicationRequest)" }),
    category: Type.Optional(Type.String({ description: "Optional filter (e.g., 'laboratory', 'vital-signs')" })),
  }),

  async execute(_toolCallId, params) {
    return {
      content: [
        {
          type: "text",
          text: `Requesting ${params.resource} data for patient ${params.patientId}. Awaiting server response.`,
        },
      ],
      details: {
        patientId: params.patientId,
        resource: params.resource,
        category: params.category,
      } satisfies FhirRequest,
      terminate: true,
    };
  },
});

export default function (pi: ExtensionAPI) {
  pi.registerTool(fetchPatientLabsTool);
}
```

#### Server Auto-Resolution Logic

The server distinguishes data-request tools from human-review tools by
checking `toolName` against a known list:

```python
# Tools that the server auto-resolves (no human needed)
DATA_REQUEST_TOOLS = {"fetch_patient_labs", "fetch_patient_meds", "lookup_guideline"}
# Tools that require human review
HUMAN_REVIEW_TOOLS = {"suggest_medication", "suggest_procedure"}

def handle_tool_execution_end(event):
    tool_name = event["toolName"]
    if tool_name in DATA_REQUEST_TOOLS:
        details = event["result"]["details"]
        data = fetch_from_fhir(details)           # auto-resolve
        send(proc, {"type": "prompt", "message":   # feed back immediately
            f"FHIR {details['resource']} for patient {details['patientId']}:\n{json.dumps(data)}"})
    elif tool_name in HUMAN_REVIEW_TOOLS:
        decision = show_review_ui(event["result"]["details"])  # wait for human
        send(proc, {"type": "prompt", "message": f"User {decision.upper()}ED. Proceed."})
```

### Approach B: Direct HTTP Callback (Tool-Driven)

The tool reaches the bridge server over HTTP from inside its `execute()` function.
The bridge exposes a REST API. No `terminate: true` needed — the tool returns
data as a normal result.

#### Full Sequence

```
Bridge (FHIR)       Server                        pi (RPC)
  │                   │                              │
  │                   │ {"type":"prompt",             │
  │                   │  "message":"Patient 123      │
  │                   │   admitted...Check labs."}    │
  │                   │─────────────────────────────►│
  │                   │                              │── agent_start
  │                   │                              │── message_update (text streaming)
  │                   │                              │── tool_execution_start
  │                   │                              │     toolName: "fetch_patient_labs"
  │◄── GET /fhir/     │                              │     execute() calls:
  │    Patient/123/   │                              │     fetch(bridgeUrl + "/fhir/...")
  │    Observation    │                              │
  │─── { labs } ────►│                              │     (HTTP, not stdout — server
  │                   │                              │      is not involved in this call)
  │                   │                              │── tool_execution_end
  │                   │◄─────────────────────────────│     result: {
  │                   │                              │       content: [labs JSON],
  │                   │                              │       details: { patientId, resource, data }
  │                   │                              │     }
  │                   │                              │── agent_end (normal)
  │                   │◄─────────────────────────────│     messages: [analysis, treatment plan]
```

Key difference: the server never sees the data request on stdout (other than
the normal `tool_execution_start/end` events). pi talks to the bridge directly.

#### Bridge Server HTTP API

A minimal FastAPI server that proxies FHIR requests:

```python
from fastapi import FastAPI, HTTPException, Header
import httpx

app = FastAPI()
FHIR_BASE = "https://fhir.example.com"

@app.get("/fhir/{resource}")
async def fhir_proxy(
    resource: str,
    patient: str,
    category: str | None = None,
    x_api_key: str = Header(...),
):
    if x_api_key != BRIDGE_API_KEY:
        raise HTTPException(status_code=403)

    params = {"patient": patient}
    if category:
        params["category"] = category

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FHIR_BASE}/{resource}",
            params=params,
            headers={"Authorization": f"Bearer {FHIR_TOKEN}"},
        )
        resp.raise_for_status()
        return resp.json()
```

#### Custom Tool

```typescript
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const fetchPatientLabsTool = defineTool({
  name: "fetch_patient_labs",
  label: "Fetch Patient Labs",
  description:
    "Fetch lab results or clinical data for a patient from the FHIR server.",
  promptSnippet: "Fetch patient data from FHIR",
  promptGuidelines: [
    "When you need lab results, vitals, medications, or other clinical data for a patient, call fetch_patient_labs.",
    "Do not fabricate lab values — always fetch them first.",
  ],
  parameters: Type.Object({
    patientId: Type.String({ description: "Patient identifier" }),
    resource: Type.String({ description: "FHIR resource type" }),
    category: Type.Optional(Type.String({ description: "Optional filter" })),
  }),

  async execute(_toolCallId, params, signal) {
    const bridgeUrl = process.env.BRIDGE_URL ?? "http://localhost:8000";
    const apiKey = process.env.BRIDGE_API_KEY ?? "";

    const url = new URL(`/fhir/${params.resource}`, bridgeUrl);
    url.searchParams.set("patient", params.patientId);
    if (params.category) url.searchParams.set("category", params.category);

    const response = await fetch(url.toString(), {
      headers: { "X-API-Key": apiKey },
      signal,
    });

    if (!response.ok) {
      throw new Error(`FHIR request failed: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();

    return {
      content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
      details: { patientId: params.patientId, resource: params.resource, data },
      // No terminate: true — pi continues automatically with the fetched data
    };
  },
});

export default function (pi: ExtensionAPI) {
  pi.registerTool(fetchPatientLabsTool);
}
```

#### Server (pi Spawner)

The server's only job: start pi with the bridge URL and API key as env vars.

```python
import subprocess, os, uuid

BRIDGE_API_KEY = str(uuid.uuid4())  # generate per-session key

proc = subprocess.Popen(
    ["pi", "--mode", "rpc", "--no-session",
     "--extension", "~/.pi/agent/extensions/fhir-data.ts"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=sys.stderr,
    text=True,
    env={**os.environ, "BRIDGE_URL": "http://localhost:8000", "BRIDGE_API_KEY": BRIDGE_API_KEY},
)

# Normal RPC event loop — no tool interception needed for data requests
```

### Extending the Data Proxy Pattern

| Domain | Tool name | Bridge backend | Data |
|---|---|---|---|
| Medical | `fetch_patient_labs` | FHIR server | Lab results, vitals, medications |
| Medical | `lookup_guideline` | Clinical guideline DB | Treatment protocols |
| Enterprise | `query_salesforce` | Salesforce API | Customer records, opportunities |
| DevOps | `fetch_deployment_status` | Kubernetes API | Pod status, logs |
| Legal | `search_precedents` | Internal case law DB | Prior rulings |

Each follows the same choice: HTTP callback when the backend is reachable,
terminate-and-continue when the server must own every data access.

---

## Caveats

### Shared (both patterns)

- **`terminate: true` is a batch-level decision.** If the LLM calls multiple tools in parallel and only one returns `terminate: true`, pi still makes the follow-up call. Every tool in the batch must be terminating.
- **The LLM might not call your tool.** If the prompt doesn't match the tool's `promptGuidelines`, the agent may answer in plain text instead. Tune your guidelines carefully.
- **pi stays running after `agent_end`.** It waits for the next command. Don't kill the process prematurely.
- **`--no-session` means no conversation history on disk.** If you need context across separate spawns, either use a session file or inject history manually in each prompt.
- **The server must handle stdout line-by-line.** pi uses JSONL (newline-delimited JSON). Do not use `readline` in Node.js — it misinterprets Unicode line separators inside JSON strings. Split on `\n` only.

### Data proxy (Approach A: terminate-and-continue)

- **Data arrives as a user message, not a tool result.** The LLM receives the fetched data as if a human pasted it. If the data is large, consider summarizing it in the server before sending, or breaking it into follow-up requests.
- **Round-trip latency stacks.** Each data request is one terminate → prompt cycle. If the LLM needs data from multiple backends, it will call one tool, wait, get data, then call the next. Pre-fetching related data on the server side reduces this.

### Data proxy (Approach B: HTTP callback)

- **Bridge must be reachable from pi's process.** If the bridge runs on a private network, pi (spawned by the server) must be able to resolve its hostname. Use `localhost` when they share a machine, or a private IP/domain otherwise.
- **Auth via env vars.** The server passes `BRIDGE_URL` and `BRIDGE_API_KEY` as environment variables. Rotate the key per session for security.
- **Tool errors propagate normally.** A failed HTTP call throws inside `execute()`, which pi reports as a tool error to the LLM. The LLM can retry or ask for guidance — unlike Approach A where the server controls the error message.
