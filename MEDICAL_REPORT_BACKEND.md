# Medical Report Generation Backend

Two-stage report system: analyze determines report type → call specific endpoint for that type.

## Flow Overview

1. Frontend calls `/api/report/analyze` with context
2. Backend analyzes and returns `recommended_endpoint` 
3. Frontend calls the recommended endpoint to generate report

## API Endpoints

### Stage 1: Analyze and Route
**POST** `/api/report/analyze`

Determines which report endpoint to use based on context and available data.

```typescript
interface ReportAnalyzeRequest {
  user_id?: string;  // Optional for anonymous
  context: {
    purpose?: 'symptom_specific' | 'annual_checkup' | 'specialist_referral' | 'emergency';
    symptom_focus?: string;  // e.g., "headache", "chest pain"
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

interface ReportAnalyzeResponse {
  recommended_endpoint: string;  // Which endpoint to call next!
  recommended_type: 'comprehensive' | 'urgent_triage' | 'photo_progression' | 
                   'symptom_timeline' | 'specialist_focused' | 'annual_summary';
  reasoning: string;
  confidence: number;
  
  report_config: {
    time_range: {
      start: string;
      end: string;
    };
    primary_focus: string;
    include_sections: string[];
    data_sources: {
      quick_scans: string[];
      deep_dives: string[];
      symptom_entries: string[];  // Intelligently merged
      photo_sessions: string[];
    };
    urgency_level: 'routine' | 'urgent' | 'emergency';
  };
  
  // Pass this to the next endpoint
  analysis_id: string;
  
  status: 'success' | 'error';
}
```

### Stage 2: Report Generation Endpoints

Each endpoint expects the `analysis_id` from the analyze step.

#### 2.1 Comprehensive Report
**POST** `/api/report/comprehensive`

```typescript
interface ComprehensiveReportRequest {
  analysis_id: string;  // From analyze endpoint
  user_id?: string;
}

interface ComprehensiveReportResponse {
  report_id: string;
  report_type: 'comprehensive';
  generated_at: string;
  
  report_data: {
    // Executive Summary (1-page overview - ALWAYS included)
    executive_summary: {
      one_page_summary: string;
      chief_complaints: string[];
      key_findings: string[];
      urgency_indicators: string[];
      action_items: string[];
    };
    
    // Patient Narrative Section
    patient_story: {
      symptoms_timeline: Array<{
        date: string;
        symptom: string;
        severity: number;
        source: 'quick_scan' | 'deep_dive' | 'tracking';
        related_session_id?: string;
        patient_description: string;
      }>;
      pain_patterns: {
        locations: string[];
        triggers: string[];
        relievers: string[];
        progression: string;
      };
    };
    
    // Clinical Analysis
    medical_analysis: {
      conditions_assessed: Array<{
        condition: string;
        likelihood: string;
        supporting_evidence: string[];
        from_sessions: string[];
      }>;
      symptom_correlations: string[];
      risk_factors: string[];
    };
    
    // Visual Documentation (if photos exist)
    photo_documentation?: {
      summary: string;
      progression_analysis: string;
      key_observations: string[];
    };
    
    // Recommendations
    action_plan: {
      immediate_actions: string[];
      diagnostic_tests: string[];
      lifestyle_changes: string[];
      monitoring_plan: string[];
      follow_up_timeline: string;
    };
    
    // Data Sources Used
    metadata: {
      sessions_included: number;
      date_range: string;
      confidence_score: number;
      generated_by_model: string;
    };
  };
  
  status: 'success' | 'error';
}
```

#### 2.2 Urgent Triage Report
**POST** `/api/report/urgent-triage`

```typescript
interface UrgentTriageRequest {
  analysis_id: string;
  user_id?: string;
}

interface UrgentTriageResponse {
  report_id: string;
  report_type: 'urgent_triage';
  
  // This IS the 1-page emergency summary
  triage_summary: {
    immediate_concerns: string[];
    vital_symptoms: {
      symptom: string;
      severity: string;
      duration: string;
      red_flags: string[];
    }[];
    recommended_action: 'Call 911' | 'ER Now' | 'Urgent Care Today';
    what_to_tell_doctor: string[];
    recent_progression: string;
  };
  
  status: 'success' | 'error';
}
```

#### 2.3 Photo Progression Report
**POST** `/api/report/photo-progression`

```typescript
interface PhotoProgressionRequest {
  analysis_id: string;
  user_id?: string;
}

interface PhotoProgressionResponse {
  report_id: string;
  report_type: 'photo_progression';
  
  report_data: {
    executive_summary: {
      one_page_summary: string;
      visual_trend: 'improving' | 'worsening' | 'stable';
      key_changes: string[];
    };
    
    progression_timeline: Array<{
      date: string;
      photo_session_id: string;
      ai_observations: string[];
      measurements?: {
        size?: string;
        color_changes?: string;
        texture_notes?: string;
      };
      change_from_baseline: string;
    }>;
    
    clinical_interpretation: {
      healing_assessment: string;
      concerning_features: string[];
      positive_indicators: string[];
      recommended_monitoring: string;
    };
  };
  
  status: 'success' | 'error';
}
```

#### 2.4 Symptom Timeline Report
**POST** `/api/report/symptom-timeline`

```typescript
interface SymptomTimelineRequest {
  analysis_id: string;
  user_id?: string;
  symptom_focus: string;  // Which symptom to track
}

interface SymptomTimelineResponse {
  report_id: string;
  report_type: 'symptom_timeline';
  
  report_data: {
    executive_summary: {
      one_page_summary: string;
      symptom_overview: string;
      total_duration: string;
      current_status: string;
    };
    
    timeline_data: {
      symptom_focus: string;
      first_occurrence: string;
      
      timeline_entries: Array<{
        date: string;
        severity: number;
        description: string;
        triggers?: string[];
        relief_methods?: string[];
        session_type: 'quick_scan' | 'deep_dive' | 'tracking';
        session_id: string;
        ai_insights: string[];
      }>;
      
      pattern_analysis: {
        frequency_pattern: string;
        severity_trend: 'improving' | 'worsening' | 'stable' | 'fluctuating';
        identified_triggers: string[];
        effective_treatments: string[];
      };
    };
  };
  
  status: 'success' | 'error';
}
```

#### 2.5 Specialist Report
**POST** `/api/report/specialist`

```typescript
interface SpecialistReportRequest {
  analysis_id: string;
  user_id?: string;
  specialty?: string;  // e.g., "neurology", "cardiology"
}

interface SpecialistReportResponse {
  report_id: string;
  report_type: 'specialist_focused';
  
  report_data: {
    executive_summary: {
      one_page_summary: string;
      referral_reason: string;
      key_findings: string[];
    };
    
    specialty_sections: {
      relevant_history: string[];
      examination_findings: string[];
      diagnostic_considerations: string[];
      recommended_workup: string[];
    };
    
    supporting_data: {
      symptom_documentation: any[];
      relevant_sessions: any[];
      timeline_summary: string;
    };
  };
  
  status: 'success' | 'error';
}
```

#### 2.6 Annual Summary Report
**POST** `/api/report/annual-summary`

```typescript
interface AnnualSummaryRequest {
  analysis_id: string;
  user_id: string;  // Required for annual
  year?: number;
}

interface AnnualSummaryResponse {
  report_id: string;
  report_type: 'annual_summary';
  
  report_data: {
    executive_summary: {
      one_page_summary: string;
      health_highlights: string[];
      areas_of_concern: string[];
    };
    
    yearly_overview: {
      total_interactions: number;
      major_health_events: Array<{
        month: string;
        event: string;
        outcome: string;
      }>;
      
      symptom_frequency: {
        [symptom: string]: {
          occurrences: number;
          trend: string;
        };
      };
      
      preventive_care_notes: string[];
    };
  };
  
  status: 'success' | 'error';
}
```

## Implementation Flow

```python
# In run_oracle.py

@app.post("/api/report/analyze")
async def analyze_report_type(request: ReportAnalyzeRequest):
    """Determine which report type and endpoint to use"""
    
    # Analyze context and data
    if has_emergency_indicators(request):
        endpoint = "/api/report/urgent-triage"
        report_type = "urgent_triage"
    elif request.context.get("purpose") == "annual_checkup":
        endpoint = "/api/report/annual-summary"
        report_type = "annual_summary"
    elif len(request.available_data.get("photo_session_ids", [])) >= 3:
        endpoint = "/api/report/photo-progression"
        report_type = "photo_progression"
    elif request.context.get("symptom_focus"):
        endpoint = "/api/report/symptom-timeline"
        report_type = "symptom_timeline"
    elif request.context.get("target_audience") == "specialist":
        endpoint = "/api/report/specialist"
        report_type = "specialist_focused"
    else:
        endpoint = "/api/report/comprehensive"
        report_type = "comprehensive"
    
    # Save analysis for next step
    analysis_id = save_analysis(request, endpoint, report_type)
    
    return {
        "recommended_endpoint": endpoint,
        "recommended_type": report_type,
        "analysis_id": analysis_id,
        # ... rest of response
    }

@app.post("/api/report/comprehensive")
async def generate_comprehensive_report(request: ComprehensiveReportRequest):
    """Generate comprehensive medical report"""
    # Load analysis config
    analysis = load_analysis(request.analysis_id)
    
    # Generate report based on analysis
    # ... implementation
```

## Frontend Usage Example

```typescript
// 1. First, analyze what type of report to generate
const analysis = await fetch('/api/report/analyze', {
  method: 'POST',
  body: JSON.stringify({
    user_id: userId,
    context: {
      purpose: 'symptom_specific',
      symptom_focus: 'recurring headaches',
      target_audience: 'primary_care'
    }
  })
});

const { recommended_endpoint, analysis_id } = await analysis.json();

// 2. Then call the recommended endpoint
const report = await fetch(recommended_endpoint, {
  method: 'POST',
  body: JSON.stringify({
    analysis_id: analysis_id,
    user_id: userId
  })
});

const reportData = await report.json();
// Display report to user
```

## Key Benefits

1. **Clear Routing**: Analyze decides, then route to specific endpoint
2. **Specialized Endpoints**: Each report type has its own endpoint and response format
3. **Consistent Pattern**: Matches your existing multi-endpoint pattern (quick-scan, deep-dive, etc.)
4. **Flexible**: Easy to add new report types as new endpoints
5. **Analysis Reuse**: Can regenerate reports using same analysis_id