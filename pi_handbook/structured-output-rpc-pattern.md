# Clinical AI Agent: FHIR-Backed Chat with Human-in-the-Loop Actions

A server-orchestrated system where users chat with an LLM that has real-time
access to patient data from a FHIR server. The LLM can request clinical data
mid-conversation and suggest actions (medications, procedures, orders) for
human approval before execution.

______________________________________________________________________

## Architecture

```
 ┌──────────┐        ┌─────────────────┐        ┌──────────────┐
 │   User   │◄──────►│  Agent Server   │◄──────►│  pi (RPC)    │
 │  (chat   │  web   │  (orchestrator) │ stdin  │  --no-session│
 │   UI)    │        │                 │ stdout │  extensions/ │
 └──────────┘        └───────┬─────────┘        └──────────────┘
                             │
                             │ HTTP (proxy)
                             ▼
                    ┌─────────────────┐
                    │  FHIR Server    │
                    │  (patient data) │
                    └─────────────────┘
```

The Agent Server is the central piece. It spawns pi in RPC mode, watches
stdout for tool calls, and handles two types of tools differently:

- **Data-fetch tools** (`fetch_patient_data`) → server auto-resolves by
  querying FHIR, feeds data back as a prompt. No human wait.
- **Action-suggestion tools** (`suggest_clinical_action`) → server shows the
  suggestion to the user in a review UI, waits for accept/reject, then feeds
  the decision back.

______________________________________________________________________

## The Two Tool Types

Both return `terminate: true` to pause pi so the server can interject.
The server tells them apart by `toolName`.

| Tool                      | Purpose                                               | Server behavior                                      | `terminate: true` |
| ------------------------- | ----------------------------------------------------- | ---------------------------------------------------- | ----------------- |
| `fetch_patient_data`      | Pull patient labs, vitals, meds, conditions from FHIR | Auto-resolve: query FHIR, feed data back immediately | Yes               |
| `suggest_clinical_action` | Propose a medication, procedure, or order             | Show review UI, wait for human accept/reject         | Yes               |

______________________________________________________________________

## Custom Tool: `fetch_patient_data`

Requests clinical data from FHIR. The LLM calls this whenever it needs
real patient context — it should never fabricate values.

**File:** `~/.pi/agent/extensions/clinical-data.ts`

```typescript
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const fetchPatientDataTool = defineTool({
  name: "fetch_patient_data",
  label: "Fetch Patient Data",
  description:
    "Request patient clinical data from the FHIR server via the agent server.",
  promptSnippet: "Fetch patient data from FHIR",
  promptGuidelines: [
    "When you need lab results, vitals, medications, conditions, or any clinical data for a patient, call fetch_patient_data.",
    "Specify what data you need (lab-results, vital-signs, medications, conditions, allergies, etc.).",
    "After calling fetch_patient_data, STOP. The server will provide the data.",
    "Do NOT fabricate or guess clinical values — always fetch them first.",
  ],
  parameters: Type.Object({
    patientId: Type.String({ description: "Patient identifier" }),
    dataTypes: Type.Array(Type.String(), {
      description:
        "Types of data needed: 'lab-results', 'vital-signs', 'medications', 'conditions', 'allergies', 'procedures'",
    }),
    lookbackDays: Type.Optional(
      Type.Number({ description: "How many days of history to fetch (default: 90)" })
    ),
  }),

  async execute(_toolCallId, params) {
    return {
      content: [
        {
          type: "text",
          text: `Requesting ${params.dataTypes.join(", ")} for patient ${params.patientId}. Awaiting server response.`,
        },
      ],
      details: {
        patientId: params.patientId,
        dataTypes: params.dataTypes,
        lookbackDays: params.lookbackDays ?? 90,
      },
      terminate: true,
    };
  },
});

export default function (pi: ExtensionAPI) {
  pi.registerTool(fetchPatientDataTool);
}
```

______________________________________________________________________

## Custom Tool: `suggest_clinical_action`

The LLM calls this when it determines a specific clinical action is indicated
(medication, procedure, lab order, referral). The user must approve before
the action proceeds.

**File:** `~/.pi/agent/extensions/clinical-actions.ts`

```typescript
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Text } from "@earendil-works/pi-tui";
import { Type } from "typebox";

interface ActionDetails {
  actionType: string;
  description: string;
  reasoning: string;
  warnings: string[];
  alternatives?: string[];
}

const suggestActionTool = defineTool({
  name: "suggest_clinical_action",
  label: "Suggest Clinical Action",
  description:
    "Suggest a clinical action for the patient. The user will review and accept or reject it.",
  promptSnippet: "Suggest a clinical action and pause for review",
  promptGuidelines: [
    "When you determine a specific clinical action is indicated, call suggest_clinical_action.",
    "Include your clinical reasoning and any relevant warnings or precautions.",
    "After calling suggest_clinical_action, STOP. The user will review and respond.",
    "If the user rejects, be ready to suggest an alternative.",
    "Do NOT assume approval — wait for the user's explicit acceptance.",
  ],
  parameters: Type.Object({
    actionType: Type.String({
      description: "Type of action: 'medication', 'procedure', 'lab_order', 'referral', 'imaging'",
    }),
    description: Type.String({
      description: "Detailed description (e.g., 'Lisinopril 10mg once daily')",
    }),
    reasoning: Type.String({ description: "Clinical reasoning for this suggestion" }),
    warnings: Type.Array(Type.String(), {
      description: "Warnings, contraindications, or monitoring required",
    }),
    alternatives: Type.Optional(
      Type.Array(Type.String(), {
        description: "Alternative actions if this one is rejected",
      })
    ),
  }),

  async execute(_toolCallId, params) {
    return {
      content: [
        {
          type: "text",
          text: `Suggested ${params.actionType}: ${params.description}. Awaiting user review.`,
        },
      ],
      details: {
        actionType: params.actionType,
        description: params.description,
        reasoning: params.reasoning,
        warnings: params.warnings,
        alternatives: params.alternatives,
      } satisfies ActionDetails,
      terminate: true,
    };
  },

  renderResult(result, _options, theme) {
    const details = result.details as ActionDetails | undefined;
    if (!details) {
      const text = result.content[0];
      return new Text(text?.type === "text" ? text.text : "", 0, 0);
    }
    const emoji: Record<string, string> = {
      medication: "💊",
      procedure: "🏥",
      lab_order: "🧪",
      referral: "📋",
      imaging: "🩻",
    };
    const icon = emoji[details.actionType] ?? "📌";
    const lines = [
      theme.fg("toolTitle", theme.bold(`${icon} ${details.actionType.toUpperCase()}: ${details.description}`)),
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
  pi.registerTool(suggestActionTool);
}
```

______________________________________________________________________

## The Agent Server

Spawns pi in RPC mode, proxies FHIR requests, and manages the human
review loop for clinical actions. This is the orchestrator.

```python
import json
import subprocess
import sys
import httpx
from typing import Generator


FHIR_BASE = "https://fhir.example.com"
FHIR_TOKEN = "your-fhir-bearer-token"

# --- Tool classification ---
DATA_TOOLS = {"fetch_patient_data"}
ACTION_TOOLS = {"suggest_clinical_action"}


def spawn_pi():
    """Spawn pi in RPC mode with both extensions loaded."""
    return subprocess.Popen(
        [
            "pi",
            "--mode", "rpc",
            "--no-session",
            "--extension", "~/.pi/agent/extensions/clinical-data.ts",
            "--extension", "~/.pi/agent/extensions/clinical-actions.ts",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
    )


def send(proc, command: dict):
    proc.stdin.write(json.dumps(command) + "\n")
    proc.stdin.flush()


def read_events(proc) -> Generator[dict, None, None]:
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


# --- FHIR proxy ---
def fetch_fhir(patient_id: str, data_types: list[str], lookback_days: int) -> dict:
    """Query the FHIR server for the requested data types."""
    results = {}
    fhir_type_map = {
        "lab-results": "Observation?category=laboratory",
        "vital-signs": "Observation?category=vital-signs",
        "medications": "MedicationRequest",
        "conditions": "Condition",
        "allergies": "AllergyIntolerance",
        "procedures": "Procedure",
    }
    for dt in data_types:
        endpoint = fhir_type_map.get(dt)
        if not endpoint:
            results[dt] = {"error": f"Unknown data type: {dt}"}
            continue
        url = f"{FHIR_BASE}/{endpoint}&patient={patient_id}"
        resp = httpx.get(
            url,
            headers={"Authorization": f"Bearer {FHIR_TOKEN}"},
        )
        resp.raise_for_status()
        bundle = resp.json()
        # Extract readable summary from the bundle
        results[dt] = _summarize_bundle(bundle, dt)
    return results


def _summarize_bundle(bundle: dict, data_type: str) -> list[dict]:
    """Extract key fields from a FHIR bundle into a readable summary."""
    entries = bundle.get("entry", [])
    summaries = []
    for entry in entries:
        resource = entry.get("resource", {})
        if data_type == "lab-results":
            code = resource.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
            value = resource.get("valueQuantity", {})
            summaries.append({
                "test": code,
                "value": f"{value.get('value')} {value.get('unit', '')}",
                "date": resource.get("effectiveDateTime", ""),
            })
        elif data_type == "vital-signs":
            code = resource.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
            value = resource.get("valueQuantity", {})
            summaries.append({
                "vital": code,
                "value": f"{value.get('value')} {value.get('unit', '')}",
                "date": resource.get("effectiveDateTime", ""),
            })
        elif data_type == "medications":
            med = resource.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display", "Unknown")
            summaries.append({"medication": med})
        elif data_type == "conditions":
            code = resource.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
            summaries.append({"condition": code, "status": resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")})
        elif data_type == "allergies":
            code = resource.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
            summaries.append({"allergy": code})
        elif data_type == "procedures":
            code = resource.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
            summaries.append({"procedure": code, "date": resource.get("performedDateTime", "")})
    return summaries


# --- Human review UI ---
def show_review_ui(details: dict) -> str:
    """Show the suggested action to the user and return 'accept' or 'reject'."""
    print(f"\n{'='*50}")
    print(f"🩺 CLINICAL ACTION SUGGESTION")
    print(f"{'='*50}")
    print(f"Action:      {details['actionType'].upper()}")
    print(f"Description: {details['description']}")
    print(f"Reasoning:   {details['reasoning']}")
    print(f"Warnings:    {', '.join(details['warnings'])}")
    if details.get("alternatives"):
        print(f"Alternatives: {', '.join(details['alternatives'])}")
    print(f"{'='*50}")

    while True:
        choice = input("[A]ccept or [R]eject? ").strip().lower()
        if choice in ("a", "accept"):
            return "accept"
        if choice in ("r", "reject"):
            return "reject"


# --- Main loop ---
def main():
    proc = spawn_pi()

    # First prompt: introduce the patient
    patient_id = "123"
    initial_prompt = f"""
    Patient ID: {patient_id}
    The user is a clinician reviewing this patient's case.
    Fetch the patient's relevant clinical data to provide context,
    then be ready to answer questions and suggest clinical actions
    based on the data and the conversation.
    """

    send(proc, {"type": "prompt", "message": initial_prompt.strip()})

    # Event loop
    for event in read_events(proc):
        etype = event.get("type", "")

        # Stream LLM text to the user
        if etype == "message_update":
            delta = event.get("assistantMessageEvent", {}).get("delta")
            if delta:
                print(delta, end="", flush=True)

        # Tool execution complete — the key interception point
        if etype == "tool_execution_end":
            tool_name = event.get("toolName", "")
            details = event.get("result", {}).get("details", {})

            if tool_name in DATA_TOOLS:
                # Auto-resolve: fetch from FHIR, feed back immediately
                data = fetch_fhir(
                    details["patientId"],
                    details["dataTypes"],
                    details.get("lookbackDays", 90),
                )
                response = (
                    f"FHIR data for patient {details['patientId']}:\n"
                    f"{json.dumps(data, indent=2)}\n\n"
                    f"Use this data to inform your clinical reasoning."
                )
                send(proc, {"type": "prompt", "message": response})

            elif tool_name in ACTION_TOOLS:
                # Human review: show UI, wait for decision
                decision = show_review_ui(details)
                action_desc = details["description"]
                if decision == "accept":
                    msg = (
                        f"User ACCEPTED your suggestion: {action_desc}. "
                        f"Proceed with documentation and any next steps."
                    )
                else:
                    msg = (
                        f"User REJECTED your suggestion: {action_desc}. "
                        f"Suggest a different approach or alternative action."
                    )
                send(proc, {"type": "prompt", "message": msg})

        # Final assistant message text (printed after streaming)
        if etype == "message_end":
            msg = event.get("message", {})
            if msg.get("role") == "assistant":
                for block in msg.get("content", []):
                    if block.get("type") == "text":
                        print(f"\n[Agent] {block['text']}")

    proc.stdin.close()
    proc.wait()


if __name__ == "__main__":
    main()
```

______________________________________________________________________

## RPC Events the Server Watches

| Event                                               | What to do                                         |
| --------------------------------------------------- | -------------------------------------------------- |
| `message_update`                                    | Stream delta text to the user's chat UI            |
| `tool_execution_end` + `toolName` in `DATA_TOOLS`   | Fetch from FHIR, feed data back as a prompt        |
| `tool_execution_end` + `toolName` in `ACTION_TOOLS` | Show review UI, wait for human, feed decision back |
| `message_end`                                       | Display final assistant message text               |

Events the server can ignore: `agent_start`, `turn_start`, `turn_end`,
`extension_ui_request`, `compaction_start/end`.

______________________________________________________________________

## Full Conversation Flow

```
 User                  Agent Server                  pi (RPC)              FHIR
  │                        │                           │                     │
  │ "Review patient 123"   │                           │                     │
  │───────────────────────►│                           │                     │
  │                        │ prompt: "Patient 123..."  │                     │
  │                        │──────────────────────────►│                     │
  │                        │                           │── fetch_patient_data │
  │                        │◄── tool_execution_end ────│   (terminate: true) │
  │                        │                           │                     │
  │                        │ GET /Observation?...      │                     │
  │                        │────────────────────────────────────────────────►│
  │                        │◄─── labs, vitals, meds ─────────────────────────│
  │                        │                           │                     │
  │                        │ prompt: "FHIR data: {...}"│                     │
  │                        │──────────────────────────►│                     │
  │  ◄── "Patient has      │                           │                     │
  │   HTN, BP 140/90,      │◄── message_update ────────│                     │
  │   no current meds..."  │                           │                     │
  │                        │                           │── suggest_clinical   │
  │                        │◄── tool_execution_end ────│   _action            │
  │                        │                           │   (terminate: true)  │
  │  ◄── "Suggest:          │                           │                     │
  │   Lisinopril 10mg"     │                           │                     │
  │  [Accept] [Reject]     │                           │                     │
  │                        │                           │                     │
  │  clicks "Accept"       │                           │                     │
  │───────────────────────►│                           │                     │
  │                        │ prompt: "User ACCEPTED"   │                     │
  │                        │──────────────────────────►│                     │
  │  ◄── "Documenting      │                           │                     │
  │   prescription..."     │◄── message_update ────────│                     │
```

The cycle can repeat: the LLM may fetch more data, suggest more actions, or
answer questions — all with the server mediating between pi, FHIR, and the user.

______________________________________________________________________

## Caveats

- **`terminate: true` is batch-level.** If the LLM fires multiple tools in
  parallel and only one returns `terminate: true`, pi still makes a follow-up
  call. Ensure all tools in a batch are terminating.
- **The LLM might not call your tool.** If the prompt doesn't match the tool's
  `promptGuidelines`, the agent may answer in plain text. Tune your guidelines
  and test with representative prompts.
- **pi stays running after `agent_end`.** It waits for the next command.
  Don't kill the process prematurely.
- **`--no-session` means no disk history.** If you need context across
  separate spawns, inject history manually in each prompt.
- **Parse stdout as JSONL.** Split on `\n` only — do not use Node.js
  `readline` which can misinterpret Unicode inside JSON strings.
- **Data arrives as user messages, not tool results.** When the server feeds
  FHIR data back via `prompt`, the LLM sees it as if a human pasted it.
  Summarize large payloads on the server side to avoid overwhelming context.
- **Sequential data fetches add latency.** Each fetch is one
  terminate → prompt round-trip. If the LLM needs multiple data types,
  it will serially call `fetch_patient_data` → wait → get data → call again.
  Pre-fetch common data bundles on the server side to reduce this.

______________________________________________________________________

## Adapting to Other Domains

The same architecture — a server that spawns pi in RPC mode, proxies data
from a backend, and gates actions behind human review — applies to any domain
where an AI needs real data context and must not act without approval.

For each domain, define two tool types following the same pattern:

- **Data-fetch tool** — lets the LLM pull live context from the backend.
  Server auto-resolves, no human wait.
- **Action-suggestion tool** — proposes a consequential action.
  Server shows review UI, waits for human accept/reject.

| Domain     | Data tool                 | Action tool               | Backend                              | Human decision                               |
| ---------- | ------------------------- | ------------------------- | ------------------------------------ | -------------------------------------------- |
| Clinical   | `fetch_patient_data`      | `suggest_clinical_action` | FHIR server (labs, meds, conditions) | Accept / Reject medication, procedure, order |
| Legal      | `lookup_precedents`       | `suggest_clause`          | Internal case law DB                 | Accept / Reject / Edit clause text           |
| DevOps     | `fetch_deployment_status` | `suggest_deploy`          | Kubernetes API, CI/CD                | Approve / Deny deployment                    |
| Finance    | `query_portfolio`         | `suggest_trade`           | Market data API, portfolio DB        | Execute / Cancel trade                       |
| Enterprise | `query_salesforce`        | `suggest_outreach`        | Salesforce API                       | Approve / Revise customer communication      |
| Security   | `fetch_threat_intel`      | `suggest_mitigation`      | SIEM, threat feeds                   | Apply / Escalate / Dismiss                   |

### What changes per domain

The server code changes in three places — the rest stays identical:

1. **Tool registration** (`DATA_TOOLS` / `ACTION_TOOLS` sets) — add your tool names
1. **Data-fetch handler** — swap `fetch_fhir()` for your backend query logic
1. **Review UI** — replace `show_review_ui()` with your domain's approval interface

The pi extension tools follow the same template: `defineTool` with a
domain-specific schema, `terminate: true` in the return value, and
`promptGuidelines` that steer the LLM toward calling the tool at the right time.
