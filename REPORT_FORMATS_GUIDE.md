# 📊 Report Formats Comprehensive Guide

This guide documents all report endpoints, their request/response formats, data flow, and logging information.

## 🔍 Overview

The Health Oracle backend provides two main types of reports:
1. **General Reports** - Symptom timelines, comprehensive reports, photo progressions
2. **Specialist Reports** - 8 specialty-specific reports + primary care

All reports now support both body-specific and general assessments!

## 🛠️ Request Format Updates

### Base Request Fields (Common to All Reports)
```typescript
{
  "analysis_id": string,                    // Required: Report analysis ID
  "user_id": string | null,                 // Optional: User ID
  
  // Body-specific interactions
  "quick_scan_ids": string[] | null,        // IDs from quick_scans table
  "deep_dive_ids": string[] | null,         // IDs from deep_dive_sessions table
  
  // General assessments (NEW!)
  "general_assessment_ids": string[] | null, // IDs from general_assessments table
  "general_deep_dive_ids": string[] | null,  // IDs from general_deepdive_sessions table
  
  // Photo sessions
  "photo_session_ids": string[] | null       // IDs from photo_sessions table
}
```

## 📋 Report Endpoints & Formats

### 1. Symptom Timeline Report
**Endpoint:** `POST /api/report/symptom-timeline`

**Additional Request Fields:**
```typescript
{
  ...baseFields,
  "symptom_focus": string | null  // Optional: Specific symptom to focus on
}
```

**Response Format:**
```json
{
  "report_id": "uuid",
  "report_type": "symptom_timeline",
  "generated_at": "ISO timestamp",
  "status": "success",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Timeline overview of symptom progression",
      "chief_complaints": ["main symptoms tracked"],
      "key_findings": ["patterns discovered", "triggers identified"]
    },
    "symptom_progression": {
      "primary_symptom": "main symptom tracked",
      "timeline": [
        {
          "date": "YYYY-MM-DD",
          "severity": 1-10,
          "description": "detailed symptom description",
          "triggers_identified": ["potential triggers"],
          "treatments_tried": ["treatments used"],
          "effectiveness": "how well treatments worked"
        }
      ],
      "patterns_identified": {
        "frequency": "how often symptoms occur",
        "peak_times": ["when symptoms are worst"],
        "seasonal_trends": "seasonal patterns if any",
        "correlation_factors": ["correlated factors"]
      }
    },
    "trend_analysis": {
      "overall_direction": "improving/worsening/stable",
      "severity_trend": "severity changes over time",
      "frequency_trend": "frequency changes",
      "response_to_treatment": "treatment effectiveness"
    }
  }
}
```

### 2. Specialist Reports

All specialist reports follow a similar structure but with specialty-specific sections.

#### 2.1 Cardiology Report
**Endpoint:** `POST /api/report/cardiology`

**Response Format:**
```json
{
  "report_id": "uuid",
  "report_type": "cardiology",
  "generated_at": "ISO timestamp",
  "status": "success",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive cardiac assessment",
      "key_findings": ["significant cardiac findings"],
      "patterns_identified": ["temporal patterns", "triggers"],
      "chief_complaints": ["chest pain", "palpitations"],
      "action_items": ["immediate actions needed"],
      "specialist_focus": "cardiology",
      "target_audience": "cardiologist"
    },
    "clinical_summary": {
      "chief_complaint": "Primary cardiac concern",
      "hpi": "Detailed cardiac history",
      "symptom_timeline": [
        {
          "date": "ISO date",
          "symptoms": "specific cardiac symptoms",
          "severity": 1-10,
          "context": "what patient was doing",
          "duration": "how long it lasted",
          "resolution": "what helped"
        }
      ],
      "pattern_analysis": {
        "frequency": "symptom frequency",
        "triggers": ["identified triggers"],
        "alleviating_factors": ["what helps"],
        "progression": "changes over time"
      }
    },
    "cardiology_assessment": {
      "angina_classification": {
        "ccs_class": "I-IV",
        "typical_features": ["substernal", "exertional"],
        "atypical_features": ["unusual characteristics"]
      },
      "functional_capacity": {
        "current": "estimated METs",
        "baseline": "prior tolerance",
        "specific_limitations": ["cannot climb stairs"]
      },
      "risk_stratification": {
        "clinical_risk": "low/intermediate/high",
        "missing_data_for_scores": ["BP", "cholesterol"],
        "red_flags": ["concerning features"]
      }
    },
    "cardiologist_specific_findings": {
      "chest_pain_characterization": {
        "quality": "pressure/sharp/burning",
        "location": "specific location",
        "radiation": "if pain spreads",
        "associated_symptoms": ["dyspnea", "diaphoresis"]
      }
    },
    "diagnostic_priorities": {
      "immediate": [
        {
          "test": "ECG",
          "rationale": "baseline assessment",
          "timing": "same day"
        }
      ],
      "short_term": ["stress test", "labs"],
      "contingent": ["angiography if indicated"]
    },
    "treatment_recommendations": {
      "immediate_medical_therapy": [
        {
          "medication": "Aspirin 81mg",
          "rationale": "antiplatelet therapy"
        }
      ],
      "lifestyle_interventions": {
        "diet": "Mediterranean/DASH",
        "exercise": "cardiac rehab",
        "risk_factor_modification": ["smoking cessation"]
      }
    },
    "clinical_scales": {
      "CHA2DS2_VASc": {
        "calculated": "score 0-9",
        "confidence": 0.85,
        "confidence_level": "high",
        "reasoning": "Age 75+, hypertension confirmed",
        "breakdown": {
          "age": 2,
          "sex": 1,
          "chf": 0,
          "hypertension": 1,
          "stroke": 0,
          "vascular": 0,
          "diabetes": 0
        },
        "missing_data": ["diabetes status unclear"],
        "interpretation": "Moderate stroke risk",
        "annual_stroke_risk": "4.0%"
      },
      "NYHA_Classification": {
        "class": "II",
        "confidence": 0.9,
        "reasoning": "Symptoms with moderate exertion",
        "functional_description": "Comfortable at rest"
      }
    }
  }
}
```

#### 2.2 Neurology Report
**Endpoint:** `POST /api/report/neurology`

**Key Differences:**
- Focuses on neurological symptoms (headaches, dizziness, numbness)
- Includes headache classification per ICHD-3 criteria
- Red flag screening for serious pathology
- Clinical scales: MIDAS, HIT-6, cognitive screening

#### 2.3 Psychiatry Report
**Endpoint:** `POST /api/report/psychiatry`

**Key Differences:**
- Mental health assessment (mood, anxiety, psychosis)
- Risk assessment (suicide, violence, self-harm)
- Functional analysis (work, social, ADLs)
- Clinical scales: PHQ-9, GAD-7, Columbia Suicide Scale, MADRS

#### 2.4 Dermatology Report
**Endpoint:** `POST /api/report/dermatology`

**Key Differences:**
- Lesion characterization (morphology, distribution)
- Photo analysis integration
- Clinical scales: PASI, DLQI, IGA
- Treatment includes topical/systemic options

#### 2.5 Gastroenterology Report
**Endpoint:** `POST /api/report/gastroenterology`

**Key Differences:**
- GI symptom patterns (pain, bowel habits)
- Dietary analysis and triggers
- Clinical scales: Rome IV, Bristol Stool, IBS-SSS
- Alarm features screening

#### 2.6 Endocrinology Report
**Endpoint:** `POST /api/report/endocrinology`

**Key Differences:**
- Metabolic and hormonal assessment
- Clinical scales: FINDRISC, thyroid symptoms
- Focus on diabetes, thyroid, hormonal issues

#### 2.7 Pulmonology Report
**Endpoint:** `POST /api/report/pulmonology`

**Key Differences:**
- Respiratory symptom analysis
- Environmental factors assessment
- Clinical scales: mMRC, CAT, ACT, STOP-BANG
- Pulmonary function recommendations

#### 2.8 Primary Care Report
**Endpoint:** `POST /api/report/primary-care`

**Unique Structure:**
```json
{
  "report_data": {
    "clinical_summary": {
      "chief_complaints": ["main concerns"],
      "review_of_systems": {
        "constitutional": ["fatigue", "weight changes"],
        "cardiovascular": ["chest pain"],
        "respiratory": ["cough"],
        // ... all body systems
      }
    },
    "preventive_care_gaps": {
      "screening_due": ["colonoscopy", "mammogram"],
      "immunizations_needed": ["flu", "covid"],
      "health_maintenance": ["annual physical"]
    },
    "chronic_disease_assessment": {
      "identified_conditions": [
        {
          "condition": "hypertension",
          "control_status": "well-controlled",
          "management_gaps": ["home BP monitoring"]
        }
      ]
    },
    "specialist_coordination": {
      "current_specialists": ["cardiology"],
      "recommended_referrals": [
        {
          "specialty": "endocrinology",
          "reason": "diabetes management",
          "urgency": "routine"
        }
      ]
    }
  }
}
```

### 3. Generic Specialist Report
**Endpoint:** `POST /api/report/specialist`

**Additional Request Field:**
```typescript
{
  ...baseFields,
  "specialty": string | null  // Which specialty to focus on
}
```

## 🔄 Data Flow & Logging

### 1. Request Flow with Logging

When a report is requested, here's what happens:

```
1. ENDPOINT RECEIVES REQUEST
   LOG: "=== [REPORT_TYPE] REPORT START ==="
   LOG: All request parameters

2. LOAD ANALYSIS CONFIG
   LOG: "Report config loaded: {config}"

3. GATHER DATA (gather_selected_data or gather_report_data)
   LOG: "=== GATHER_SELECTED_DATA START ==="
   LOG: Each data type being fetched
   LOG: Count of records found
   LOG: "=== GATHER_SELECTED_DATA SUMMARY ==="

4. BUILD CONTEXT & CALL LLM
   LOG: "Calling LLM for analysis..."
   LOG: "LLM response received"
   LOG: "Report data extracted: true/false"

5. SAVE & RETURN REPORT
   LOG: "Report saved with ID: {id}"
   LOG: "=== [REPORT_TYPE] REPORT RESPONSE ==="
   LOG: Response summary
   LOG: "=== [REPORT_TYPE] REPORT END ==="
```

### 2. Data Gathering Details

**When specific IDs are provided:**
```javascript
// gather_selected_data is called
{
  quick_scans: [...],           // From quick_scans table
  deep_dives: [...],           // From deep_dive_sessions table
  general_assessments: [...],   // From general_assessments table
  general_deep_dives: [...],    // From general_deepdive_sessions table
  photo_analyses: [...],        // From photo_analyses table
  symptom_tracking: [...],      // Related symptom data
  llm_summaries: [...]         // Related chat summaries
}
```

**When NO specific IDs provided:**
```javascript
// gather_report_data is called
// Uses time range from report config
// Fetches all data within the specified time range
```

## 🎯 Clinical Scales in Reports

Each specialist report includes relevant clinical scales calculated automatically:

### Cardiology
- **CHA₂DS₂-VASc**: Stroke risk in atrial fibrillation
- **HAS-BLED**: Bleeding risk score
- **NYHA**: Heart failure functional class
- **CCS**: Angina grading

### Neurology
- **MIDAS**: Migraine disability assessment
- **HIT-6**: Headache impact test
- **ICHD-3**: Headache classification
- **Cognitive screening**: If cognitive complaints

### Psychiatry
- **PHQ-9**: Depression severity
- **GAD-7**: Anxiety severity
- **Columbia SSR**: Suicide risk
- **MADRS**: Depression rating scale

### Each Scale Includes:
```json
{
  "calculated": "numeric score",
  "confidence": 0.0-1.0,
  "confidence_level": "high/medium/low",
  "reasoning": "How score was calculated",
  "breakdown": { /* individual components */ },
  "missing_data": ["what would improve accuracy"],
  "interpretation": "Clinical meaning",
  "treatment_recommendation": "Based on score"
}
```

## 🚀 Frontend Integration Tips

### 1. Error Handling
```typescript
const response = await fetch('/api/report/cardiology', {
  method: 'POST',
  body: JSON.stringify(requestData)
});

if (response.status === "error") {
  // Handle error
  console.error(response.error);
}
```

### 2. Loading States
Track report generation progress using the logs:
- Request sent → "REPORT START"
- Gathering data → "GATHER_SELECTED_DATA"
- Processing → "Calling LLM"
- Complete → "REPORT END"

### 3. Data Selection
You can mix and match data sources:
```typescript
// Example: Cardiology report with mixed data
{
  "analysis_id": "abc-123",
  "quick_scan_ids": ["chest-scan-1"],      // Body-specific
  "general_assessment_ids": ["fatigue-1"], // General
  "photo_session_ids": ["ecg-photo-1"]     // Photos
}
```

### 4. Report Display
- Use the `executive_summary` for overview
- Show `clinical_scales` with confidence indicators
- Highlight `red_flags` or urgent findings
- Present `recommendations` as actionable items

## 📊 Logging Output Example

```
2024-01-20 10:30:15 INFO === CARDIOLOGY REPORT START ===
2024-01-20 10:30:15 INFO User ID: user-123
2024-01-20 10:30:15 INFO Quick scan IDs: ['scan-1', 'scan-2']
2024-01-20 10:30:15 INFO General assessment IDs: ['assess-1']
2024-01-20 10:30:15 INFO === GATHER_SELECTED_DATA START ===
2024-01-20 10:30:15 INFO Fetching 2 quick scans...
2024-01-20 10:30:15 INFO Found 2 quick scans
2024-01-20 10:30:15 INFO Fetching 1 general assessments...
2024-01-20 10:30:16 INFO Found 1 general assessments
2024-01-20 10:30:16 INFO === GATHER_SELECTED_DATA SUMMARY ===
2024-01-20 10:30:16 INFO Quick scans: 2
2024-01-20 10:30:16 INFO General assessments: 1
2024-01-20 10:30:16 INFO Calling LLM for analysis...
2024-01-20 10:30:18 INFO LLM response received
2024-01-20 10:30:18 INFO Report saved with ID: report-789
2024-01-20 10:30:18 INFO === CARDIOLOGY REPORT END ===
```

## 🔧 Troubleshooting

### Common Issues:
1. **Empty report_data**: Check if LLM response parsing failed (see logs)
2. **Missing clinical scales**: Ensure sufficient data provided for calculation
3. **Low confidence scores**: More data needed for accurate assessment

### Debug Tips:
- Enable DEBUG logging for detailed traces
- Check `gather_selected_data` summary for data counts
- Verify all required IDs exist and belong to the user
- Monitor LLM response extraction success

## 📝 Notes

- All timestamps are in UTC ISO format
- Confidence scores range from 0.0 to 1.0
- Clinical scales include reasoning for transparency
- Reports support both anonymous and authenticated users
- Data is filtered by user_id for security