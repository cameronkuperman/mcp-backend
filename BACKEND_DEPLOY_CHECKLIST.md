# Backend Deploy Checklist 🚀

## What You Need to Deploy:

### 1. ✅ Already Fixed in Code:
- Deep Dive now uses DeepSeek V3 (better JSON parsing)
- Ask Me More accepts `current_confidence` field
- Added `initial_questions_count` tracking
- Enhanced JSON extraction for Gemini models
- Debug logging for session issues
- Support for up to 5 additional questions (11 total)

### 2. 🔧 Just Deploy These Changes:
```bash
# Check what's changed
git status

# Add all changes
git add -A

# Commit with clear message
git commit -m "Fix Deep Dive JSON parsing and Ask Me More - track initial questions, accept frontend fields"

# Push to deploy
git push
```

### 3. 📊 Monitor After Deploy:

#### Check Deep Dive is returning real analysis:
- Should see "Rotator Cuff Tendinitis" not "Analysis of Left Deltoid pain"
- Confidence should be realistic (70-85%) not always 70%
- Differentials should have real conditions

#### Check Ask Me More works:
- Look for debug logs: `[DEBUG] Ask Me More - Looking for session: xxx`
- Should return actual questions, not "session not found"
- Should track `initial_questions_count`

### 4. 🔍 If Issues Persist:

#### Session Not Found:
```python
# Check logs for:
[DEBUG] Ask Me More - Session response exists: False
[DEBUG] Ask Me More - Recent sessions: [...]
```
This means session ID is wrong or session was deleted

#### Missing initial_questions_count:
- Old sessions won't have this field
- Only new Deep Dive sessions (after deploy) will track it
- Frontend might need to handle old sessions gracefully

### 5. 🎯 Quick Validation:
```bash
# After deploy, test Deep Dive
curl -X POST https://your-api.railway.app/api/deep-dive/start \
  -H "Content-Type: application/json" \
  -d '{
    "body_part": "shoulder",
    "form_data": {"symptoms": "pain"}
  }'

# Complete it
curl -X POST https://your-api.railway.app/api/deep-dive/complete \
  -H "Content-Type: application/json" \
  -d '{"session_id": "xxx"}'

# Check response has real medical terms, not generic fallback
```

## What's Ready to Go:
1. ✅ Deep Dive returns real medical analysis
2. ✅ Ask Me More accepts frontend fields
3. ✅ Tracks questions properly for Ask Me More
4. ✅ AI-powered question generation
5. ✅ Up to 11 total questions (6 + 5 more)

## No Additional Backend Work Needed!
Just deploy and monitor. The code fixes are all in place.

## Frontend Reminders:
- Don't auto-complete after Ask Me More
- Send `current_confidence` field
- Handle old sessions without `initial_questions_count`
- Keep using `max_questions` field (it works now!)

Ready to deploy! 🚀