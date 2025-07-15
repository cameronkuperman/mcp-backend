# Medical Report API Structure & Usage Guide

This guide explains exactly how to call the report APIs and what structure you get back.

## API Call Flow

### Step 1: Analyze What Report Type to Generate

**Endpoint:** `POST /api/report/analyze`

**What you send:**
```typescript
{
  user_id?: string;
  context: {
    purpose?: 'symptom_specific' | 'annual_checkup' | 'specialist_referral' | 'emergency';
    symptom_focus?: string;
    time_frame?: {
      start?: string;  // ISO date
      end?: string;    // ISO date
    };
    target_audience?: 'self' | 'primary_care' | 'specialist' | 'emergency';
  };
  available_data?: {
    quick_scan_ids?: string[];
    deep_dive_ids?: string[];
    photo_session_ids?: string[];
  };
}
```

**What comes back:**
```typescript
{
  recommended_endpoint: string;     // "/api/report/urgent-triage"
  recommended_type: string;         // "urgent_triage"
  reasoning: string;                // "Emergency symptoms detected requiring immediate attention"
  confidence: number;               // 0.95
  report_config: {
    time_range: {
      start: string;                // "2024-01-01T00:00:00Z"
      end: string;                  // "2024-01-08T00:00:00Z"
    };
    primary_focus: string;          // "chest pain"
    include_sections: string[];     // ["triage_summary", "immediate_actions"]
    data_sources: {
      quick_scans: string[];        // ["scan-id-1", "scan-id-2"]
      deep_dives: string[];         // ["dive-id-1"]
    };
    urgency_level: string;          // "emergency"
  };
  analysis_id: string;              // "uuid-for-this-analysis"
  status: 'success' | 'error';
}
```

### Step 2: Generate the Actual Report

Use the `analysis_id` from step 1 and call the recommended endpoint.

**Endpoint:** `POST /api/report/{type}` (where type is from recommended_type)

**What you send:**
```typescript
{
  analysis_id: string;    // From step 1
  user_id?: string;
}
```

## Report Response Structures

### Comprehensive Report Response

```typescript
{
  report_id: string;
  report_type: "comprehensive";
  generated_at: string;         // ISO timestamp
  report_data: {
    executive_summary: {
      one_page_summary: string;           // Full paragraph summary
      chief_complaints: string[];         // ["Recurring headaches", "Sleep issues"]
      key_findings: string[];             // ["Stress-related patterns", "Caffeine correlation"]
      urgency_indicators: string[];       // ["No immediate red flags"]
      action_items: string[];             // ["Schedule primary care visit", "Track sleep"]
    };
    patient_story: {
      symptoms_timeline: Array<{
        date: string;                     // "2024-01-15"
        symptom: string;                  // "Headache"
        severity: number;                 // 7 (out of 10)
        patient_description: string;      // "Throbbing pain behind right eye"
      }>;
      pain_patterns: {
        locations: string[];              // ["Right temple", "Behind eyes"]
        triggers: string[];               // ["Stress", "Bright lights"]
        relievers: string[];              // ["Dark room", "Ibuprofen"]
        progression: string;              // "Worsening over past 2 weeks"
      };
    };
    medical_analysis: {
      conditions_assessed: Array<{
        condition: string;                // "Tension Headache (stress headache)"
        likelihood: string;               // "Very likely"
        supporting_evidence: string[];    // ["Stress correlation", "Pattern matches"]
        from_sessions: string[];          // ["scan-id-1", "dive-id-2"]
      }>;
      symptom_correlations: string[];     // ["Headaches worsen with work stress"]
      risk_factors: string[];             // ["High stress job", "Poor sleep hygiene"]
    };
    action_plan: {
      immediate_actions: string[];        // ["Continue tracking symptoms"]
      diagnostic_tests: string[];         // ["Consider stress assessment"]
      lifestyle_changes: string[];        // ["Improve sleep schedule", "Stress management"]
      monitoring_plan: string[];          // ["Track headache frequency", "Note triggers"]
      follow_up_timeline: string;        // "2 weeks if no improvement"
    };
  };
  confidence_score: number;              // 85
  model_used: string;                    // "tngtech/deepseek-r1t-chimera:free"
  status: 'success' | 'error';
}
```

### Urgent Triage Report Response

```typescript
{
  report_id: string;
  report_type: "urgent_triage";
  generated_at: string;
  report_data: {
    triage_summary: {
      immediate_concerns: string[];       // ["Severe chest pain", "Difficulty breathing"]
      vital_symptoms: Array<{
        symptom: string;                  // "Chest pain"
        severity: 'mild' | 'moderate' | 'severe';  // "severe"
        duration: string;                 // "Started 2 hours ago"
        red_flags: string[];              // ["Radiating to left arm", "Shortness of breath"]
      }>;
      recommended_action: string;         // "Call 911 immediately"
      what_to_tell_doctor: string[];      // ["Sudden onset chest pain", "Pain scale 9/10"]
      recent_progression: string;         // "Pain increasing rapidly over last hour"
    };
  };
  status: 'success' | 'error';
}
```

### Symptom Timeline Report Response

```typescript
{
  report_id: string;
  report_type: "symptom_timeline";
  generated_at: string;
  report_data: {
    executive_summary: {
      one_page_summary: string;
      chief_complaints: string[];
      key_findings: string[];
    };
    symptom_progression: {
      primary_symptom: string;            // "Headaches"
      timeline: Array<{
        date: string;                     // "2024-01-01"
        severity: number;                 // 6
        description: string;              // "Dull ache, lasted 3 hours"
        triggers_identified: string[];    // ["Work stress", "Skipped lunch"]
        treatments_tried: string[];       // ["Ibuprofen", "Rest"]
        effectiveness: string;            // "Partial relief after 1 hour"
      }>;
      patterns_identified: {
        frequency: string;                // "3-4 times per week"
        peak_times: string[];             // ["Afternoon", "Evening"]
        seasonal_trends: string;          // "Worse in winter months"
        correlation_factors: string[];    // ["Work deadlines", "Poor sleep"]
      };
    };
    trend_analysis: {
      overall_direction: string;          // "Worsening"
      severity_trend: string;             // "Increasing from 4/10 to 7/10"
      frequency_trend: string;            // "More frequent - daily vs weekly"
      response_to_treatment: string;      // "Less responsive to OTC pain meds"
    };
  };
  status: 'success' | 'error';
}
```

### Photo Progression Report Response

```typescript
{
  report_id: string;
  report_type: "photo_progression";
  generated_at: string;
  report_data: {
    executive_summary: {
      one_page_summary: string;
      key_findings: string[];
    };
    visual_analysis: {
      photos_analyzed: Array<{
        photo_id: string;                 // "photo-session-id-1"
        date: string;                     // "2024-01-15"
        ai_description: string;           // "Red, inflamed area on left forearm"
        size_measurement: string;         // "Approximately 2cm diameter"
        color_changes: string[];          // ["Increased redness", "More defined borders"]
        concerning_features: string[];    // ["Irregular shape", "Color variation"]
      }>;
      progression_summary: {
        overall_change: string;           // "Condition appears to be worsening"
        size_change: string;              // "Increased by approximately 30%"
        color_evolution: string;          // "Darker pigmentation, more irregular"
        texture_changes: string;          // "More raised, rougher surface"
        border_changes: string;           // "Less defined, more irregular"
      };
      ai_recommendations: {
        urgency_level: string;            // "High - requires dermatologist evaluation"
        specific_concerns: string[];      // ["Rapid growth", "Color irregularity"]
        recommended_timeline: string;     // "Within 1-2 weeks"
        what_to_monitor: string[];        // ["Further size changes", "New symptoms"]
      };
    };
  };
  status: 'success' | 'error';
}
```

### Annual Summary Report Response

```typescript
{
  report_id: string;
  report_type: "annual_summary";
  generated_at: string;
  report_data: {
    executive_summary: {
      one_page_summary: string;
      key_findings: string[];
      action_items: string[];
    };
    yearly_overview: {
      total_assessments: number;          // 47
      most_common_concerns: string[];     // ["Headaches", "Back pain", "Sleep issues"]
      health_trends: {
        improving_areas: string[];        // ["Sleep quality", "Exercise frequency"]
        concerning_trends: string[];      // ["Increasing headache frequency"]
        stable_conditions: string[];      // ["Blood pressure readings"]
      };
      seasonal_patterns: {
        winter_issues: string[];          // ["More respiratory symptoms"]
        summer_concerns: string[];        // ["Allergy symptoms"]
        year_round_stable: string[];      // ["Energy levels"]
      };
    };
    health_metrics: {
      symptom_frequency: Record<string, number>;  // {"headaches": 23, "back_pain": 15}
      severity_averages: Record<string, number>;  // {"headaches": 6.2, "back_pain": 4.8}
      improvement_tracking: {
        symptoms_resolved: string[];      // ["Shoulder pain", "Anxiety episodes"]
        new_symptoms: string[];           // ["Occasional dizziness"]
        chronic_patterns: string[];       // ["Weekly tension headaches"]
      };
    };
    preventive_recommendations: {
      screening_due: string[];            // ["Annual physical", "Eye exam"]
      lifestyle_goals: string[];          // ["Stress management", "Better sleep hygiene"]
      monitoring_priorities: string[];    // ["Blood pressure", "Headache patterns"]
      specialist_referrals: string[];     // ["Neurologist for headaches"]
    };
  };
  status: 'success' | 'error';
}
```

## How the AI Works

### AI Decision Process for Report Type

The AI looks at your request and decides which report type based on:

1. **Emergency Keywords**: "chest pain", "difficulty breathing", "severe headache" → **Urgent Triage**
2. **Purpose = "emergency"** → **Urgent Triage**
3. **Purpose = "annual_checkup"** → **Annual Summary**
4. **3+ photo sessions available** → **Photo Progression**
5. **Specific symptom mentioned** → **Symptom Timeline**
6. **Target audience = "specialist"** → **Specialist Report**
7. **Default** → **Comprehensive**

### AI Content Generation

Each report type uses a specialized AI prompt:

**Comprehensive Reports**: AI analyzes all your health data to create a complete medical picture
- Uses model: `tngtech/deepseek-r1t-chimera:free`
- Temperature: 0.3 (balanced creativity/accuracy)
- Max tokens: 3000 (longer responses)

**Urgent Triage**: AI focuses on immediate risks and next steps
- Uses model: `tngtech/deepseek-r1t-chimera:free`
- Temperature: 0.2 (higher accuracy for safety)
- Max tokens: 1000 (concise emergency info)

**Timeline Reports**: AI tracks patterns over time
- Analyzes symptom progression
- Identifies triggers and correlations
- Tracks treatment effectiveness

## Example API Usage

### Complete Flow Example

```javascript
// Step 1: Analyze
const analysis = await fetch('/api/report/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'user-123',
    context: {
      purpose: 'symptom_specific',
      symptom_focus: 'recurring headaches',
      target_audience: 'primary_care'
    },
    available_data: {
      quick_scan_ids: ['scan-1', 'scan-2'],
      deep_dive_ids: ['dive-1']
    }
  })
}).then(r => r.json());

// Analysis response:
// {
//   recommended_endpoint: "/api/report/symptom-timeline",
//   recommended_type: "symptom_timeline",
//   reasoning: "Specific symptom mentioned with historical data available",
//   confidence: 0.88,
//   analysis_id: "analysis-uuid-123"
// }

// Step 2: Generate report using recommended endpoint
const report = await fetch('/api/report/symptom-timeline', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    analysis_id: analysis.analysis_id,
    user_id: 'user-123'
  })
}).then(r => r.json());

// Report comes back with full structure shown above
console.log(report.report_data.executive_summary.one_page_summary);
console.log(report.report_data.symptom_progression.timeline);
```

### Error Handling

```javascript
try {
  const analysis = await fetch('/api/report/analyze', { /* ... */ });
  if (!analysis.ok) throw new Error('Analysis failed');
  
  const report = await fetch(analysis.recommended_endpoint, { /* ... */ });
  if (!report.ok) throw new Error('Report generation failed');
  
  // Use report.report_data
} catch (error) {
  // Handle AI generation failures
  console.error('Report generation failed:', error);
}
```

## Key Points

1. **Always call analyze first** - Don't guess which report type to use
2. **Use the analysis_id** - Required for all report generation calls
3. **Check the status field** - Reports can fail, always verify success
4. **Different structures per type** - Urgent triage is different from comprehensive
5. **AI confidence scores** - Higher confidence = more reliable analysis
6. **Model information included** - Know which AI model generated your report

This is exactly how the reports work and what you get back from each API call.