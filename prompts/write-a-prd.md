---
description: Create a PRD from the discussion with user. 
---

Once you have a complete understanding of the problem and solution, use the template below to write the PRD. Save it as named `<task>-prd.md`

```markdown
# Problem Statement
The problem that the user is facing, from the user's perspective.

# Solution
The solution to the problem, from the user's perspective.

# User Stories
A LONG, numbered list of user stories. Each user story should be in the format of:
1. As an , I want a , so that
This list of user stories should be extremely extensive and cover all aspects of the feature.

# Implementation Decisions
A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

# Testing Decisions
A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

# Out of Scope
A description of the things that are out of scope for this PRD.

# Further Notes
Any further notes about the feature.
```
