@AGENTS.md

## Claude Code subagents

Project subagents live in `.claude/agents/` and follow the same `AGENTS.md` rules.

- `git-workflow`: delegate Git work to it, such as reviewing repository state, preparing commits or pull requests, resolving merge conflicts, and handling releases. Delegating does not grant permission to commit, push, merge, or tag. The user must still ask for each of those actions explicitly.

Handle small, single-file questions directly rather than spawning an agent.
