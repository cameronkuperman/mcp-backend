# Specialist Report Data Filtering Debug Guide

## Issue Summary
Frontend reports that specialist reports are showing ALL user data instead of filtering by the selected assessment IDs that are sent in the request.

## FIXED: UUID Type Mismatch Error
The Supabase error "operator does not exist: uuid = text" has been fixed. The code now properly converts user_id to string when querying TEXT columns.

## Changes Made

### 1. Added Extensive Logging (COMPLETED)
Added detailed logging throughout the specialist report flow:

- **Request logging**: Logs all IDs received from frontend
- **Database query logging**: Logs what's being fetched and what's found
- **Data summary logging**: Logs the final data being sent to AI

Key log points:
- `/api/reports/specialist.py`: Lines 218-231, 248-286, 303-313
- `/utils/data_gathering.py`: Lines 377-384, 405-441, 454-481

### 2. Added Test Endpoint (NEW)
Created `/api/report/test-data-filtering` endpoint to verify data filtering works:

```bash
curl -X POST http://localhost:8000/api/report/test-data-filtering \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "test-123",
    "user_id": "actual-user-id",
    "quick_scan_ids": ["scan-1", "scan-2"],
    "deep_dive_ids": ["dive-1"]
  }'
```

This returns exactly what was requested vs what was found.

### 3. Fixed User ID Filtering (IMPORTANT)
Modified `gather_selected_data` to handle cases where user_id might not match:
- Now only filters by user_id if it's provided
- Logs warnings when fetching without user filter
- Shows debug info about mismatched user IDs

## How to Debug

### Step 1: Restart Backend
```bash
python run_oracle.py
```

### Step 2: Monitor Logs
Watch the console output when generating a specialist report. Look for:

```
=== SPECIALIST REPORT REQUEST ===
Quick scan IDs requested: ['id-1', 'id-2']
RAW REQUEST DATA: {...}

=== GATHER_SELECTED_DATA START ===
Quick scan IDs to fetch: ['id-1', 'id-2']
DEBUG - Found 2 quick scans WITHOUT user filter
DEBUG - User IDs in results: ['user-123', 'user-123']
Found 2 quick scans WITH user filter: True

=== DATA BEING SENT TO AI ===
Total quick scans: 2
Quick scan dates: ['2025-01-15', '2025-01-16']
```

### Step 3: Test Data Filtering
Use the test endpoint to verify filtering works:

```javascript
// Frontend test
const response = await fetch('/api/report/test-data-filtering', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    analysis_id: 'test',
    user_id: currentUser.id,
    quick_scan_ids: ['scan-1', 'scan-2'],
    deep_dive_ids: ['dive-1']
  })
});

const result = await response.json();
console.log('Requested:', result.requested);
console.log('Found:', result.found);
```

## Potential Issues and Fixes

### 1. User ID Type Mismatch (FIXED)
**Issue**: Supabase error "operator does not exist: uuid = text"
**Fix**: Updated gather_selected_data to convert user_id to string for TEXT columns:
- quick_scans.user_id is TEXT
- deep_dive_sessions.user_id is TEXT  
- general_assessments.user_id is UUID
- general_deepdive_sessions.user_id is UUID

The code now properly handles type conversion.

### 2. Wrong IDs Being Sent
**Issue**: Frontend sending wrong IDs or wrong format
**Fix**: Check "RAW REQUEST DATA" in logs

### 3. Database Query Issues
**Issue**: Supabase `.in_()` query not working as expected
**Fix**: Use test endpoint to verify; check Supabase logs

### 4. Analysis Table Override
**Issue**: The analysis record might have its own IDs that override the request
**Fix**: Logs now show both analysis IDs and request IDs

## Next Steps for Frontend

1. **Verify Request Format**:
   ```javascript
   // Ensure IDs are arrays of strings
   const requestBody = {
     analysis_id: analysisId,
     user_id: userId,
     quick_scan_ids: ['id1', 'id2'], // Array of strings
     deep_dive_ids: ['id3', 'id4'],  // Array of strings
     specialty: 'cardiology'
   };
   ```

2. **Check Response**:
   - Look at the actual report data returned
   - Verify the IDs in the report match what was requested

3. **Use Test Endpoint**:
   - Call `/api/report/test-data-filtering` first
   - Verify it returns only the requested data
   - Then try the actual specialist report

## If Still Not Working

1. **Check Supabase RLS Policies**: 
   - Might be blocking certain queries
   - Try with service role key temporarily

2. **Verify ID Format**:
   - Ensure IDs are exact matches (UUIDs)
   - No extra spaces or formatting issues

3. **Check Frontend State**:
   - Ensure the IDs being sent are actually the selected ones
   - Not accidentally sending all IDs

## Message to Frontend Developer

The backend has been updated with extensive logging. Please:

1. Restart your backend server
2. Generate a specialist report with specific IDs selected
3. Send me the console logs showing the "=== SPECIALIST REPORT REQUEST ===" section
4. Try the test endpoint `/api/report/test-data-filtering` with the same IDs
5. Let me know if the test endpoint returns the correct filtered data

The issue is likely one of:
- User ID format mismatch
- IDs not being sent correctly from frontend
- RLS policies blocking the queries

The logs will tell us exactly what's happening.