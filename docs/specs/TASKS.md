# TASKS.md
## Implementation Task List

`Project_Flow.md` is authoritative.  
This file is the executable task order for contributors.

---

## Global Rules

- no scope expansion beyond core pipeline
- no seller/comments/risk/marketplace logic
- no fake fallback data
- no undocumented runtime behavior
- all user-facing failures must map to cataloged error codes

---

## Task Order

1. Spec hard reset and doc alignment
2. Startup validation and error-code mapping
3. Feed filter enforcement and verification
4. Feed scan telemetry and canonical dedupe
5. Post opening stability and container readiness
6. DOM-first extraction schema completion
7. Extraction quality classification
8. Mandatory screenshot capture (element-first + fallback)
9. Pipeline schema alignment across extraction -> AI -> output
10. Result artifact diagnostics (`post_failures`, extraction signals)
11. Manual local URL extraction probe path
12. Default input alignment (`"ספה"`)
13. Test expansion for scanner/extractor/schema/probe
14. Live gate stabilization

---

## Definition of Complete Task

A task is complete only if:

- behavior is covered by tests
- docs are updated if behavior changed
- no conflicting behavior remains in neighboring modules

---

## Final Acceptance Gate

Must pass in this order:

1. `pytest -q`
2. `python scripts/doctor.py`
3. `python scripts/doctor.py --check-facebook-session`
4. `python start.py`

Artifacts expected:

- `data/reports/latest.json`
- `data/logs/debug_trace.txt`
