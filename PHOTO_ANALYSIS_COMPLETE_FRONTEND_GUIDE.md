# Complete Photo Analysis Frontend Implementation Guide

## Overview
This document combines all photo analysis features including basic functionality, sensitive content handling, and follow-up/reminder systems. Everything your frontend needs to implement a comprehensive photo tracking system.

## Table of Contents
1. [Core Photo Analysis](#core-photo-analysis)
2. [Sensitive Content Handling](#sensitive-content-handling)
3. [Follow-up & Reminders](#follow-up--reminders)
4. [Implementation Summary](#implementation-summary)

---

# Core Photo Analysis

## Key Features
- **Smart Categorization**: Automatically classifies photos into appropriate categories
- **Privacy Protection**: Sensitive photos analyzed without permanent storage
- **Medical Analysis**: Detailed AI-powered assessment using Gemini 2.5 Pro
- **Progress Tracking**: Compare photos over time (non-sensitive only)
- **Report Integration**: Include photo analyses in comprehensive medical reports

## Photo Categories

### 1. `medical_normal`
Standard medical conditions safe for storage:
- Skin conditions (rashes, acne, eczema, psoriasis)
- Injuries (cuts, bruises, sprains)
- Visible infections (non-intimate areas)
- Post-surgical healing (non-intimate)
- Any medical condition NOT in private areas

### 2. `medical_sensitive`
Medical conditions in intimate areas:
- Genital conditions
- Anal/perineal conditions
- **Important**: These photos are analyzed but NOT stored permanently
- Analysis results are kept forever, only photos are temporary

### 3. `medical_gore`
Severe but legitimate medical content:
- Deep wounds
- Active surgical procedures
- Severe trauma
- Major burns

### 4. `unclear`
Photos that cannot be properly analyzed:
- Too blurry
- Poor lighting
- Obstructed view

### 5. `non_medical`
Not medical content

### 6. `inappropriate`
Illegal content (extremely rare)

## API Endpoints

### 1. Create Photo Session
```
POST /api/photo-analysis/sessions
Content-Type: application/json

{
  "user_id": "user-uuid",
  "condition_name": "Skin Rash on Arm",
  "description": "Red, itchy rash that appeared 3 days ago"
}

Response:
{
  "session_id": "session-uuid",
  "condition_name": "Skin Rash on Arm",
  "created_at": "2025-01-31T..."
}
```

### 2. Upload Photos
```
POST /api/photo-analysis/upload
Content-Type: multipart/form-data

photos: [files] (max 5)
session_id: "session-uuid"
user_id: "user-uuid"
condition_name: "Condition Name" (if new session)
description: "Optional description"

Response:
{
  "session_id": "session-uuid",
  "uploaded_photos": [
    {
      "id": "photo-uuid",
      "category": "medical_normal",
      "stored": true,
      "preview_url": "https://..."
    }
  ],
  "requires_action": null
}
```

### 3. Analyze Photos
```
POST /api/photo-analysis/analyze
Content-Type: application/json

{
  "session_id": "session-uuid",
  "photo_ids": ["photo-uuid-1", "photo-uuid-2"],
  "context": "Additional context from user",
  "comparison_photo_ids": ["older-photo-uuid"],
  "temporary_analysis": false
}

Response:
{
  "analysis_id": "analysis-uuid",
  "analysis": {
    "primary_assessment": "Atopic dermatitis (eczema)",
    "confidence": 85,
    "visual_observations": [
      "Red, inflamed patches on forearm",
      "Visible scaling and dryness",
      "No signs of infection"
    ],
    "differential_diagnosis": [
      "Contact dermatitis",
      "Psoriasis"
    ],
    "recommendations": [
      "Apply fragrance-free moisturizer 3x daily",
      "Avoid hot showers",
      "See dermatologist if no improvement in 1 week"
    ],
    "red_flags": [],
    "trackable_metrics": [
      {
        "metric_name": "Rash Size",
        "current_value": 5,
        "unit": "cm",
        "suggested_tracking": "weekly"
      }
    ]
  },
  "comparison": {
    "days_between": 7,
    "changes": {
      "size": {"from": 3, "to": 5, "unit": "cm", "change": 67},
      "color": {"description": "Increased redness"},
      "texture": {"description": "More scaling visible"}
    },
    "trend": "worsening",
    "ai_summary": "The rash has expanded and shows increased inflammation"
  },
  "expires_at": null
}
```

### 4. Get Photo Sessions
```
GET /api/photo-analysis/sessions?user_id=uuid&limit=20&offset=0

Response:
{
  "sessions": [
    {
      "id": "session-uuid",
      "condition_name": "Skin Rash",
      "created_at": "2025-01-31T...",
      "last_photo_at": "2025-01-31T...",
      "photo_count": 3,
      "analysis_count": 2,
      "is_sensitive": false,
      "latest_summary": "Atopic dermatitis",
      "thumbnail_url": "https://..."
    }
  ],
  "total": 5,
  "has_more": false
}
```

---

# Sensitive Content Handling

## How It Works
1. **Upload**: Photo is uploaded and categorized
2. **Temporary Storage**: If sensitive, base64 data stored in `temporary_data` field
3. **Analysis**: Full medical analysis performed normally
4. **Cleanup**: Photo data deleted after 24 hours
5. **Results Persist**: Analysis results kept permanently

## User Experience
When a sensitive photo is detected, the frontend should display:
```
⚠️ Sensitive Content Detected

This photo contains sensitive medical content. 

What will happen:
✓ Photo will be analyzed by our medical AI
✓ Analysis results will be saved permanently
✗ Photo will NOT be stored permanently
✗ You cannot track visual changes over time

Options:
[Proceed with Analysis] [Retake Different Photo]
```

## Technical Implementation
```json
// Sensitive photo upload response
{
  "session_id": "uuid",
  "uploaded_photos": [{
    "id": "photo-uuid",
    "category": "medical_sensitive",
    "stored": false,
    "preview_url": null
  }],
  "requires_action": {
    "type": "sensitive_modal",
    "affected_photos": ["photo-uuid"],
    "message": "Sensitive content detected. Photos will be analyzed temporarily without permanent storage."
  }
}
```

## Error Handling

### Retry Logic
- All AI calls automatically retry up to 3 times with exponential backoff
- Primary model: `google/gemini-2.5-pro`
- Fallback model: `google/gemini-2.0-flash-exp:free`

### Common Errors
```json
// File too large
{
  "status_code": 413,
  "detail": "File too large (max 10MB)"
}

// Invalid file type
{
  "status_code": 400,
  "detail": "Invalid file type. Allowed: image/jpeg, image/png, image/heic, image/heif, image/webp"
}

// Sensitive photo without data
{
  "status_code": 400,
  "detail": "Cannot analyze photo without data"
}
```

---

# Follow-up & Reminders

## Core Principles
- **Opt-in only**: No reminders unless explicitly requested
- **User control**: Full control over intervals and notification methods
- **Privacy-focused**: Generic reminder text, no specific condition details
- **AI-guided**: Intelligent interval suggestions based on condition type
- **Non-intrusive**: Especially for ongoing monitoring

## Follow-up API Endpoints

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

### 4. Get Session Timeline with Reminders
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

---

# Implementation Summary

## Frontend Flow

### 1. Initial Photo Upload
```javascript
// Create session
const session = await createPhotoSession({
  user_id: currentUser.id,
  condition_name: 'Mole on left arm',
  description: 'Concerned about color changes'
});

// Upload photos
const formData = new FormData();
formData.append('photos', file);
formData.append('session_id', session.session_id);
formData.append('user_id', currentUser.id);

const upload = await uploadPhotos(formData);

// Handle sensitive content
if (upload.requires_action?.type === 'sensitive_modal') {
  const userConsent = await showSensitiveContentModal();
  if (!userConsent) return;
}

// Analyze photos
const analysis = await analyzePhotos({
  session_id: session.session_id,
  photo_ids: upload.uploaded_photos.map(p => p.id)
});

// Show results
displayAnalysisResults(analysis);

// Offer follow-up reminders if beneficial
if (analysis.analysis.trackable_metrics?.length > 0) {
  const enableReminders = await showReminderOptIn({
    condition: analysis.analysis.primary_assessment,
    suggestedInterval: 30,
    reasoning: "Monthly monitoring recommended for moles"
  });
  
  if (enableReminders) {
    await configureReminders({
      session_id: session.session_id,
      analysis_id: analysis.analysis_id,
      interval_days: 30,
      reminder_method: 'email'
    });
  }
}
```

### 2. Follow-up Photo (Returning User)
```javascript
// User returns to session after 30 days
const followUpResult = await addFollowUpPhotos(sessionId, {
  photos: newPhotos,
  auto_compare: true,
  notes: "No changes noticed"
});

// Show comparison
displayComparison({
  before: followUpResult.comparison_results.compared_with,
  after: followUpResult.uploaded_photos,
  trend: followUpResult.comparison_results.analysis.trend,
  changes: followUpResult.comparison_results.analysis.changes
});

// Update reminder settings if needed
if (followUpResult.follow_up_suggestion.benefits_from_tracking) {
  // Show subtle option to adjust reminder interval
  showReminderAdjustment({
    current: 30,
    suggested: followUpResult.follow_up_suggestion.suggested_interval_days
  });
}
```

### 3. Session List View
```javascript
// Show sessions with follow-up indicators
const sessions = await getPhotoSessions(userId);

sessions.forEach(session => {
  // Display session card with:
  // - Thumbnail (if not sensitive)
  // - Days since last photo
  // - "Due for follow-up" badge if > suggested interval
  // - Latest assessment summary
  
  if (daysSinceLastPhoto(session) > 30 && session.condition_name.includes('mole')) {
    showFollowUpBadge(session);
  }
});
```

## Best Practices

### Frontend Implementation
1. **Size Validation**: Check file size before upload (10MB max)
2. **Type Validation**: Only allow supported image types
3. **Sensitive Content Modal**: Always show warning for sensitive photos
4. **Progress Indicators**: Show upload and analysis progress
5. **Error Recovery**: Allow retry on failure

### Privacy Considerations
1. **No Permanent Storage**: Sensitive photos never stored permanently
2. **24-Hour Cleanup**: Automatic deletion of temporary data
3. **User Consent**: Always get explicit consent before analyzing sensitive content
4. **Secure Transmission**: Use HTTPS for all photo uploads
5. **Access Control**: Photos only accessible to uploading user

### UX Guidelines

#### After Analysis Flow (Opt-in Reminders)
1. Analysis completes
2. If condition benefits from tracking:
   - Show non-intrusive card: "Track this over time?"
   - Display AI reasoning
   - Allow interval adjustment
   - Choose notification method
3. User must actively click "Enable Reminders"
4. Confirmation shows next reminder date

#### Ongoing Monitoring (Less Intrusive)
- Smaller reminder cards
- "Continue tracking" instead of full setup
- Quick snooze/disable options
- No pop-ups or modals

#### Mobile-Friendly Features
1. **Quick Re-photo**: Overlay previous photo as ghost image for alignment
2. **One-tap follow-up**: From session list, directly open camera
3. **Progress badges**: Visual indicators of improvement/worsening

## Reports Integration

### Photo Analysis Report
Generate a dedicated photo analysis report:
```
POST /api/photo-analysis/reports/photo-analysis
{
  "user_id": "user-uuid",
  "session_ids": ["session-uuid-1", "session-uuid-2"],
  "include_visual_timeline": true,
  "include_tracking_data": true,
  "time_range_days": 30  // Optional, null for all time
}
```

### Integration with Other Reports
Photo analyses can be included in any report type by adding `photo_session_ids`:

```
POST /api/reports/specialist
{
  "analysis_id": "analysis-uuid",
  "specialty": "dermatology",
  "photo_session_ids": ["session-uuid"]  // Optional
}
```

When photo data is included, reports will contain:
- Visual assessments and observations
- Progression tracking (non-sensitive photos only)
- AI-generated insights from visual data
- Correlation with other health data

## Security & Privacy

### Key Points
1. **Sensitive photos** are NEVER stored in permanent storage
2. **Temporary data** is automatically cleaned after 24 hours
3. **Generic reminders** never include specific condition details
4. **Full user control** over all reminder settings
5. **Easy opt-out** at any time

### Database Requirements
The following migration must be run:
```sql
-- Add temporary_data column for sensitive photos
ALTER TABLE photo_uploads 
ADD COLUMN IF NOT EXISTS temporary_data TEXT;

-- Add index for cleanup
CREATE INDEX IF NOT EXISTS idx_photo_uploads_temporary_data 
ON photo_uploads(uploaded_at) 
WHERE temporary_data IS NOT NULL;
```

## Testing Checklist

### Sensitive Photo Flow
- [ ] Upload genital/intimate area photo
- [ ] Verify categorization as `medical_sensitive`
- [ ] Confirm analysis works without storage
- [ ] Check temporary_data cleanup after 24 hours

### Follow-up Flow
- [ ] Create session with initial photos
- [ ] Return after 30 days to add follow-up
- [ ] Verify automatic comparison works
- [ ] Check timeline view shows progression

### Reminder Flow
- [ ] Complete analysis of trackable condition
- [ ] See opt-in reminder suggestion
- [ ] Configure reminders
- [ ] Verify reminder arrives at scheduled time
- [ ] Test disable/snooze functionality

## AI Examples

### Condition-Specific Intervals
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

## Support & Questions

This comprehensive guide covers all photo analysis features. For optimal UX:
- Make the sensitive content flow clear and reassuring
- Keep reminders opt-in and non-intrusive
- Focus on helping users track conditions over time
- Prioritize privacy and user control

The backend fully supports all these features with proper error handling, retry logic, and privacy protection.