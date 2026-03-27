# SYSTEM_DESIGN.md
## Facebook Groups Post Finder & Matcher

This document defines the active runtime architecture.
`Project_Flow.md` remains the governing workflow document.

---

## 1. Architecture Summary

Pipeline layers:

1. Browser access (Playwright + existing Chrome profile)
2. Feed filtering and scan
3. Post opening and extraction
4. AI analysis and filtering
5. Ranking and presentation
6. Logging and run artifacts

---

## 2. Responsibility Split

System responsibility:

- browser actions
- filter selection
- scanning
- extraction
- screenshot capture
- payload construction
- result storage

AI responsibility:

- semantic understanding
- relevance decision
- match scoring
- recency final decision (`is_recent_24h`)

---

## 3. Core Data Contracts

### 3.1 Collected Post (runtime normalized schema)

- `post_link`
- `post_id`
- `post_text`
- `images`
- `image_count`
- `publish_date_raw`
- `publish_date_normalized`
- `extraction_quality` (`good|partial|failed`)
- `post_screenshot_path`
- `screenshot_paths`

### 3.2 AI Output (active schema)

- `is_relevant`
- `match_score`
- `detected_item`
- `match_reason`
- `confidence`
- `is_recent_24h`
- `publish_date_observed`
- `publish_date_reason`
- `publish_date_confidence`

---

## 4. Filtering Rules

Hard runtime conditions:

- `Recent posts` must be selected and verified.
- AI must return `is_recent_24h=true`.
- AI must return `is_relevant=true`.

If one condition fails, the post is discarded.

---

## 5. Screenshot Policy

- Screenshot is required for each processed post.
- Preferred capture mode: post-element screenshot.
- Fallback mode: full-page screenshot with coded warning/error path.

---

## 6. Provider Policy

- Active runtime expects Groq vision-compatible configuration.
- Missing/invalid vision model is startup/runtime error, not silent fallback.

---

## 7. Runtime Interface

Current interface:

- `start.py` CLI execution
- JSON report artifact
- debug trace artifact

Dedicated UI is future scope.
