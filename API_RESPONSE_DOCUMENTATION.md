# API Response Structure Documentation
## Complete Field Reference for All Health Assessment Endpoints

Last Updated: 2025-01-13

---

## 1. Quick Scan API (`/api/quick-scan`)

### Existing Fields (Already Implemented)
```json
{
  "scan_id": "uuid",
  "analysis": {
    "confidence": 85,                    // 0-100 diagnostic confidence
    "primaryCondition": "Tension Headache (tension-type headache)",
    "likelihood": "Very likely",          // Very likely | Likely | Possible
    "symptoms": ["headache", "neck tension", "stress"],
    "recommendations": [                 // 3-5 actionable recommendations
      "Rest in a quiet, dark room",
      "Apply cold compress",
      "Practice stress management"
    ],
    "urgency": "low",                   // low | medium | high
    "differentials": [                  // Alternative diagnoses
      {"condition": "Migraine", "probability": 20},
      {"condition": "Cluster Headache", "probability": 10}
    ],
    "redFlags": [                       // Warning signs requiring immediate care
      "Sudden severe headache",
      "Headache with fever",
      "Vision changes"
    ],
    "selfCare": [                       // Self-management tips
      "Stay hydrated",
      "Maintain regular sleep schedule",
      "Gentle neck stretches"
    ],
    "timeline": "2-3 days",             // Expected recovery timeline
    "followUp": "If no improvement in 3 days or symptoms worsen",
    "relatedSymptoms": [                // Things to monitor
      "Nausea or vomiting",
      "Light sensitivity",
      "Neck stiffness"
    ]
  },
  "body_part": "head",
  "confidence": 85,
  "user_id": "uuid",
  "usage": {},
  "model": "openai/gpt-5-mini",
  "status": "success"
}
```

### New Fields Added (2025-01-13)
```json
{
  "what_this_means": "Your symptoms suggest tension in the head and neck muscles, likely from stress or poor posture. This is common and usually responds well to self-care measures.",
  "immediate_actions": [                // 3-5 specific actions to take right now
    "Take an over-the-counter pain reliever (if appropriate)",
    "Apply a cold compress for 15 minutes",
    "Rest in a quiet, dark room",
    "Practice deep breathing for 5 minutes",
    "Drink 2 glasses of water"
  ]
}
```

### Database Storage
- Table: `quick_scans`
- New columns added:
  - `what_this_means` (TEXT)
  - `immediate_actions` (JSONB)

---

## 2. Deep Dive API (`/api/deep-dive/complete`)

### Existing Fields (Already Implemented)
```json
{
  "deep_dive_id": "uuid",
  "analysis": {
    "confidence": 92,
    "primaryCondition": "Chronic Tension Headache",
    "likelihood": "Very likely",
    "symptoms": ["daily headaches", "neck pain", "stress", "poor sleep"],
    "recommendations": [
      "Consult with neurologist",
      "Start headache diary",
      "Consider preventive medication"
    ],
    "urgency": "medium",
    "differentials": [
      {"condition": "Medication Overuse Headache", "probability": 30},
      {"condition": "Chronic Migraine", "probability": 25}
    ],
    "redFlags": [
      "Sudden change in headache pattern",
      "Neurological symptoms",
      "Fever with headache"
    ],
    "selfCare": [
      "Stress reduction techniques",
      "Regular exercise",
      "Consistent sleep schedule"
    ],
    "timeline": "Improvement expected in 2-4 weeks with treatment",
    "followUp": "Schedule neurologist appointment within 2 weeks",
    "relatedSymptoms": [
      "Jaw clenching",
      "Shoulder tension",
      "Fatigue"
    ],
    "reasoning_snippets": [              // Key insights from Q&A
      "Daily pattern suggests chronic condition",
      "Stress correlation identified",
      "No red flag symptoms present"
    ]
  },
  "body_part": "head",
  "confidence": 92,
  "questions_asked": 5,
  "reasoning_snippets": [],
  "usage": {},
  "status": "success"
}
```

### New Fields Added (2025-01-13)
```json
{
  "what_this_means": "Based on our detailed conversation, your daily headaches appear to be chronic tension-type headaches triggered by stress and poor posture. The pattern suggests this has become a persistent condition that would benefit from a comprehensive treatment approach.",
  "immediate_actions": [
    "Start a headache diary today to track patterns",
    "Schedule an appointment with your primary care provider",
    "Begin daily neck stretches (morning and evening)",
    "Reduce screen time by 1 hour today",
    "Try a guided relaxation app before bed tonight"
  ]
}
```

### Database Storage
- Table: `deep_dive_sessions`
- New columns added:
  - `what_this_means` (TEXT)
  - `immediate_actions` (JSONB)

---

## 3. General Assessment API (`/api/general-assessment`)

### Previous Fields (Before Update)
```json
{
  "assessment_id": "uuid",
  "analysis": {
    "primary_assessment": "Chronic stress affecting energy levels",
    "confidence": 75,
    "key_findings": ["Fatigue", "Poor sleep", "Stress"],
    "possible_causes": [
      {"condition": "Chronic Fatigue", "likelihood": 70, "explanation": "..."}
    ],
    "recommendations": ["Improve sleep hygiene", "Stress management"],
    "urgency": "medium",
    "follow_up_questions": ["How long have you felt this way?"]
  }
}
```

### All New Fields Added (2025-01-13)
```json
{
  "severity_level": "moderate",         // low | moderate | high | urgent
  "confidence_level": "high",           // low | medium | high
  "what_this_means": "Your fatigue and difficulty concentrating suggest your body is dealing with prolonged stress, which is depleting your energy reserves. This pattern often improves with targeted lifestyle changes.",
  "immediate_actions": [
    "Take a 20-minute rest break now",
    "Drink 2 glasses of water",
    "Do 5 minutes of deep breathing",
    "Go to bed 30 minutes earlier tonight",
    "Take a short walk outside"
  ],
  "red_flags": [                        // Warning signs requiring immediate attention
    "Chest pain or palpitations",
    "Severe headache with vision changes",
    "Extreme fatigue preventing daily activities",
    "Sudden weight loss",
    "Persistent fever"
  ],
  "tracking_metrics": [                 // Specific items to monitor daily
    "Energy level 1-10 (morning and evening)",
    "Hours of actual sleep",
    "Number of rest breaks taken",
    "Stress level before bed (1-10)",
    "Physical activity minutes"
  ],
  "follow_up_timeline": {
    "check_progress": "3 days",
    "see_doctor_if": "No improvement after 1 week or symptoms worsen"
  }
}
```

### Database Storage
- Table: `general_assessments`
- New columns added:
  - `severity_level` (TEXT)
  - `confidence_level` (TEXT)
  - `what_this_means` (TEXT)
  - `immediate_actions` (JSONB)
  - `red_flags` (JSONB)
  - `tracking_metrics` (JSONB)
  - `follow_up_timeline` (JSONB)

---

## 4. General Deep Dive API (`/api/general-deepdive/complete`)

### All New Fields Added (2025-01-13)
Same 7 fields as General Assessment:
- `severity_level`
- `confidence_level`
- `what_this_means`
- `immediate_actions`
- `red_flags`
- `tracking_metrics`
- `follow_up_timeline`

### Database Storage
- Table: `general_deepdive_sessions`
- Same new columns as general_assessments

---

## 5. Flash Assessment API (`/api/flash-assessment`)

### NO CHANGES
Flash Assessment remains unchanged and returns the same response structure as before:
```json
{
  "flash_id": "uuid",
  "response": "Your symptoms could indicate...",
  "main_concern": "headache",
  "urgency": "low",
  "confidence": 75,
  "next_steps": {
    "recommended_action": "general-assessment",
    "reason": "To get a more detailed analysis"
  }
}
```

---

## Summary of Changes

### Quick Scan & Deep Dive
- **Already had**: `redFlags`, `selfCare`, `timeline`, `followUp`, `relatedSymptoms`, `recommendations`, `differentials`
- **Added**: `what_this_means`, `immediate_actions` (2 fields only)

### General Assessment & General Deep Dive
- **Added ALL 7 new fields**: `severity_level`, `confidence_level`, `what_this_means`, `immediate_actions`, `red_flags`, `tracking_metrics`, `follow_up_timeline`

### Flash Assessment
- **No changes**

---

## Implementation Details

### How Fields Are Generated
1. **AI-Generated**: All new fields are generated by the LLM based on the analysis, not from templates
2. **Dynamic**: Fields are generated at runtime even if not stored in database
3. **Stored**: Fields are now stored in database for analytics and historical tracking
4. **Backward Compatible**: All existing fields remain unchanged

### Field Generation Priority
1. If the LLM provides the field → Use LLM value
2. If not provided → Generate from existing data
3. If cannot generate → Use sensible defaults

### Database Migration Required
Run `SUPABASE_SIMPLE_MIGRATION.sql` to add the new columns to your database.

---

## Usage Examples

### Quick Scan Request
```bash
POST /api/quick-scan
{
  "body_part": "head",
  "form_data": {
    "symptoms": "severe headache",
    "painLevel": 8
  },
  "user_id": "user-uuid"
}
```

### Response Includes
- All original fields (confidence, primaryCondition, redFlags, etc.)
- Plus: `what_this_means` and `immediate_actions`

### General Assessment Request
```bash
POST /api/general-assessment
{
  "category": "energy",
  "form_data": {
    "symptoms": "chronic fatigue",
    "duration": "3 months"
  },
  "user_id": "user-uuid"
}
```

### Response Includes
- All original analysis fields
- Plus all 7 new enhanced fields

---

## Frontend Integration Notes

### Displaying New Fields
1. **what_this_means**: Display prominently as the main explanation
2. **immediate_actions**: Show as actionable checklist
3. **red_flags**: Display with warning icon
4. **tracking_metrics**: Provide as daily tracking guide
5. **severity_level**: Use for color coding (low=green, moderate=yellow, high=orange, urgent=red)
6. **confidence_level**: Show as confidence indicator
7. **follow_up_timeline**: Display as timeline card

### Backward Compatibility
- Check if fields exist before displaying
- All new fields are optional
- Existing clients will continue to work without modification