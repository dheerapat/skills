# Pi RPC + Structured Output: Server-Orchestrated Action Pattern

How to run pi in headless RPC mode, give it a custom tool that signals
"server, do something now," and orchestrate a multi-turn conversation where a
human reviews and approves AI suggestions before the server acts on them.

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

## Caveats

- **`terminate: true` is a batch-level decision.** If the LLM calls multiple tools in parallel and only one returns `terminate: true`, pi still makes the follow-up call. Every tool in the batch must be terminating.
- **The LLM might not call your tool.** If the prompt doesn't match the tool's `promptGuidelines`, the agent may answer in plain text instead. Tune your guidelines carefully.
- **pi stays running after `agent_end`.** It waits for the next command. Don't kill the process prematurely.
- **`--no-session` means no conversation history on disk.** If you need context across separate spawns, either use a session file or inject history manually in each prompt.
- **The server must handle stdout line-by-line.** pi uses JSONL (newline-delimited JSON). Do not use `readline` in Node.js — it misinterprets Unicode line separators inside JSON strings. Split on `\n` only.
