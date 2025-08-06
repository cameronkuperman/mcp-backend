# Specialist Report Backend Fix - Analysis Record Creation

## The Problem
Frontend was expecting backend to CREATE the analysis record, but backend was trying to LOAD an existing one.

## The Fix Applied

### 1. Main Specialist Endpoint (`/api/reports/specialist.py`)
- Added logic to create analysis record if it doesn't exist
- Uses the analysis_id provided by frontend
- Creates proper report_config structure
- Stores all the selected IDs in the analysis record

### 2. Extended Specialist Endpoints (`/api/reports/specialist_extended.py`)
- Created `load_or_create_analysis()` function
- All 5 endpoints now create analysis if needed:
  - nephrology
  - urology
  - gynecology
  - oncology
  - physical_therapy

### 3. Key Changes Made

#### Analysis Record Creation
```python
# When analysis doesn't exist, create it with:
{
    "id": request.analysis_id,  # Use frontend-provided ID
    "user_id": request.user_id,
    "purpose": f"Specialist report for {specialty}",
    "recommended_type": specialty,
    "report_config": {
        "report_type": "specialist_focused",
        "specialty": specialty,
        "selected_data_only": True,
        "time_range": {
            "start": (30 days ago),
            "end": (now)
        }
    },
    "quick_scan_ids": request.quick_scan_ids or [],
    "deep_dive_ids": request.deep_dive_ids or [],
    # ... other ID arrays
}
```

#### Data Loading
- ALWAYS uses selected data mode
- Uses ONLY the IDs provided in request
- Empty arrays `[]` result in NO data loaded
- Never falls back to loading all user data

#### Response Format
```json
{
    "report_id": "xxx",
    "report_type": "specialist_focused",
    "specialty": "cardiology",  // ALWAYS included
    "report_data": {...},
    "status": "success"
}
```

## Model Change
- All reports now use `google/gemini-2.5-flash` instead of `tngtech/deepseek-r1t-chimera:free`
- Better performance and reliability

## Summary
Backend now properly:
1. Creates analysis records when frontend requests it
2. Uses ONLY the provided IDs (respects empty arrays)
3. Returns the specialty in all responses
4. Uses faster Gemini 2.5 Flash model

## Endpoints Updated
All specialist endpoints now create analysis records if they don't exist:
- `/api/report/specialist` ✓
- `/api/report/cardiology` ✓
- `/api/report/neurology` ✓
- `/api/report/psychiatry` ✓
- `/api/report/dermatology` ✓
- `/api/report/gastroenterology` ✓
- `/api/report/endocrinology` ✓
- `/api/report/pulmonology` ✓
- `/api/report/primary-care` ✓
- `/api/report/orthopedics` ✓
- `/api/report/rheumatology` ✓
- `/api/report/nephrology` ✓
- `/api/report/urology` ✓
- `/api/report/gynecology` ✓
- `/api/report/oncology` ✓
- `/api/report/physical-therapy` ✓