# System Design Document
## Facebook Groups Post Finder & Matcher

---

## 1. Overview

The system scans the user’s Facebook groups feed and matches posts against the user’s query using AI.

The system does NOT perform:
- Risk analysis
- Seller analysis
- Comment analysis

Its sole purpose is to evaluate how well each post matches the user’s intent.

---

## 2. System Goals

- Identify relevant posts  
- Understand post content  
- Match posts to user intent  
- Rank posts by match quality  

---

## 3. System Boundaries

The system operates only on the user’s Facebook groups feed using an existing Chrome profile.

The system does NOT include:
- Facebook login automation  
- Seller profile analysis  
- Comment analysis  
- Risk detection  
- Marketplace support  

---

## 4. User Input

- Search query (text)

---

## 5. System Flow

1. User enters query  
2. Open Chrome with existing profile  
3. Navigate to Facebook groups feed  
4. Apply Facebook built-in filters  
5. Scan and collect posts  
6. Open each post  
7. Extract data  
8. Send data to AI  
9. Filter non-relevant posts  
10. Score relevant posts  
11. Rank results  
12. Display results  

---

## 6. Data Collection

The system extracts only the following from each post:

- Post text  
- Images  
- Publish date  
- Post link  

The system does NOT collect:
- Comments  
- Seller information  
- Likes or reactions  

---

## 7. Data Processing

- Clean text  
- Normalize date  
- Organize images  

---

## 8. Filtering Rules

### Hard Conditions:

- Post must be from the last 24 hours  
- Post must be relevant to the user query  

If either condition fails → the post is discarded

---

## 9. Matching Logic

The AI determines what the post actually represents based on:

- Post text  
- Images  

Then compares it to the user query to determine relevance.

---

## 10. AI Responsibilities

The AI receives:

- User query  
- Post text  
- Images  

The AI returns:

- Relevance (true / false)  
- Detected item (what the post actually offers)  
- Match score  

---

## 11. Scoring System

The score represents:

> How well the post matches what the user is searching for

The score is based on:

- Understanding the product from text  
- Understanding the product from images  
- Consistency between text and images  
- Match to the user query  

The score does NOT include:

- Risk evaluation  
- Seller reliability  
- Comments  

---

## 12. Output

### List View:
- Post link  
- Match score  
- Short summary  

### Detail View:
- Extracted data  
- AI analysis  
- Match explanation  

---

## 13. UI

- Search screen  
- Start button  
- Progress bar  
- Results list  
- Detail view  

---

## 14. Constraints

- Only posts from the last 24 hours  
- Limited runtime  
- No fake fallback data  

---

## 15. Error Handling

- If a post fails → skip and continue  
- The process must not stop due to a single failure  

---

## 16. Summary

The system is a lightweight AI-powered matcher that:

- Collects data using Playwright  
- Delegates all understanding to AI  
- Filters strictly by relevance  
- Scores only based on match quality  