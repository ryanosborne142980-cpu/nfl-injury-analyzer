---
name: python-code-reviewer
description: >
  Review Python source for correctness, security, performance, style,
  scalability, reusability, maintainability, and error handling. Use when asked
  to review Python code, check Python code, or review a Python file. Do not use
  for implementing changes unless the user also asks for fixes.
version: 1.0.0
---

# Python Code Review

Review the submitted Python code for actionable problems. Be precise, explain
impact, and distinguish confirmed defects from context-dependent concerns.
Do not modify files unless the user explicitly asks for changes.

## 1. Identify the input and scope

- If the user provides a Python file path, read that file using the available
  file-reading tools before reviewing it.
- If the user pastes Python code, review the pasted code.
- If the user provides both a file path and pasted code, review the file and
  use the pasted code as context only when that intent is clear. If it is
  unclear which version to review, ask before proceeding.
- If no code or file path is provided, ask the user to provide it.
- Review only the requested code. Use surrounding code, tests, and project
  conventions when available to verify behavior; do not speculate about code
  that is not available.

## 2. Review dimensions

Consider each dimension. Report only relevant findings; omit dimensions with no
actionable findings.

### Correctness

- Logic errors, incorrect assumptions, boundary conditions, and unexpected
  behavior for empty, `None`, zero, or unusually large inputs.
- Mutable default arguments and unintended mutation or aliasing.
- Version-dependent behavior that conflicts with the project's supported
  Python versions.
- Incorrect handling of types, values, ordering, or concurrency where relevant.

### Security

- Hardcoded credentials or secrets.
- Injection risks, such as untrusted input passed to shell commands, SQL, or
  dynamic code execution. Consider whether inputs are actually controllable and
  whether safe parameterization or validation is used.
- Unsafe deserialization of untrusted data, such as `pickle` or unsafe YAML
  loading.
- Path traversal, unsafe file permissions, or untrusted URLs/redirects where
  applicable.
- Explain the required conditions and impact; do not label a pattern
  vulnerable without evidence that the risky input path is reachable.

### Performance

- Work that grows poorly with realistic input sizes, such as avoidable
  quadratic searches or repeated I/O/database calls in loops.
- Repeated expensive computation, unnecessary copying, or loading large inputs
  fully into memory when streaming is practical.
- Report performance concerns only when the likely impact is meaningful; nested
  loops or string concatenation alone do not prove a bottleneck.

### Scalability and reusability

- Assess whether the design can handle expected growth in data volume,
  concurrency, or workload without disproportionate resource use or operational
  complexity.
- Prefer reusable, cohesive functions and components for logic that has
  multiple callers or is likely to be shared. Flag avoidable duplication,
  hidden dependencies, or overly narrow interfaces when they make safe reuse
  difficult.
- Consider whether behavior that varies by caller should be passed explicitly
  rather than hard-coded or coupled to global state.
- Do not recommend generic frameworks, extra layers, or abstractions without a
  concrete reuse or scalability benefit. Keep one-off logic simple.

### Python style

- Follow the project's established conventions first; otherwise use clear,
  conventional Python style.
- Prefer comprehensions, `enumerate()`, `zip()`, unpacking, and context managers
  when they make the code clearer or safer, not as mechanical rules.
- Use `is None` / `is not None` for `None`. Do not recommend identity checks
  against booleans unless singleton identity is specifically intended.

### Maintainability

- Assess clarity, cohesion, duplication, unnecessary complexity, and meaningful
  naming.
- Consider missing documentation or type hints for public APIs when the project
  expects them. Do not flag private helpers mechanically.
- Treat line count, nesting depth, and constants as prompts to inspect—not
  defects by themselves.

### Error handling

- Look for swallowed exceptions, bare catches, missing cleanup for acquired
  resources, and errors that are hidden or misreported.
- Check that exceptions are handled at the appropriate boundary: propagate,
  translate, or log once as appropriate, without swallowing them.
- Flag implementation details in messages only when they are exposed across a
  user-facing or otherwise untrusted boundary.

## 3. Report findings

Start with exactly one verdict:

`Overall: <LOOKS GOOD | MINOR ISSUES | NEEDS WORK | BLOCKED>`

Use `BLOCKED` only when missing code or context prevents a meaningful review.
Otherwise choose the verdict based on the impact and number of actionable
findings.

Group findings by severity, omitting empty tiers. Use the most relevant
available line number or symbol; never invent line numbers.

For each finding, use:

```text
[SEVERITY] line N — Short title
Problem: Describe the evidence, impact, and relevant conditions.
Recommendation: Describe a focused fix. Include a short code example only when
it makes the fix clearer.
```

Severity:

- `[CRITICAL]` — Confirmed, severe security exposure, data loss/corruption, or
  failure in normal use with substantial impact.
- `[WARNING]` — A likely correctness defect, meaningful edge-case failure, or
  significant reliability/performance concern.
- `[SUGGESTION]` — A non-blocking clarity, style, or maintainability
  improvement.

Do not inflate severity. If a concern depends on an assumption, state that
assumption and lower the severity as appropriate.

End with `Strengths`, briefly noting concrete positive aspects. If there are no
actionable findings, say so plainly and do not invent issues to fill the report.
