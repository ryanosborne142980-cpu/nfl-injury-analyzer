---
name: python-code-review
description: >
  Review Python code for quality, correctness, security, and style.
  Triggered when user says "review this Python code", "code review",
  "check my Python", pastes Python snippets asking for feedback,
  or provides a .py file path for review. Use /python-code-review to invoke.
version: 1.0.0
---

# Python Code Review

You are performing a structured Python code review. Follow this framework every time.

## Step 1: Get the Code

- If `$ARGUMENTS` is a file path ending in `.py` → read the file with the Read tool
- If `$ARGUMENTS` is inline Python code → review it directly
- If `$ARGUMENTS` is empty → ask: "Please paste the Python code or provide a file path."

## Step 2: Review Across 6 Dimensions

Evaluate every submission against all six dimensions. Skip a dimension only if it truly has nothing to flag.

### 1. Correctness
- Logic bugs, off-by-one errors, wrong operator precedence
- Edge cases: empty inputs, `None`, zero, very large values
- Mutating arguments the caller doesn't expect to change
- Incorrect use of mutable default arguments (`def f(x=[])`)
- Relying on dict ordering in Python < 3.7

### 2. Security
- Hardcoded secrets, tokens, or passwords
- Shell injection via `subprocess` with `shell=True` + user input
- SQL injection via string formatting instead of parameterized queries
- `pickle`/`yaml.load` on untrusted data (unsafe deserialization)
- `eval()`/`exec()` on user-controlled strings
- Path traversal when constructing file paths from user input
- Unvalidated redirects or URLs passed to `requests`

### 3. Performance
- O(n²) nested loops where a set/dict lookup would be O(1)
- DB or I/O calls inside a loop (N+1 pattern)
- Re-computing the same value repeatedly (missing variable or `functools.lru_cache`)
- Concatenating strings in a loop (`+=`) instead of `"".join()`
- Loading an entire file into memory when streaming would work
- Unnecessary deep copies of large data structures

### 4. Pythonic Style
- PEP 8: snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants
- Use list/dict/set comprehensions where they improve clarity (not blindly)
- Prefer `with` statements for file/lock/connection management
- Use `enumerate()` instead of `range(len(x))`
- Use `zip()` instead of index-based parallel iteration
- Unpack tuples and use `_` for unused values
- Use `is` / `is not` for `None`, `True`, `False` comparisons

### 5. Maintainability
- Public functions/classes/modules missing docstrings
- Missing type hints on public API functions
- Magic numbers and strings (extract to named constants)
- Functions doing more than one thing (> ~20 lines is a smell)
- Deep nesting (> 3 levels — consider early returns or helper functions)
- Duplicate logic that should be extracted

### 6. Error Handling
- Bare `except:` or `except Exception:` without re-raise or logging
- Swallowed exceptions (catch + `pass`)
- Missing `finally` or `with` for resource cleanup
- Raising `Exception` directly instead of a specific or custom exception class
- Error messages that leak implementation details to end users

## Step 3: Output Format

Start with a one-line verdict:

```
Overall: [LOOKS GOOD | MINOR ISSUES | NEEDS WORK | BLOCKED — critical issues found]
```

Then list findings grouped by severity. Omit a severity tier if empty.

**Format for each finding:**
```
[SEVERITY] line N — Short title
Problem: What is wrong and why it matters.
Fix:
  <code snippet showing the corrected version>
```

End with a "Strengths" section acknowledging what's done well (even briefly).

---

## Severity Definitions

| Severity | When to use |
|----------|-------------|
| `[CRITICAL]` | Security vulnerability, data loss risk, or crashes in normal use |
| `[WARNING]` | Bug in edge cases, significant performance issue, swallowed exception |
| `[SUGGESTION]` | Style, readability, idiomatic improvement — non-blocking |

## Decision Guidance

- **Don't rewrite working logic** just to make it "more Pythonic" unless the readability gain is clear and the logic is equivalent.
- **Type hints**: flag absence only on public functions; skip for one-line internal helpers.
- **Docstrings**: flag absence on public APIs; skip for private/internal functions that are obvious from context.
- **Style**: if the rest of the file uses a consistent style that differs from PEP 8, note it once rather than flagging every instance.
- **Scope**: review only what was submitted. Don't speculate about code not shown.

## Common Anti-Pattern Quick Reference

| Anti-pattern | Preferred alternative |
|---|---|
| `for i in range(len(lst))` | `for i, val in enumerate(lst)` |
| `lst = []; for x in …: lst += [f(x)]` | `lst = [f(x) for x in …]` |
| `open(f)` without `with` | `with open(f) as fh:` |
| `except Exception: pass` | Log or re-raise; never swallow silently |
| `def f(x=[])` | `def f(x=None): x = x or []` |
| `subprocess.run(cmd, shell=True)` | Pass list: `subprocess.run(["cmd", arg])` |
| `"SELECT … " + user_input` | Parameterized queries: `cursor.execute(q, (val,))` |
| `yaml.load(data)` | `yaml.safe_load(data)` |
| `pickle.loads(untrusted)` | Use JSON or validate source first |
| `if x == None` | `if x is None` |