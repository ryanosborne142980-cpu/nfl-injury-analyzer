---
description: Shrink CLAUDE.md back under budget without losing what matters
---

Budget: `CLAUDE.md` under 250 lines, at most 15 entries in `## Lessons`.

1. Report the current line count and number of lessons.
2. For each line, decide: **Delete** (default behavior, obsolete, or duplicate), **Merge**
   (shared root cause), **Move** (data fact → `docs/data_contracts.md`, design choice →
   `docs/decisions.md`, enforceable → `.claude/hooks/hooks.py`), **Promote** (a proven
   lesson becomes a line in its section), or **Keep**.
3. Trim **Where we left off** to current state only; finished history lives in git.
4. Present a table (line, action, reason) and **wait for approval**. Never drop a Do's and
   Don'ts safety rule without explicit approval.
5. Apply approved changes, show the diff and new counts. Do not commit.
