---
description: Scaffold-handoff-wait-continue workflow for collaborative implementation
---

Break work into small, logical portions. For each portion:

1. **Scaffold** — Describe what to do, where, and roughly how (the "what" not the "how"). Use a `# HANDOFF:` comment marker in the file to show where the human implements.

2. **Hand off** — Say something like: _"Implement the X logic in src/foo.ts at the HANDOFF marker, then reply 'next' to continue."_

3. **Wait** — Do not proceed until the human says they're done.

4. **Continue** — Verify the portion is done (optional quick scan), then move to the next portion.

That's it. Everything else (commands, settings, tooling) is optional cruft you can add later if the pattern needs it.
