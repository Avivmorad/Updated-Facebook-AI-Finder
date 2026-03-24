---
description: "Validate pipeline flow (Search -> Extract -> Filter -> AI -> Rank) and report consistency, missing fields, and breakpoints"
name: "Pipeline Check"
argument-hint: "Which pipeline input, file, or run should be checked?"
agent: "agent"
---

Run a strict pipeline validation for this flow:
Search -> Extract -> Filter -> AI -> Rank

Primary checks:

- data consistency across stages
- missing fields required by downstream stages
- breaking points and first failing stage

Execution rules:

1. Do not summarize architecture only; validate behavior from actual code paths and execution evidence when possible.
2. Trace payload shape at each stage and identify field additions/removals/renames.
3. Mark every stage status as: WORKING | FAILING | PARTIAL | NOT_TESTED.
4. If something was not executed, explicitly mark NOT_TESTED.
5. Do not guess. If evidence is insufficient, mark UNKNOWN.
6. Keep proposed fixes minimal and behavior-safe.

Required output format:

1. Stage-by-stage status table (Search, Extract, Filter, AI, Rank)
2. Data consistency findings
3. Missing fields by stage (with exact field names)
4. Breaking points (first failure + root cause)
5. Exact fix proposals (file + function + expected result)
6. Verification summary (what was run vs not tested)
