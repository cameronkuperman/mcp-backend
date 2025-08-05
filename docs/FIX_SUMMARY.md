# Fix Applied: Specialist Reports Data Isolation

## Problem Found
When you selected a specific assessment (e.g., lesion scan), the report was including unrelated data (e.g., chest pain) from the same day.

## Root Cause
The `gather_selected_data()` function was fetching:
1. **ALL symptom tracking from the same dates** as selected assessments
2. **ALL oracle chat summaries from the same dates**

This meant if you had multiple assessments on the same day, selecting one would pull in data from all of them.

## Fix Applied

### Before (Lines 415-428):
```python
# Get dates for symptom tracking correlation
scan_dates = [scan["created_at"][:10] for scan in data["quick_scans"]]

# Get symptom tracking entries from same dates
if scan_dates:
    for date in scan_dates:
        symptoms_result = supabase.table("symptom_tracking")\
            .select("*")\
            .eq("user_id", user_id)\
            .gte("created_at", f"{date}T00:00:00")\  # ALL from that day!
            .lte("created_at", f"{date}T23:59:59")\
            .execute()
```

### After:
```python
# Get ONLY symptom tracking directly linked to these specific scans
for scan in data["quick_scans"]:
    scan_id = scan.get("id")
    if scan_id:
        symptoms_result = supabase.table("symptom_tracking")\
            .select("*")\
            .eq("quick_scan_id", scan_id)\  # ONLY linked to THIS scan
            .execute()
```

## Changes Made

1. **Quick Scans**: Now only fetches symptom tracking with `quick_scan_id` matching the selected scan
2. **Deep Dives**: Now only fetches symptom tracking with `deep_dive_id` matching the selected dive
3. **Removed Oracle Chats**: No longer fetches unrelated chat summaries from the same dates
4. **Removed Date-Based Fetching**: Completely removed the logic that pulled all data from matching dates

## Result

Now when you select a specific assessment:
- ✅ ONLY that assessment's data is included
- ✅ NO unrelated data from the same day
- ✅ Reports focus on exactly what you selected

## Testing

To verify the fix works:

```bash
# Test with a specific quick scan
curl -X POST http://localhost:8000/api/report/specialist \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "your-analysis-id",
    "user_id": "your-user-id",
    "quick_scan_ids": ["single-scan-id"]  # Should ONLY include this scan
  }'
```

The report should now only discuss the selected assessment, not other interactions from the same day.

## Frontend Impact

No changes needed on frontend! Just ensure you're sending the correct IDs:

```javascript
// This will now work correctly - only selected data included
const report = await fetch('/api/report/cardiology', {
  body: JSON.stringify({
    analysis_id: analysisId,
    user_id: userId,
    quick_scan_ids: [selectedLesionScanId],  // Only lesion data
    deep_dive_ids: []  // Not chest pain!
  })
});
```

---

**Status**: ✅ FIXED AND READY
**Files Modified**: `/utils/data_gathering.py`
**Lines Changed**: 415-495