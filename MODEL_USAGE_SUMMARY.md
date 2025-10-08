# Model Usage Summary - Which Endpoints Use GPT-5 vs GPT-5-mini

## Quick Answer:
**`openai/gpt-5`** = Full GPT-5 (expensive, high-quality)
**`openai/gpt-5-mini`** = GPT-5-mini (cheaper, faster, good quality)

---

## 📊 Endpoints Using `openai/gpt-5` (Full Model)

### Photo Analysis (Multiple Uses)
- `/api/photo-analysis/*` - 10+ occurrences
- Photo comparison, tracking, reports
- **Why:** Vision tasks need highest quality model

### Follow-Up System
- `/api/follow_up/*` - Used for generating follow-up questions (line 558)
- `/api/follow_up/*` - Used for analyzing answers (line 773)
- **Why:** Complex reasoning needed for diagnostic refinement

### Weekly Brief Intelligence
- `/api/intelligence/weekly-brief` - (line 246)
- **Why:** "Use GPT-5 with reasoning for maximum narrative quality"

### Health Scan (Deep Dive)
- `/api/deep-dive/start` - (line 296, 316)
- `/api/deep-dive/continue` - (line 510)
- `/api/deep-dive/complete` - (line 765)
- **Why:** Deep diagnostic reasoning requires full model

---

## 📊 Endpoints Using `openai/gpt-5-mini` (Mini Model)

### ✅ General Assessment System (NEW - What We Just Fixed)
- `/api/flash-assessment` - (line 227)
- `/api/general-assessment` - (line 475)
- `/api/general-deepdive/start` - (line 665)
- `/api/general-deepdive/continue` - (line 788)
- `/api/general-deepdive/complete` - (line 907)
- `/api/general-assessment/refine` - (line 1032)
- **Why:** Fast triage, good quality, cost-effective

### Health Story Generation
- `/api/health-story/*` - (lines 139, 218)
- **Why:** Creative writing but not critical diagnosis

### Intelligence Endpoints
- `/api/intelligence/health-velocity` - (line 161) "Fast model for quick analysis"
- `/api/intelligence/body-systems` - (line 209) "Fast model for structured analysis"
- `/api/intelligence/comparative` - (line 115)
- `/api/intelligence/timeline` - (line 234)
- `/api/intelligence/doctor-readiness` - (line 154)
- **Why:** Quick insights, structured data processing

### Tracking & Follow-Up
- `/api/tracking/*` - (line 91)
- `/api/follow_up/*` - (line 646) - Some follow-up questions
- **Why:** Simple pattern detection

### Health Scan (Quick Scan)
- `/api/quick-scan/ask-more` - (line 1499) "Standard model for question generation"
- `/api/quick-scan/think-harder` - (line 1831, 2187)
- **Why:** Quick assessments

### Think Harder Tiers
- `QuickScanThinkHarderRequest` - (model default in models/requests.py line 83)
- `QuickScanO4MiniRequest` - (model default in models/requests.py line 89)
- **Why:** Balanced cost/performance for enhanced analysis

---

## 🔍 Ultra Think / Deep Reasoning

**Ultra Think endpoints use `x-ai/grok-4`** (NOT GPT-5):
- Deep Dive Ultra Think
- General Assessment Ultra Think (if implemented)

**Why:** Grok-4 has extended reasoning capabilities

---

## 💰 Cost Implications

### High Cost (Use Sparingly):
- `openai/gpt-5` - Photo analysis, deep dive, weekly briefs
- `x-ai/grok-4` - Ultra think mode

### Medium Cost (Balance):
- `openai/gpt-5-mini` - Most assessment endpoints

### Low Cost (Bulk Operations):
- Free models like `deepseek/deepseek-chat` (fallback)

---

## 🎯 Summary for Your Question

**General Assessment System (what we just fixed):**
- ✅ Uses `openai/gpt-5-mini` (MINI, not full)
- Flash Assessment, General Assessment, General Deep Dive all use MINI
- This is intentional - fast triage doesn't need full GPT-5

**Other endpoints using GPT-5 models:**
- Full GPT-5: Photo analysis (vision), Deep Dive (complex reasoning), Weekly briefs (narrative quality)
- GPT-5-mini: Intelligence endpoints, tracking, health stories, general assessments

**Ultra Think uses Grok-4** (different model entirely for extended reasoning)

---

## 🔄 Model Selection Pattern

```
Simple/Fast Tasks → gpt-5-mini
Complex Reasoning → gpt-5
Maximum Reasoning → grok-4 (ultra think)
Vision Tasks → gpt-5 (only model with vision)
Cost-Sensitive → deepseek (fallback)
```
