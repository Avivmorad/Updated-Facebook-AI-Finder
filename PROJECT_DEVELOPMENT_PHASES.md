# Project Development Phases
## Facebook Groups Post Finder & Matcher

---

## Phase 1 — Specification Lock

- Define system goals  
- Define boundaries  
- Confirm:
  - Groups feed only  
  - No comments  
  - No seller analysis
  - No risk analysis  
  - AI used only for matching  

---

## Phase 2 — Technical Foundation

- Create project structure  
- Define environment variables  
- Ensure system can run  

---

## Phase 3 — Facebook Access

- Connect using Chrome profile  
- Navigate to groups feed  

---

## Phase 4 — Facebook Filtering

- Use only Facebook built-in filters  

---

## Phase 5 — Feed Scanning

- Scroll feed  
- Collect post links  

---

## Phase 6 — Post Opening

- Open each post  
- Wait for full load  

---

## Phase 7 — Data Extraction

The system extracts:

- Post text  
- Images  
- Publish date  
- Post link  

The system does NOT extract:

- Comments  
- Seller info  
- Likes  

---

## Phase 8 — Data Processing

- Clean text  
- Normalize date  
- Organize images  

---

## Phase 9 — Time Filtering

- Check if post is within last 24 hours  
- If not → discard  

---

## Phase 10 — AI Analysis

The AI:

- Understands what the post is offering  
- Compares it to the user query  
- Determines relevance  
- Produces a match score  

---

## Phase 11 — Relevance Filtering

- If not relevant → discard  
- If relevant → continue  

---

## Phase 12 — Scoring

- Assign match score only  

---

## Phase 13 — Ranking

- Sort posts by score (descending)  

---

## Phase 14 — Results Presentation

- Display results list  
- Enable detailed view  

---

## Phase 15 — UI Layer

- Search screen  
- Start button  
- Progress bar  
- Results  

---

## Phase 16 — Logging

- Log execution steps  
- Log errors  

---

## Phase 17 — Error Handling

- Skip failed posts  
- Continue processing  

---

## Phase 18 — Performance Optimization

- Improve runtime  
- Reduce unnecessary actions  

---

## Phase 19 — Production Readiness

- Code cleanup  
- Final testing  
- Stabilization  

---

## Summary

The system evolves from:

- Basic Facebook access  
→ Data extraction  
→ AI-based matching  
→ Ranked results display