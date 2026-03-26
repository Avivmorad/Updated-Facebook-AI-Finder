# AGENTS.md
## Facebook Groups Post Finder & Matcher

---

## 1. Project Summary

This project builds an automated system that:

- Scans the user's Facebook groups feed
- Extracts post data using Playwright
- Uses AI to determine relevance and match quality
- Ranks posts based on how well they match the user’s query

The system is intentionally minimal and focused.

---

## 2. Core Principle

> The system COLLECTS data.  
> The AI UNDERSTANDS data.

No logic duplication.

---

## 3. Scope (Strict)

### Included:

- Facebook Groups Feed scanning
- Post extraction (text, images, date, link)
- AI-based relevance check
- Match scoring
- Ranking results

---

### Excluded (Do NOT implement):

- Facebook login automation  
- Seller profile analysis  
- Comment extraction or analysis  
- Risk detection  
- Fraud detection  
- Marketplace support  
- Messaging sellers  
- Any external data enrichment  

---

## 4. Non-Negotiable Rules

- NEVER add features outside the defined scope  
- NEVER introduce fallback or fake data  
- NEVER implement risk logic or heuristics  
- NEVER analyze seller or comments  
- NEVER change architecture without strong justification  
- NEVER hardcode assumptions about Facebook structure without fallback handling  

---

## 5. Data Collection Rules

The system extracts ONLY:

- Post text  
- Images  
- Publish date  
- Post link  

Nothing else.

---

## 6. Filtering Rules

### Hard Conditions:

- Post must be from last 24 hours  
- Post must be relevant (AI decision)

If not → discard immediately

---

## 7. AI Responsibilities (Only AI decides meaning)

The AI is responsible for:

- Understanding what the post actually offers  
- Comparing it to the user query  
- Determining relevance  
- Assigning match score  

The system must NOT:

- Interpret meaning  
- Infer product type  
- Apply manual matching logic  

---

## 8. Scoring Definition

Score = match quality only

Based on:

- Product understanding (text)  
- Product understanding (images)  
- Consistency between text and images  
- Alignment with user query  

NOT based on:

- Risk  
- Seller  
- Comments  
- External data  

---

## 9. Expected AI Output Format

The AI must return structured output:

```json
{
  "is_relevant": true,
  "match_score": 0-100,
  "detected_item": "string",
  "match_reason": "string",
  "confidence": 0-100
}
10. Development Workflow
Before making changes:
Read:
docs/specs/SYSTEM_DESIGN.md
docs/specs/PROJECT_DEVELOPMENT_PHASES.md
docs/specs/AGENTS.md
Understand current code structure
While developing:
Make small, focused changes
Keep functions modular
Avoid breaking existing logic
Prefer clarity over cleverness
After changes:
Verify code runs
Verify no breaking changes
Validate core flow still works
11. Code Guidelines
Use clear function names
Avoid large functions
Separate concerns (browser / extraction / AI / pipeline)
Keep AI interface isolated
Avoid duplicated logic
12. Architecture Expectations

Modules should be separated logically:

browser → Playwright logic
extraction → data extraction
processing → cleaning / normalization
ai → AI interaction
pipeline → orchestration
ui → presentation
13. Error Handling
Fail per post, not globally
Log errors clearly
Continue processing remaining posts
14. Performance Guidelines
Avoid unnecessary page reloads
Avoid repeated DOM queries
Limit number of posts processed
Optimize scrolling and loading
15. When to Stop and Ask

Stop and request clarification if:

A feature seems outside scope
Facebook structure prevents reliable extraction
AI output is inconsistent
A change requires architectural redesign
16. Anti-Patterns (DO NOT DO)
Adding heuristics instead of using AI
Adding scoring dimensions beyond match
Using comments or seller data
Creating fake/mock fallback results
Overengineering early
17. Definition of Done

A feature is complete only if:

It follows the system design
It respects scope constraints
It does not introduce forbidden logic
It integrates cleanly into pipeline
It does not break existing flow
18. Final Principle

Keep it simple.
Collect → Send to AI → Filter → Score → Rank.

Nothing more.
