Guide the user through a structured, one-question-at-a-time interview to fully define a new feature.
After reaching shared understanding, output a complete PRD summary. Do NOT write the PRD file until
the interview is done and the user confirms the summary.

---

## Step 0 — Opening question (always first)

Before anything else, ask this single opening question:

> "What feature or product area do you want to write a PRD for?
> Give me a rough description — even a few words is fine to start."

Wait for the user's answer before proceeding.

---

## Step 1 — Interview rules

Follow these rules strictly throughout the interview:

1. **One question at a time.** Never ask two questions in the same message.
2. **Provide your recommended answer** with every question, prefixed with `💡 My recommendation:`.
   Base the recommendation on the user's context so far and engineering best practices.
3. **Resolve dependencies first.** Walk the decision tree in order — don't ask about edge cases
   before you know the core scope; don't ask about success metrics before you know the goal.
4. **Be relentless.** Keep going until every section of the PRD has enough information.
   Do not stop early just because the user gave a broad answer — follow up to get specifics.
5. **Acknowledge and build.** Start each question with a one-sentence acknowledgement of
   the previous answer before asking the next question.
6. **Probe vague answers.** If an answer is too broad (e.g. "improve performance"), ask a
   follow-up to quantify or scope it before moving on.

---

## Step 2 — Question tree

Work through these branches in order. Each branch may take 1–4 questions depending on answers.
Use judgment — skip questions whose answers are already clear from context.

### Branch A: Problem & goal
- What specific problem does this feature solve? Who experiences it?
- What is the measurable outcome we want to achieve? (quantify if possible)
- Why is this the right time to build it?
- What does failure look like — what happens if we ship the wrong thing?

### Branch B: Users & scope
- Who are the primary users of this feature? (role, segment, persona)
- Are there secondary users or stakeholders who interact with it indirectly?
- What is explicitly OUT of scope for this version? (non-goals)
- Is this a v1 MVP or a more complete feature? What gets deferred?

### Branch C: Functional requirements
- Walk through the core user flow step by step — what does the user do first, then what?
- What are the key actions the system must support?
- What are the most important edge cases or error states to handle?
- Are there any business rules or constraints the system must enforce?

### Branch D: Non-functional requirements
- Are there performance requirements? (e.g. latency, throughput targets)
- Are there security, compliance, or data privacy constraints?
- What availability or reliability is expected?
- Does this need to work across specific platforms, devices, or locales?

### Branch E: Dependencies & risks
- What internal services, APIs, or teams does this feature depend on?
- What external dependencies or third-party tools are involved?
- What is the biggest technical or product risk? What would you do if it materialised?
- Is there a migration or backward-compatibility concern?

### Branch F: Success metrics
- How will we measure whether this feature succeeded post-launch?
- What is the baseline today, and what is the target after launch?
- Who owns monitoring this metric, and how is it tracked?

### Branch G: Open questions
- Is there anything still undecided or being debated that should be flagged?
- Are there assumptions baked in that we haven't validated yet?

---

## Step 3 — Shared understanding check

After completing all branches, say:

> "I think I have enough to summarise the PRD. Before I do — is there anything we haven't
> covered that you want to make sure is captured?"

Wait for their response.

---

## Step 4 — PRD summary output

Produce the full PRD summary in this structure. Use the exact section names.
Write in clear, engineering-ready language. Do NOT add waffle or filler.

```
# PRD: [Feature name]

## Problem statement
[2–3 sentences: the problem, who has it, why it matters now]

## Goals
- [Measurable goal 1]
- [Measurable goal 2]

## Non-goals
- [Explicitly out of scope item 1]

## Users
[Primary and secondary users, with context]

## User stories
| ID | As a… | I want to… | So that… | Priority |
|----|-------|------------|----------|----------|
| US-01 | … | … | … | Must / Should / Could |

## Functional requirements
### [Feature area]
- FR-01 — [Requirement]
- FR-02 — [Requirement]

## Non-functional requirements
| Category | Requirement |
|----------|-------------|
| Performance | … |
| Security | … |

## Dependencies & risks
| Item | Type | Owner | Risk |
|------|------|-------|------|
| … | … | … | Low / Med / High |

## Success metrics
| Metric | Baseline | Target | Method |
|--------|----------|--------|--------|
| … | … | … | … |

## Open questions
| # | Question | Owner |
|---|----------|-------|
| 1 | … | … |
```

After presenting the summary, ask:
> "Does this capture everything correctly? Say 'looks good' and I'll save this as your PRD markdown file,
> or tell me what to adjust."

---

## Step 5 — Save the PRD

Only after the user confirms, write the PRD to a file using the PRD template structure and present it.
