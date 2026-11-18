---
description: Record a lesson in the narrowest place it fits, without bloating CLAUDE.md
argument-hint: "<what went wrong or what to remember>"
---

Lesson: $ARGUMENTS

If no lesson was given, use the most recent correction the user made in this conversation.

**1. Is it worth keeping?** Skip it, and say so, if it was a one-off, Claude would do it
right by default, or it's already covered. If covered but ignored, sharpen the existing line.

**2. Pick the narrowest home**, first match wins:

| If the lesson... | Put it in |
|---|---|
| can be enforced mechanically (command pattern, formatting, file not to read) | `.claude/hooks/hooks.py` or `.claude/settings.json` |
| is a fact about the data (grain, quirk, key) | `docs/data_contracts.md` |
| is a design choice with trade-offs | `docs/decisions.md` |
| is a coding convention | `## Coding Standards` in `CLAUDE.md` |
| applies to all of the user's repos | `~/.claude/CLAUDE.md`: propose and ask first |
| is anything else project-wide | one line in `## Lessons` in `CLAUDE.md` |

**3. Write it tight**: one imperative line with the reason in a few words.

**4. Respect the budget**: `CLAUDE.md` under 250 lines, at most 15 lessons. If over, run
`/prune` first.

**5. Show the diff** and name the file you chose and why. Do not commit.
