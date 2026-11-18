---
description: Verify, commit on a feature branch, push, and open a PR (never merges)
argument-hint: "[optional PR title or scope]"
---

Running this command is the user's explicit request to commit, push the current feature
branch, and open a PR. It is **not** permission to merge, tag, or push to `main`.

1. `git status --short --branch`. If on `main`, create a `type/short-description` branch.
   Never stash, discard, or overwrite the user's uncommitted changes.
2. Run `/verify`. Stop if any check fails.
3. Review staged, unstaged, and untracked files separately. Stage only in-scope files by
   name (no `git add -A`). Stop if anything looks like a secret, a key, or data under `data/`.
4. Update **Where we left off** in `CLAUDE.md` if this work changes it, and stage it.
5. The user is the **sole author**: use their configured git identity, and add no
   `Co-Authored-By` trailer and no "Generated with Claude Code" line to commits or PR bodies.
   Commit with a Conventional Commit: `type(scope): description`. Types: `feat`, `fix`,
   `docs`, `refactor`, `chore`. Scopes: `infra`, `ingest`, `bronze`, `silver`, `gold`,
   `checks`, `report`, `docs`, `claude`.
6. `git push -u origin <branch>`, then `gh pr create`, filling in
   `.github/pull_request_template.md`. $ARGUMENTS
7. Report the PR URL, checks run, and anything not verified.
