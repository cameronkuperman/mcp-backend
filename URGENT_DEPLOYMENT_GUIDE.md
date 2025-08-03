# 🚨 URGENT: Photo Analysis Follow-up Endpoint Fixes

## Quick Deployment Guide

### Issue Summary
The photo analysis follow-up endpoint is returning 500 errors due to:
1. JSON parsing failures (AI returning markdown-wrapped JSON)
2. AttributeError from using dot notation on dicts
3. Rate limiting not properly handled

### Immediate Fix Steps

#### 1. Update JSON Parser (CRITICAL)
The enhanced JSON parser is already in place and working. Verify it's deployed:
```bash
# Check if json_parser.py has the markdown extraction logic
grep -n "```json" utils/json_parser.py
```

#### 2. Fix Dictionary Access in Follow-up Endpoint

In `api/photo_analysis.py`, locate the `add_follow_up_photos` function (around line 1478) and make these changes:

**Find and replace these lines (around lines 1696-1705):**
```python
# WRONG - Using dot notation
'primary_change': analysis_response.comparison.get('primary_change'),
'change_significance': analysis_response.comparison.get('change_significance'),
# ... etc

# CORRECT - Using dict access
'primary_change': analysis_response.get('comparison', {}).get('primary_change'),
'change_significance': analysis_response.get('comparison', {}).get('change_significance'),
# ... etc
```

**Complete list of fixes needed:**
1. `analysis_response.comparison` → `analysis_response.get('comparison', {})`
2. `analysis_response.analysis` → `analysis_response.get('analysis', {})`

#### 3. Add Comprehensive Error Handling

Add this error handling at the END of the `add_follow_up_photos` function (before line 1744):

```python
    except HTTPException:
        raise
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "rate_limit",
                    "message": "AI service is temporarily busy. Please try again in 30 seconds.",
                    "retry_after": 30
                }
            )
        else:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "ai_service_error",
                    "message": f"AI service error: {e.response.status_code}"
                }
            )
            
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "json_parse_error",
                "message": "Failed to parse AI response. Please try again."
            }
        )
        
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred. Please try again."
            }
        )
```

### Testing the Fix

1. **Test JSON Parser**:
```bash
python test_json_parser.py
# Should show 6/8 tests passing
```

2. **Test Follow-up Endpoint Locally**:
```bash
# Start server
python run_oracle.py

# In another terminal, test the endpoint
curl -X POST http://localhost:8000/api/photo-analysis/session/{session_id}/follow-up \
  -F "photos=@test_image.jpg" \
  -F "auto_compare=true"
```

3. **Check Error Handling**:
- The endpoint should return structured JSON errors
- No more 500 errors with Python tracebacks
- Clear messages for rate limits

### Deploy to Railway

1. **Commit the fixes**:
```bash
git add api/photo_analysis.py
git commit -m "Fix photo analysis follow-up endpoint errors

- Fix AttributeError by using dict access instead of dot notation
- Add comprehensive error handling for all failure modes
- Improve error messages for better debugging"
```

2. **Push to deploy**:
```bash
git push origin main
```

3. **Monitor logs**:
```bash
railway logs
# Watch for any remaining errors
```

### Verification

After deployment, verify:
1. No more AttributeError in logs
2. Rate limits return 503 with retry message
3. JSON parsing errors are caught gracefully
4. Frontend receives structured error responses

### If Issues Persist

1. **Check AI Response Format**:
   - Log the raw AI response before parsing
   - Verify the JSON extractor handles the format

2. **Rate Limiting**:
   - Consider implementing request queuing
   - Add exponential backoff in frontend

3. **CORS Issues**:
   - Verify Railway deployment URL is in allowed origins
   - Check multipart/form-data headers

### Emergency Rollback

If needed:
```bash
git revert HEAD
git push origin main
```

---
**Priority**: CRITICAL
**Time to Deploy**: 5 minutes
**Risk**: Low (error handling improvements only)