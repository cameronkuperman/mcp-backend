# Migration Guide: Modularizing run_oracle.py

## What I've Done So Far

1. **Created directory structure**:
   - `api/` - All API endpoints organized by feature
   - `models/` - Request/response models
   - `utils/` - Utility functions
   - `core/` - Core app functionality

2. **Migrated these endpoints**:
   - ✅ `/api/chat` → `api/chat.py`
   - ✅ `/api/health` → `api/chat.py`
   - ✅ `/api/generate_summary` → `api/chat.py`
   - ✅ `/api/quick-scan` → `api/health_scan.py`
   - ✅ `/api/deep-dive/start` → `api/health_scan.py`
   - ✅ `/api/deep-dive/continue` → `api/health_scan.py`
   - ✅ `/api/deep-dive/complete` → `api/health_scan.py`

3. **Created new entry point**: `run_oracle_new.py` (slim ~60 lines)

## Remaining Endpoints to Migrate

### Health Story (1 endpoint)
- `/api/health-story` → `api/health_story.py`

### Report Endpoints (18 endpoints)
- `/api/report/analyze` → `api/reports/general.py`
- `/api/report/comprehensive` → `api/reports/general.py`
- `/api/report/urgent-triage` → `api/reports/urgent.py`
- `/api/report/symptom-timeline` → `api/reports/general.py`
- `/api/report/photo-progression` → `api/reports/general.py`
- `/api/report/specialist` → `api/reports/specialist.py`
- `/api/report/annual-summary` → `api/reports/time_based.py`
- `/api/report/cardiology` → `api/reports/specialist.py`
- `/api/report/neurology` → `api/reports/specialist.py`
- `/api/report/psychiatry` → `api/reports/specialist.py`
- `/api/report/dermatology` → `api/reports/specialist.py`
- `/api/report/gastroenterology` → `api/reports/specialist.py`
- `/api/report/endocrinology` → `api/reports/specialist.py`
- `/api/report/pulmonology` → `api/reports/specialist.py`
- `/api/report/30-day` → `api/reports/time_based.py`
- `/api/report/annual` → `api/reports/time_based.py`
- `/api/report/{report_id}/doctor-notes` → `api/reports/general.py`
- `/api/report/{report_id}/share` → `api/reports/general.py`
- `/api/report/{report_id}/rate` → `api/reports/general.py`

### Population Health (2 endpoints)
- `/api/population-health/alerts` → `api/population_health.py`
- `/api/reports` → `api/population_health.py`

### Tracking (5 endpoints)
- `/api/tracking/suggest` → `api/tracking.py`
- `/api/tracking/configure` → `api/tracking.py`
- `/api/tracking/data` → `api/tracking.py`
- `/api/tracking/configurations` → `api/tracking.py`
- `/api/tracking/data-points` → `api/tracking.py`

## Helper Functions to Move

These should be moved to `utils/data_gathering.py`:
- `get_health_story_data()`
- `gather_report_data()`
- `gather_comprehensive_data()`
- `extract_cardiac_patterns()`
- `determine_time_range()`
- `has_emergency_indicators()`
- `extract_session_context()`
- `safe_insert_report()`
- `load_analysis()`

## How to Complete Migration

1. For each module, create a new file with FastAPI router
2. Copy endpoints and their helper functions
3. Update imports to use models from `models/requests.py`
4. Add router import to `run_oracle_new.py`
5. Test each endpoint works exactly the same

## Testing Migration

```bash
# Start with new modular server
python run_oracle_new.py

# Test endpoints match original
curl http://localhost:8000/api/health
curl http://localhost:8000/api/chat -X POST -d '...'
```

## Final Steps

1. Once all endpoints migrated and tested
2. Rename `run_oracle.py` → `run_oracle_old.py`
3. Rename `run_oracle_new.py` → `run_oracle.py`
4. Deploy and verify in production