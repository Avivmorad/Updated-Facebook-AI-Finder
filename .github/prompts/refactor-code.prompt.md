---
description: "Refactor selected code for readability and reduced duplication without changing behavior"
name: "Refactor Code Safely"
argument-hint: "What code/file/function should be refactored?"
agent: "agent"
---

Refactor the provided code with these fixed goals:

- improve readability
- reduce duplication
- keep exactly the same behavior

Execution rules:

1. Read the relevant file(s) first and identify repeated logic, long/unclear blocks, and naming issues.
2. Preserve external behavior and public interfaces unless explicitly requested otherwise.
3. Prefer small, safe, modular changes over large rewrites.
4. Do not change schemas, field names, or return formats.
5. Keep existing style and conventions in this repository.
6. Add brief comments only where logic is non-obvious.
7. After edits, run relevant tests/lint for touched areas when available.
8. If full verification cannot be run, state exactly what was not verified.

Required output format:

1. Summary of what was refactored
2. File-by-file change list
3. Behavior-safety notes (why behavior is preserved)
4. Verification results (tests/lint run + outcomes)
5. Remaining risks or follow-ups
