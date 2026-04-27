---
description: Create a issue from the PRD. 
---

Break the $1 into tracer bullet issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

Slices may be 'human-in-the-loop' or 'automatic'. human-in-the-loop slices require human interaction, such as an architectural decision or a design review. automatic slices can be implemented and merged without human interaction. Prefer automatic over human-in-the-loop where possible.

# Quiz the user
Present the proposed breakdown as a numbered list. For each slice, show:

- Title: short descriptive name
- Type: human-in-the-loop / automatic
- Blocked by: which other slices (if any) must complete first
- User stories covered: which user stories from the PRD this addresses

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked as human-in-the-loop and automatic?
- Iterate until the user approves the breakdown.

# Create the issues
For each approved slice, create an issue inside folder `./issue/<task>/<issue>.md`. Use the issue body template below.
Create issues in dependency order (blockers first) so you can reference real issue numbers in the "Blocked by" field.

```markdown
# What to build
A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation.
Reference specific sections of the parent PRD rather than duplicating content.

# Acceptance criteria

- Criterion 1
- Criterion 2
- Criterion 3

# Blocked by
Blocked by # (if any)
Or "None - can start immediately" if no blockers.

# User stories addressed
Reference by number from the parent PRD:

- User story 3
- User story 7
```

Do NOT modify the parent PRD.
