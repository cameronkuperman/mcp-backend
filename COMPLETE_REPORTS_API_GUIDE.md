# Complete Reports API Guide

## Table of Contents
1. [Overview](#overview)
2. [Report Flow Architecture](#report-flow-architecture)
3. [General Reports](#general-reports)
4. [Specialist Reports](#specialist-reports)
5. [Time-Based Reports](#time-based-reports)
6. [Urgent/Triage Reports](#urgent-triage-reports)
7. [Photo Analysis Reports](#photo-analysis-reports)
8. [Implementation Guide](#implementation-guide)

---

## Overview

The Oracle Health API provides comprehensive medical report generation across multiple categories. Each report type follows a consistent pattern:

1. **Data Collection**: Gather relevant health data from various sources
2. **AI Analysis**: Process data through specialized AI models
3. **Report Generation**: Create structured, actionable reports
4. **Storage**: Save reports for future reference

### Common Response Structure
```json
{
  "report_id": "uuid",
  "report_type": "string",
  "generated_at": "ISO timestamp",
  "report_data": {
    // Report-specific content
  },
  "status": "success|error"
}
```

---

## Report Flow Architecture

```
User Request → Data Gathering → AI Analysis → Report Generation → Response
     ↓              ↓                ↓              ↓              ↓
  Validate      Query DB      Call AI Models   Format Data    Store & Return
```

### Key Components:
- **Request Models**: Pydantic models for validation
- **Data Gathering**: Supabase queries for health data
- **AI Processing**: OpenRouter API calls with various models
- **Report Storage**: `medical_reports` table

---

## General Reports

### 1. Report Analysis
**Endpoint**: `POST /api/reports/analyze`

**Purpose**: Analyzes available health data and suggests which reports would be most valuable.

**Request**:
```json
{
  "user_id": "uuid",
  "context": {
    "recent_symptoms": ["headache", "fatigue"],
    "time_frame": "last_30_days"
  },
  "available_data": {
    "quick_scans": ["scan-id-1", "scan-id-2"],
    "deep_dives": ["dive-id-1"]
  }
}
```

**Response**:
```json
{
  "report_id": "analysis-uuid",
  "suggested_reports": [
    {
      "report_type": "comprehensive",
      "relevance_score": 0.95,
      "reasoning": "Multiple symptoms suggest comprehensive analysis needed",
      "estimated_insights": 15
    }
  ],
  "data_availability": {
    "has_quick_scans": true,
    "has_deep_dives": true,
    "has_photos": false,
    "has_tracking": true
  }
}
```

**Flow**:
1. Validate user and gather metadata about available data
2. Use AI to analyze patterns and suggest relevant reports
3. Return prioritized list of recommended reports

### 2. Comprehensive Report
**Endpoint**: `POST /api/reports/comprehensive`

**Purpose**: Generates a complete health overview combining all available data sources.

**Request**:
```json
{
  "analysis_id": "analysis-uuid",
  "user_id": "uuid",
  "photo_session_ids": ["session-1", "session-2"]  // Optional
}
```

**Response**:
```json
{
  "report_id": "report-uuid",
  "report_type": "comprehensive",
  "report_data": {
    "executive_summary": "Overall health assessment...",
    "health_timeline": [
      {
        "date": "2025-01-15",
        "event": "Reported severe headache",
        "category": "symptom",
        "severity": 8
      }
    ],
    "symptom_analysis": {
      "patterns": ["Recurring headaches correlate with stress"],
      "severity_trends": "improving",
      "correlations": ["Sleep quality affects symptom severity"]
    },
    "ai_insights": {
      "key_findings": ["Possible tension headaches", "Sleep hygiene important"],
      "risk_factors": ["Chronic stress", "Poor sleep"],
      "recommendations": ["Stress management", "Sleep study"]
    },
    "action_plan": {
      "immediate": ["Track sleep patterns", "Hydration monitoring"],
      "short_term": ["Stress reduction techniques", "Ergonomic assessment"],
      "long_term": ["Lifestyle modifications", "Regular check-ups"]
    }
  }
}
```

**Flow**:
1. Gather all health data for the user
2. Create comprehensive timeline of health events
3. Analyze patterns across all data types
4. Generate actionable recommendations
5. Store report with 1-year retention

---

## Specialist Reports

### 1. Basic Specialist Report
**Endpoint**: `POST /api/reports/specialist`

**Purpose**: Generate a report tailored for a specific medical specialty.

**Request**:
```json
{
  "analysis_id": "analysis-uuid",
  "user_id": "uuid",
  "specialty": "neurology",  // Optional, AI will suggest if not provided
  "quick_scan_ids": ["scan-1"],
  "deep_dive_ids": ["dive-1"],
  "photo_session_ids": ["photo-1"],
  "general_assessment_ids": ["assessment-1"],
  "general_deep_dive_ids": ["gen-dive-1"]
}
```

**Specialties Available**:
- cardiology
- neurology
- dermatology
- gastroenterology
- endocrinology
- psychiatry
- orthopedics
- rheumatology

**Response**:
```json
{
  "report_id": "specialist-report-uuid",
  "report_type": "specialist_neurology",
  "report_data": {
    "specialty": "neurology",
    "chief_complaints": ["Chronic headaches", "Memory issues"],
    "clinical_summary": "Patient presents with...",
    "relevant_findings": {
      "neurological": ["Tension-type headache pattern", "No red flags"],
      "imaging_needed": ["Consider MRI if symptoms persist"],
      "lab_suggestions": ["Vitamin D", "B12 levels"]
    },
    "differential_diagnosis": [
      {
        "condition": "Tension headaches",
        "likelihood": "high",
        "supporting_evidence": ["Bilateral pressure", "Stress correlation"]
      },
      {
        "condition": "Migraine",
        "likelihood": "moderate",
        "supporting_evidence": ["Duration >4 hours"]
      }
    ],
    "specialist_recommendations": {
      "immediate": ["Headache diary", "Trigger identification"],
      "diagnostic": ["Consider neurological exam"],
      "treatment": ["Stress management", "Physical therapy"],
      "follow_up": "4-6 weeks"
    },
    "red_flags": [],
    "icd_codes": ["G44.2 - Tension-type headache"],
    "referral_urgency": "routine"
  }
}
```

### 2. Cardiology Report
**Endpoint**: `POST /api/reports/specialist/cardiology`

**Purpose**: Specialized cardiovascular assessment.

**Additional Response Fields**:
```json
{
  "cardiovascular_risk": {
    "score": 12,
    "category": "moderate",
    "factors": ["Family history", "Sedentary lifestyle"]
  },
  "vital_signs_analysis": {
    "blood_pressure": "Borderline high",
    "heart_rate": "Normal",
    "trends": "Increasing BP trend"
  },
  "lifestyle_modifications": ["DASH diet", "150min exercise/week"]
}
```

### 3. Neurology Report
**Endpoint**: `POST /api/reports/specialist/neurology`

**Additional Features**:
- Headache pattern analysis
- Neurological symptom timeline
- Cognitive assessment suggestions
- Sleep impact evaluation

### 4. Dermatology Report
**Endpoint**: `POST /api/reports/specialist/dermatology`

**Special Integration**: Works with photo analysis data

**Additional Response Fields**:
```json
{
  "skin_assessment": {
    "conditions_identified": ["Atopic dermatitis", "Dry skin"],
    "photo_analysis": {
      "progression": "Improving with treatment",
      "visual_changes": ["Reduced redness", "Less scaling"]
    }
  },
  "treatment_plan": {
    "topical": ["Moisturizers", "Corticosteroids"],
    "systemic": [],
    "lifestyle": ["Avoid hot showers", "Fragrance-free products"]
  }
}
```

---

## Time-Based Reports

### 1. 30-Day Summary
**Endpoint**: `POST /api/reports/30-day-summary`

**Purpose**: Comprehensive overview of the last 30 days.

**Request**:
```json
{
  "user_id": "uuid",
  "include_wearables": true  // Optional
}
```

**Response**:
```json
{
  "report_id": "30day-uuid",
  "report_type": "30_day_summary",
  "report_data": {
    "period": {
      "start": "2024-12-15",
      "end": "2025-01-15"
    },
    "health_metrics": {
      "symptom_days": 12,
      "symptom_free_days": 18,
      "average_severity": 5.2,
      "trend": "improving"
    },
    "top_symptoms": [
      {
        "symptom": "headache",
        "frequency": 8,
        "average_severity": 6,
        "triggers": ["stress", "poor sleep"]
      }
    ],
    "health_events": [
      {
        "date": "2025-01-10",
        "type": "quick_scan",
        "summary": "Migraine assessment",
        "outcome": "Managed with rest"
      }
    ],
    "patterns_identified": [
      "Symptoms worse on weekdays",
      "Sleep quality affects next-day symptoms"
    ],
    "ai_insights": {
      "key_observations": ["Stress-related pattern", "Improving trend"],
      "recommendations": ["Maintain sleep schedule", "Stress management"],
      "achievements": ["50% reduction in severe symptoms"]
    }
  }
}
```

### 2. Annual Health Summary
**Endpoint**: `POST /api/reports/annual-summary`

**Purpose**: Year-long health trends and insights.

**Request**:
```json
{
  "analysis_id": "analysis-uuid",
  "user_id": "uuid",
  "year": 2024  // Optional, defaults to current year
}
```

**Response Structure**:
- Quarterly breakdowns
- Year-over-year comparisons
- Long-term pattern analysis
- Preventive care recommendations
- Health milestones achieved

---

## Urgent/Triage Reports

### 1. Urgent Triage Report
**Endpoint**: `POST /api/reports/urgent-triage`

**Purpose**: Rapid assessment for urgent symptoms.

**Request**:
```json
{
  "analysis_id": "analysis-uuid",
  "user_id": "uuid"
}
```

**Response**:
```json
{
  "report_id": "urgent-uuid",
  "report_type": "urgent_triage",
  "report_data": {
    "triage_level": "urgent",  // emergency|urgent|semi-urgent|non-urgent
    "red_flags_identified": [
      "Sudden severe headache",
      "Vision changes"
    ],
    "immediate_actions": [
      "Seek emergency care",
      "Do not drive yourself"
    ],
    "time_sensitive": true,
    "recommended_facility": "Emergency Department",
    "preparation": {
      "bring": ["Medication list", "Insurance card"],
      "document": ["Symptom timeline", "Recent changes"]
    },
    "warning_signs": [
      "Worsening symptoms",
      "New neurological symptoms"
    ]
  }
}
```

**Triage Algorithm**:
1. Scan for red flag symptoms
2. Assess severity and progression
3. Determine appropriate care level
4. Provide specific guidance

---

## Photo Analysis Reports

### 1. Photo Analysis Report
**Endpoint**: `POST /api/photo-analysis/reports/photo-analysis`

**Purpose**: Comprehensive report from photo tracking sessions.

**Request**:
```json
{
  "user_id": "uuid",
  "session_ids": ["session-1", "session-2"],
  "include_visual_timeline": true,
  "include_tracking_data": true,
  "time_range_days": 30  // Optional
}
```

**Response**:
```json
{
  "report_id": "photo-report-uuid",
  "report_type": "photo_analysis",
  "report_data": {
    "sessions": [...],
    "total_analyses": 5,
    "total_photos": 15,
    "date_range": {
      "start": "2024-12-01",
      "end": "2025-01-15"
    },
    "conditions_tracked": ["Mole on arm", "Eczema"],
    "analyses_timeline": [
      {
        "date": "2025-01-01",
        "primary_assessment": "Benign mole, stable",
        "confidence": 92,
        "key_observations": ["No size change", "Symmetric"],
        "recommendations": ["Continue monthly monitoring"]
      }
    ],
    "visual_progression": [
      {
        "date": "2025-01-01",
        "preview_url": "https://...",
        "category": "medical_normal",
        "assessment": "Stable appearance"
      }
    ],
    "ai_insights": {
      "overall_trend": "stable",
      "confidence": 0.88,
      "key_patterns": ["No concerning changes", "Consistent appearance"],
      "significant_changes": [],
      "tracking_recommendations": ["Continue monthly photos"],
      "medical_attention_indicators": ["Rapid size change", "Color variation"],
      "summary": "Monitored conditions remain stable with no concerning changes."
    }
  }
}
```

---

## Implementation Guide

### Frontend Integration Steps

#### 1. Initial Setup
```javascript
// Base configuration
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Common headers
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${userToken}` // If using auth
};
```

#### 2. Report Generation Flow
```javascript
// Step 1: Analyze available data
const analyzeReports = async (userId) => {
  const response = await fetch(`${API_BASE}/api/reports/analyze`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ user_id: userId })
  });
  return response.json();
};

// Step 2: Generate specific report
const generateReport = async (reportType, analysisId, userId) => {
  const endpoint = getReportEndpoint(reportType);
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ 
      analysis_id: analysisId,
      user_id: userId 
    })
  });
  return response.json();
};

// Step 3: Retrieve stored report
const getReport = async (reportId) => {
  const response = await fetch(`${API_BASE}/api/reports/${reportId}`, {
    headers
  });
  return response.json();
};
```

#### 3. Error Handling
```javascript
const generateReportWithErrorHandling = async (type, data) => {
  try {
    const response = await fetch(endpoint, options);
    
    if (!response.ok) {
      throw new Error(`Report generation failed: ${response.status}`);
    }
    
    const report = await response.json();
    
    // Handle partial failures
    if (report.status === 'partial') {
      console.warn('Report generated with warnings:', report.warnings);
    }
    
    return report;
  } catch (error) {
    // Handle network errors
    if (error.message.includes('fetch')) {
      throw new Error('Network error. Please check your connection.');
    }
    
    // Handle API errors
    throw error;
  }
};
```

#### 4. Report Display Components
```jsx
// Generic report viewer
const ReportViewer = ({ report }) => {
  const { report_type, report_data, generated_at } = report;
  
  return (
    <div className="report-container">
      <ReportHeader type={report_type} date={generated_at} />
      <ReportContent data={report_data} type={report_type} />
      <ReportActions reportId={report.report_id} />
    </div>
  );
};

// Specialized renderers for each report type
const renderReportContent = (data, type) => {
  switch(type) {
    case 'comprehensive':
      return <ComprehensiveReportView data={data} />;
    case 'specialist_cardiology':
      return <CardiologyReportView data={data} />;
    case 'urgent_triage':
      return <UrgentTriageView data={data} />;
    // ... other types
  }
};
```

### Best Practices

#### 1. Loading States
```javascript
const [loading, setLoading] = useState(false);
const [progress, setProgress] = useState(0);

const generateReportWithProgress = async () => {
  setLoading(true);
  setProgress(10); // Starting
  
  try {
    setProgress(30); // Data gathered
    const analysis = await analyzeReports(userId);
    
    setProgress(60); // Analysis complete
    const report = await generateReport(type, analysis.id, userId);
    
    setProgress(100); // Done
    return report;
  } finally {
    setLoading(false);
  }
};
```

#### 2. Caching Strategy
```javascript
// Cache reports locally
const reportCache = new Map();

const getCachedReport = async (reportId) => {
  // Check memory cache
  if (reportCache.has(reportId)) {
    return reportCache.get(reportId);
  }
  
  // Check localStorage for recent reports
  const cached = localStorage.getItem(`report_${reportId}`);
  if (cached) {
    const report = JSON.parse(cached);
    const age = Date.now() - new Date(report.generated_at).getTime();
    
    // Cache for 1 hour
    if (age < 3600000) {
      reportCache.set(reportId, report);
      return report;
    }
  }
  
  // Fetch fresh
  const report = await getReport(reportId);
  reportCache.set(reportId, report);
  localStorage.setItem(`report_${reportId}`, JSON.stringify(report));
  
  return report;
};
```

#### 3. Export Functionality
```javascript
const exportReport = async (reportId, format = 'pdf') => {
  const response = await fetch(
    `${API_BASE}/api/reports/${reportId}/export?format=${format}`,
    { headers }
  );
  
  if (!response.ok) throw new Error('Export failed');
  
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `health_report_${reportId}.${format}`;
  a.click();
  URL.revokeObjectURL(url);
};
```

### Common Patterns

#### 1. Report Type Selection
```javascript
const REPORT_TYPES = {
  COMPREHENSIVE: {
    id: 'comprehensive',
    name: 'Comprehensive Health Report',
    description: 'Complete overview of all health data',
    icon: 'clipboard-list',
    requiredData: ['any']
  },
  CARDIOLOGY: {
    id: 'specialist_cardiology',
    name: 'Cardiology Report',
    description: 'Heart and cardiovascular focused',
    icon: 'heart',
    requiredData: ['vitals', 'symptoms']
  },
  URGENT: {
    id: 'urgent_triage',
    name: 'Urgent Care Assessment',
    description: 'Immediate medical guidance',
    icon: 'ambulance',
    requiredData: ['symptoms']
  }
  // ... more types
};
```

#### 2. Data Validation
```javascript
const validateReportRequest = (type, userData) => {
  const reportConfig = REPORT_TYPES[type];
  
  if (!reportConfig) {
    throw new Error('Invalid report type');
  }
  
  // Check required data
  const hasRequiredData = reportConfig.requiredData.some(req => {
    switch(req) {
      case 'symptoms':
        return userData.quick_scans?.length > 0;
      case 'photos':
        return userData.photo_sessions?.length > 0;
      case 'vitals':
        return userData.wearable_data?.length > 0;
      case 'any':
        return true;
      default:
        return false;
    }
  });
  
  if (!hasRequiredData) {
    throw new Error(`Insufficient data for ${reportConfig.name}`);
  }
  
  return true;
};
```

### Troubleshooting

#### Common Issues:
1. **404 on report endpoints**: Ensure the server has been restarted after adding new routes
2. **Empty report data**: Check that the user has sufficient health data
3. **Timeout errors**: Large reports may take 30-60 seconds, increase client timeout
4. **Rate limiting**: Implement client-side throttling for report generation

#### Debug Mode:
```javascript
const DEBUG = process.env.NODE_ENV === 'development';

const debugLog = (stage, data) => {
  if (DEBUG) {
    console.log(`[Report Generation] ${stage}:`, data);
  }
};

// Use throughout the flow
debugLog('Analysis Started', { userId, reportType });
debugLog('Analysis Complete', { analysisId, suggestedReports });
debugLog('Report Generated', { reportId, dataPoints: report.report_data });
```

---

## API Rate Limits

- **Report Analysis**: 60 requests/minute per user
- **Report Generation**: 10 reports/minute per user
- **PDF Export**: 20 exports/hour per user

## Data Retention

- **Reports**: Stored for 1 year
- **Analysis Results**: Stored for 90 days
- **Temporary Data**: Cleaned after 24 hours

## Security Considerations

1. **Authentication**: All endpoints require valid user authentication
2. **Authorization**: Users can only access their own reports
3. **Data Sanitization**: All user inputs are validated and sanitized
4. **Encryption**: Reports containing sensitive data are encrypted at rest

---

This guide provides a complete foundation for integrating all report endpoints into your frontend application. Each report type is designed to provide maximum value while maintaining consistency in implementation patterns.