# Photo Analysis Follow-up Implementation

## Overview
This document describes the implementation of the photo analysis follow-up and reminder system endpoints that were missing from the backend.

## Implemented Endpoints

### 1. Add Follow-up Photos
**Endpoint:** `POST /api/photo-analysis/session/{session_id}/follow-up`

**Purpose:** Add new photos to an existing session and automatically compare with previous photos.

**Request:**
```
Content-Type: multipart/form-data

photos: [files] (max 5)
auto_compare: boolean (default: true)
notes: string (optional)
compare_with_photo_ids: JSON string of photo IDs (optional)
```

**Response:**
```json
{
  "uploaded_photos": [...],
  "comparison_results": {
    "compared_with": ["photo-id-1"],
    "days_since_last": 30,
    "analysis": {
      "trend": "stable",
      "changes": {...},
      "confidence": 0.85,
      "summary": "No significant changes observed"
    }
  },
  "follow_up_suggestion": {
    "benefits_from_tracking": true,
    "suggested_interval_days": 30,
    "reasoning": "Monthly monitoring recommended for moles",
    "priority": "routine"
  }
}
```

### 2. Configure Reminders
**Endpoint:** `POST /api/photo-analysis/reminders/configure`

**Purpose:** Set up or update follow-up reminders for a photo session.

**Request:**
```json
{
  "session_id": "session-uuid",
  "analysis_id": "analysis-uuid",
  "enabled": true,
  "interval_days": 30,
  "reminder_method": "email",
  "reminder_text": "Time to update on your mole",
  "contact_info": {
    "email": "user@example.com"
  }
}
```

**Response:**
```json
{
  "reminder_id": "reminder-uuid",
  "session_id": "session-uuid",
  "next_reminder_date": "2025-03-01T10:00:00Z",
  "interval_days": 30,
  "method": "email",
  "status": "active",
  "ai_reasoning": "Monthly checks for moles provide good balance",
  "can_modify": true
}
```

### 3. Get Monitoring Suggestions
**Endpoint:** `POST /api/photo-analysis/monitoring/suggest`

**Purpose:** Get AI-powered monitoring schedule recommendations.

**Request:**
```json
{
  "analysis_id": "analysis-uuid",
  "condition_context": {
    "is_first_analysis": true,
    "user_concerns": "Mole has been changing",
    "duration": "noticed 2 months ago"
  }
}
```

**Response:**
```json
{
  "monitoring_plan": {
    "recommended_interval_days": 30,
    "interval_type": "fixed",
    "reasoning": "New moles should be monitored monthly",
    "schedule": [
      {"check_number": 1, "days_from_now": 30, "purpose": "Initial monitoring"},
      {"check_number": 2, "days_from_now": 60, "purpose": "Confirm stability"}
    ],
    "red_flags_to_watch": ["Rapid size increase", "Color changes"],
    "when_to_see_doctor": "If rapid changes occur"
  },
  "confidence": 0.9,
  "based_on_conditions": ["mole", "pigmented_lesion"]
}
```

### 4. Get Session Timeline
**Endpoint:** `GET /api/photo-analysis/session/{session_id}/timeline`

**Purpose:** Get complete timeline of photos, analyses, and reminders.

**Response:**
```json
{
  "session": {
    "id": "session-uuid",
    "condition_name": "Mole on left arm",
    "created_at": "2025-01-01T10:00:00Z",
    "is_sensitive": false
  },
  "timeline_events": [
    {
      "date": "2025-01-01T10:00:00Z",
      "type": "photo_upload",
      "photos": [...],
      "analysis_summary": "Benign mole"
    },
    {
      "date": "2025-02-01T10:00:00Z",
      "type": "follow_up",
      "photos": [...],
      "comparison": {
        "days_since_previous": 31,
        "trend": "stable",
        "summary": "No changes observed"
      }
    }
  ],
  "next_action": {
    "type": "photo_follow_up",
    "date": "2025-03-01T10:00:00Z",
    "days_until": 29
  },
  "overall_trend": {
    "direction": "stable",
    "total_duration_days": 31,
    "number_of_checks": 2
  }
}
```

## Database Changes

A new table `photo_reminders` has been created with the following structure:
- `id`: UUID primary key
- `session_id`: Reference to photo session
- `analysis_id`: Reference to photo analysis
- `user_id`: User who owns the reminder
- `enabled`: Whether reminder is active
- `interval_days`: Days between reminders
- `reminder_method`: email, sms, in_app, or none
- `reminder_text`: Generic reminder message
- `contact_info`: JSON with email/phone
- `next_reminder_date`: When to send next reminder
- `ai_reasoning`: AI explanation for interval
- `last_sent_at`: When last reminder was sent

Additionally, `photo_uploads` table now has:
- `is_followup`: Boolean flag for follow-up photos
- `followup_notes`: Optional notes for follow-up

## Testing

Run the test script to verify all endpoints are working:
```bash
python test_photo_followup_endpoints.py
```

## Frontend Integration Notes

1. **Follow-up Photos**: When user returns to add more photos, use the follow-up endpoint instead of the regular upload endpoint. This ensures proper comparison and tracking.

2. **Reminders**: After analysis, if `trackable_metrics` exist, offer reminder configuration. The backend will provide intelligent interval suggestions.

3. **Timeline View**: Use the timeline endpoint to show progression over time with visual comparison of trends.

4. **Error Handling**: All endpoints return proper HTTP status codes:
   - 200: Success
   - 404: Session/Analysis not found
   - 422: Validation error
   - 500: Server error

## Migration

Run the SQL migration in `migrations/photo_reminders_migration.sql` to create the necessary database tables and indexes.