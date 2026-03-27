# AGENTS.md
## Execution Rules for Coding Agents

`docs/specs/Project_Flow.md` is the source of truth.

---

## Mission

Build and maintain a focused Facebook Groups matcher pipeline:

- scan groups feed
- extract post data
- run AI relevance/match analysis
- rank and present results

---

## Strict Scope

Included:

- groups feed scanning
- post extraction
- AI matching
- ranking
- CLI + JSON artifacts

Excluded:

- seller analysis
- comments analysis
- risk/fraud logic
- marketplace flow
- Facebook login automation
- messaging sellers

---

## Locked Runtime Decisions

1. Recency final decision is AI-driven.
2. Screenshot is mandatory per processed post.
3. `Recent posts` filter is run-blocking and must be verified.
4. Active provider policy is Groq vision path.
5. UI is not part of the current runtime target.

---

## Engineering Rules

- Keep modules separated by concern: browser, extraction, ai, pipeline, presentation.
- No fallback fake data.
- No manual semantic heuristics replacing AI meaning decisions.
- Fail per post and continue when possible.
- Use explicit, cataloged error codes.
- Keep runtime behavior aligned with docs.

---

## Definition of Done

A change is done only if:

- behavior matches `Project_Flow.md`
- tests pass
- live gate passes:
  - `pytest -q`
  - `python scripts/doctor.py`
  - `python scripts/doctor.py --check-facebook-session`
  - `python start.py`
- debug trace and JSON artifact remain readable and consistent
