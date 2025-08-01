# Photo Follow-Up & Reminder System API Design

## Overview
This document outlines the API design for photo follow-up functionality and optional reminder system. The system allows users to track conditions over time with AI-suggested monitoring intervals.

## Core Principles
- **Opt-in only**: No reminders unless explicitly requested
- **User control**: Full control over intervals and notification methods
- **Privacy-focused**: Generic reminder text, no specific condition details
- **AI-guided**: Intelligent interval suggestions based on condition type
- **Non-intrusive**: Especially for ongoing monitoring

## API Endpoints

### 1. Add Follow-up Photos to Session
```
POST /api/photo-analysis/session/{session_id}/follow-up
Content-Type: multipart/form-data

photos: [files] (max 5)
auto_compare: boolean (default: true)
notes: string (optional)
compare_with_photo_ids: [string] (optional, overrides auto_compare)

Response:
{
  "uploaded_photos": [...],
  "comparison_results": {
    "compared_with": ["photo-id-1", "photo-id-2"],
    "days_since_last": 30,
    "analysis": {
      "trend": "stable|improving|worsening",
      "changes": {...},
      "confidence": 0.85,
      "summary": "No significant changes observed"
    }
  },
  "follow_up_suggestion": {
    "benefits_from_tracking": true,
    "suggested_interval_days": 30,
    "reasoning": "Monthly monitoring recommended for moles to detect changes",
    "priority": "routine|important|urgent"
  }
}
```

### 2. Configure Follow-up Reminders
```
POST /api/photo-analysis/reminders/configure
Content-Type: application/json

{
  "session_id": "session-uuid",
  "analysis_id": "analysis-uuid",
  "enabled": true,
  "interval_days": 30,  // Can override AI suggestion
  "reminder_method": "email|sms|in_app|none",
  "reminder_text": "Time to update on your mole",  // Generic, high-level
  "contact_info": {
    "email": "user@example.com",  // If email method
    "phone": "+1234567890"  // If SMS method
  }
}

Response:
{
  "reminder_id": "reminder-uuid",
  "session_id": "session-uuid",
  "next_reminder_date": "2025-03-01",
  "interval_days": 30,
  "method": "email",
  "status": "active",
  "ai_reasoning": "Based on benign mole assessment, monthly checks recommended",
  "can_modify": true
}
```

### 3. Get AI Monitoring Suggestions
```
POST /api/photo-analysis/monitoring/suggest
Content-Type: application/json

{
  "analysis_id": "analysis-uuid",
  "condition_context": {
    "is_first_analysis": true,
    "user_concerns": "Mole has been changing",
    "duration": "noticed 2 months ago"
  }
}

Response:
{
  "monitoring_plan": {
    "recommended_interval_days": 30,
    "interval_type": "fixed|decreasing|conditional",
    "reasoning": "New or changing moles should be photographed monthly for the first 3 months, then quarterly if stable",
    "schedule": [
      {"check_number": 1, "days_from_now": 30, "purpose": "Initial change monitoring"},
      {"check_number": 2, "days_from_now": 60, "purpose": "Confirm stability"},
      {"check_number": 3, "days_from_now": 90, "purpose": "Establish baseline"},
      {"check_number": 4, "days_from_now": 180, "purpose": "Quarterly check if stable"}
    ],
    "red_flags_to_watch": [
      "Rapid size increase",
      "Color changes",
      "Border irregularity"
    ],
    "when_to_see_doctor": "If any rapid changes occur between scheduled photos"
  },
  "confidence": 0.9,
  "based_on_conditions": ["mole", "pigmented_lesion"]
}
```

### 4. Update Reminder Settings
```
PUT /api/photo-analysis/reminders/{reminder_id}
Content-Type: application/json

{
  "enabled": true|false,
  "interval_days": 45,  // User adjusting
  "reminder_method": "in_app",
  "pause_until": "2025-03-15"  // Optional pause
}

Response:
{
  "reminder_id": "reminder-uuid",
  "updated_settings": {...},
  "next_reminder_date": "2025-03-15",
  "status": "active|paused|disabled"
}
```

### 5. Get Session Timeline with Reminders
```
GET /api/photo-analysis/session/{session_id}/timeline

Response:
{
  "session": {...},
  "timeline_events": [
    {
      "date": "2025-01-01",
      "type": "photo_upload",
      "photos": [...],
      "analysis_summary": "Initial assessment: benign mole"
    },
    {
      "date": "2025-02-01",
      "type": "follow_up",
      "photos": [...],
      "comparison": {
        "days_since_previous": 31,
        "trend": "stable",
        "summary": "No changes observed"
      }
    },
    {
      "date": "2025-03-01",
      "type": "scheduled_reminder",
      "status": "upcoming",
      "message": "Time to update on your mole"
    }
  ],
  "next_action": {
    "type": "photo_follow_up",
    "date": "2025-03-01",
    "days_until": 29
  },
  "overall_trend": {
    "direction": "stable",
    "total_duration_days": 60,
    "number_of_checks": 2
  }
}
```

### 6. Quick Follow-up Status Check
```
GET /api/photo-analysis/sessions/follow-up-status?user_id={user_id}

Response:
{
  "sessions_needing_follow_up": [
    {
      "session_id": "session-uuid",
      "condition_name": "Mole on left arm",
      "last_photo_date": "2025-01-15",
      "days_since": 16,
      "suggested_interval": 30,
      "reminder_status": "active|none",
      "priority": "routine"
    }
  ],
  "upcoming_reminders": [
    {
      "reminder_id": "reminder-uuid",
      "session_id": "session-uuid",
      "scheduled_date": "2025-02-15",
      "days_until": 14,
      "condition_hint": "mole"  // Generic, not specific location
    }
  ]
}
```

### 7. Batch Reminder Management
```
GET /api/photo-analysis/reminders?user_id={user_id}

Response:
{
  "active_reminders": [
    {
      "reminder_id": "reminder-uuid",
      "session_id": "session-uuid",
      "condition_type": "mole",
      "interval_days": 30,
      "next_date": "2025-03-01",
      "method": "email",
      "created_at": "2025-01-01",
      "total_follow_ups": 2
    }
  ],
  "reminder_statistics": {
    "total_active": 3,
    "average_compliance_rate": 0.85,
    "most_tracked_condition": "mole"
  }
}
```

### 8. Disable All Reminders (Privacy Option)
```
POST /api/photo-analysis/reminders/disable-all
Content-Type: application/json

{
  "user_id": "user-uuid",
  "reason": "privacy|not_needed|other" (optional)
}

Response:
{
  "disabled_count": 3,
  "message": "All reminders have been disabled",
  "can_reenable": true
}
```

## Data Models

### ReminderConfiguration
```typescript
{
  id: string
  session_id: string
  user_id: string
  analysis_id: string
  enabled: boolean
  interval_days: number
  reminder_method: 'email' | 'sms' | 'in_app' | 'none'
  reminder_text: string  // Generic text
  next_reminder_date: Date
  last_reminder_sent: Date | null
  total_reminders_sent: number
  created_at: Date
  updated_at: Date
  paused_until: Date | null
  
  // AI metadata
  ai_suggested_interval: number
  ai_reasoning: string
  condition_category: string  // 'mole', 'rash', 'injury', etc.
  monitoring_priority: 'routine' | 'important' | 'urgent'
}
```

### MonitoringSchedule
```typescript
{
  id: string
  session_id: string
  schedule_type: 'fixed' | 'decreasing' | 'conditional'
  checkpoints: [
    {
      check_number: number
      days_from_start: number
      interval_to_next: number
      purpose: string
      completed: boolean
      completed_date: Date | null
    }
  ]
  total_duration_days: number
  graduation_criteria: string  // When to stop regular monitoring
}
```

## AI Integration Details

### Interval Determination Logic
The AI considers:
1. **Condition type** (mole, rash, wound, etc.)
2. **Initial assessment** (benign, concerning, unclear)
3. **Change velocity** (how fast things typically change)
4. **Medical guidelines** (e.g., ABCDE for moles)
5. **User context** (first time vs. ongoing monitoring)

### Example AI Reasoning Responses
```json
// For a new mole
{
  "interval_days": 30,
  "reasoning": "New moles should be monitored monthly for 3 months to establish if they're stable",
  "after_stable": "Can extend to quarterly checks after 3 stable months"
}

// For a healing wound
{
  "interval_days": 3,
  "reasoning": "Wounds change rapidly; check every 3 days until healed",
  "red_flags": "Look for signs of infection: increased redness, pus, or fever"
}

// For chronic eczema
{
  "interval_days": 14,
  "reasoning": "Eczema flares can be tracked bi-weekly to identify triggers",
  "note": "Daily photos during flares can help identify patterns"
}
```

## Notification Templates

### Email Template
```
Subject: Time to update your health tracking

Hi [Name],

It's been [interval] days since your last photo update for your [condition_type].

Taking regular photos helps track changes over time.

[View Session] [Take Photo Now] [Adjust Reminder Settings]

---
You're receiving this because you opted in to reminders. 
[Unsubscribe from this reminder] [Manage all reminders]
```

### In-App Notification
```
"Time to update on your mole" 
[Take Photo] [Remind Later] [Stop Reminders]
```

## Privacy & Security Considerations

1. **Generic reminders**: Never include specific condition details or location
2. **Encrypted storage**: Reminder configurations encrypted at rest
3. **Access control**: Only session owner can configure reminders
4. **Data retention**: Reminder history kept for 1 year
5. **Opt-out**: Easy one-click disable for all reminders
6. **No external sharing**: Reminder data never shared with third parties

## Frontend Integration Notes

### After Analysis Flow
1. Analysis completes
2. If `follow_up_suggestion.benefits_from_tracking = true`:
   - Show non-intrusive card: "Track this over time?"
   - Display AI reasoning
   - Allow interval adjustment
   - Choose notification method
3. User must actively click "Enable Reminders"
4. Confirmation shows next reminder date

### Ongoing Monitoring (Less Intrusive)
- Smaller reminder cards
- "Continue tracking" instead of full setup
- Quick snooze/disable options
- No pop-ups or modals

### Session List Indicators
- Small badge for "due for follow-up"
- Days since last photo
- Next reminder date if active
- Sort by "needs attention"

## Error Handling

### Common Scenarios
1. **Session not found**: 404 with helpful message
2. **Reminder already exists**: Return existing config
3. **Invalid interval**: Suggest appropriate range
4. **Notification failure**: Fallback to in-app
5. **User unsubscribed**: Respect and don't retry

## Rate Limiting
- Configure reminders: 10 per hour
- Update reminders: 20 per hour
- Follow-up photos: Standard upload limits apply

## Future Considerations
1. **Smart intervals**: AI adjusts based on trending
2. **Bulk sessions**: Track multiple conditions together
3. **Family sharing**: Monitor children's conditions
4. **Provider integration**: Share timeline with doctors
5. **Pattern detection**: AI identifies concerning trends

This API design prioritizes user control, privacy, and helpful AI guidance while avoiding notification fatigue.