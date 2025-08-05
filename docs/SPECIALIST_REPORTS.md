# Specialist Reports Implementation Guide

## Overview
The specialist reports system generates comprehensive medical reports tailored for specific medical specialties. It intelligently handles both complete and incomplete assessment data, ensuring valuable partial data is not lost.

## Architecture Flow

```
User Request → Report Analysis → Data Gathering → Report Generation → Storage
     ↓              ↓                  ↓                ↓              ↓
  Select IDs   Triage/Config    Fetch Sessions    LLM Process    Database
                               (Any Status)      (Handle Partial)
```

### Detailed Process Flow

1. **User Request Phase**
   - Frontend sends assessment IDs (quick scans, deep dives, etc.)
   - Can be specific IDs or time-range based
   - Includes user_id and analysis_id

2. **Report Analysis Phase**
   - Load analysis configuration from database
   - Determine report type and specialty
   - Validate user permissions

3. **Data Gathering Phase**
   - `gather_selected_data()` for specific IDs
   - `gather_comprehensive_data()` for time ranges
   - Fetches ALL non-abandoned sessions
   - Includes medical profile, demographics

4. **Report Generation Phase**
   - Process session status indicators
   - Build context with partial data handling
   - LLM generates specialist-specific report
   - Calculate clinical scores when applicable

5. **Storage Phase**
   - Save to `medical_reports` table
   - Link to original analysis
   - Track confidence and model used

## Session Status Handling

### Deep Dive & General Deep Dive Sessions

| Status | Included | Description | Handling |
|--------|----------|-------------|----------|
| `completed` | ✅ | Full analysis with final confidence | Use all data including final_analysis |
| `analysis_ready` | ✅ | Initial analysis done, Ask Me More available | Use initial analysis, flag for follow-up |
| `active` | ✅ | Assessment in progress | Use questions array, add "Continue Assessment" action |
| `abandoned` | ❌ | User stopped responding | Exclude from reports |

### Key Principles
- **No Artificial Completeness Scoring**: Deep dives ask questions until reaching confidence naturally
- **Dynamic Question Count**: 2 questions might suffice for simple cases, 6+ for complex ones
- **Trust the System**: The deep dive manages its own confidence mechanism

## Data Gathering Functions

### `gather_selected_data()`
Fetches specific sessions by ID, regardless of completion status:
```python
# Includes all non-abandoned sessions
.in_("status", ["active", "analysis_ready", "completed"])
```

### `gather_comprehensive_data()`
Time-based data fetching for comprehensive reports:
```python
# Deep Dives - Include all non-abandoned sessions
dives = supabase.table("deep_dive_sessions")\
    .select("*")\
    .eq("user_id", user_id)\
    .in_("status", ["active", "analysis_ready", "completed"])\
    .gte("created_at", time_range["start"])\
    .lte("created_at", time_range["end"])\
    .execute()
```

## API Structure Overview

### How The System Works

1. **Client initiates report request** → Sends selected assessment IDs
2. **Backend validates and loads data** → Fetches all relevant sessions
3. **Process session status** → Includes partial data with indicators  
4. **Generate specialist-specific report** → LLM analyzes with medical context
5. **Return structured JSON** → Frontend displays formatted report

### Base Request Structure

All specialist report endpoints accept the same request structure:

```typescript
interface SpecialistReportRequest {
  analysis_id: string;           // Required: Links to report analysis
  user_id?: string;              // Optional: Falls back to analysis user_id
  quick_scan_ids?: string[];     // Body-specific quick scans
  deep_dive_ids?: string[];      // Body-specific deep dive sessions
  general_assessment_ids?: string[];    // General health assessments
  general_deep_dive_ids?: string[];     // General deep dive sessions
  photo_session_ids?: string[];         // Photo analysis sessions
}
```

### Base Response Structure

All endpoints return a consistent response format:

```typescript
interface SpecialistReportResponse {
  report_id: string;              // Unique report identifier
  specialty: string;              // Medical specialty
  status: "success" | "error";    
  report_data: {
    executive_summary: {
      one_page_summary: string;
      key_findings: string[];
      patterns_identified: string[];
      chief_complaints: string[];
      action_items: string[];
      specialist_focus: string;
      target_audience: string;
    };
    clinical_summary: {
      chief_complaint: string;
      hpi: string;              // History of present illness
      symptom_timeline: Array<{
        date: string;
        symptoms: string;
        severity: number;
        context: string;
        duration: string;
        resolution: string;
      }>;
      pattern_analysis: {
        frequency: string;
        triggers: string[];
        alleviating_factors: string[];
        progression: string;
      };
    };
    [specialty]_assessment: object;  // Specialty-specific section
    diagnostic_priorities: {
      immediate: string[];
      short_term: string[];
      long_term: string[];
    };
    treatment_recommendations: {
      lifestyle: string[];
      medical: string[];
      follow_up: string[];
    };
    follow_up_plan: {
      timeline: string;
      next_steps: string[];
      monitoring: string[];
    };
    data_completeness?: {
      complete_sessions: number;
      in_progress_sessions: number;
      data_quality: "excellent" | "good" | "fair" | "limited";
    };
  };
  confidence_score: number;      // 0-100
  model_used: string;
  created_at: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}
```

## Available Specialist Reports

### 1. Specialty Triage (`/api/report/specialty-triage`)

**Purpose**: Analyzes symptoms to recommend appropriate specialist(s)

**Request:**
```json
POST /api/report/specialty-triage
{
  "quick_scan_ids": ["uuid1", "uuid2"],
  "deep_dive_ids": ["uuid3"],
  "user_id": "user_uuid"
}
```

**Response:**
```json
{
  "primary_specialty": "cardiology",
  "confidence": 0.85,
  "reasoning": "Patient presents with chest pain, shortness of breath, and palpitations consistent with cardiac etiology",
  "secondary_specialties": [
    {
      "specialty": "pulmonology",
      "confidence": 0.45,
      "reason": "Dyspnea could have pulmonary component"
    }
  ],
  "urgency": "urgent",
  "red_flags": ["chest pain with exertion", "new onset symptoms"],
  "recommended_report_type": "cardiology",
  "triage_notes": "Recommend cardiac workup with ECG and troponins"
}
```

### 2. General Specialist Report (`/api/report/specialist`)

**Purpose**: Flexible report that adapts to any specialty based on triage

**Request:**
```json
POST /api/report/specialist
{
  "analysis_id": "analysis_uuid",
  "user_id": "user_uuid",
  "quick_scan_ids": ["scan1"],
  "deep_dive_ids": ["dive1"]
}
```

**Response:** Same structure as base response, with specialty-specific assessment section

---

### 3. Cardiology Report (`/api/report/cardiology`)

**Purpose**: Comprehensive cardiac assessment with risk scoring

**Unique Features:**
- CHA₂DS₂-VASc score (AFib stroke risk)
- HAS-BLED score (bleeding risk)
- NYHA Functional Classification
- CCS Angina Grade
- METs estimation

**Request:**
```json
POST /api/report/cardiology
{
  "analysis_id": "analysis_uuid",
  "user_id": "user_uuid",
  "quick_scan_ids": ["chest_pain_scan"],
  "deep_dive_ids": ["cardiac_dive"],
  "general_assessment_ids": ["general1"]
}
```

**Specialty-Specific Response Section:**
```json
{
  "cardiology_assessment": {
    "angina_classification": {
      "ccs_class": "II",
      "typical_features": ["substernal", "exertional", "relieved by rest"],
      "atypical_features": ["sharp quality"]
    },
    "functional_capacity": {
      "current": "4-6 METs",
      "baseline": "8-10 METs",
      "specific_limitations": ["stops after 2 blocks", "cannot climb 2 flights"]
    },
    "risk_stratification": {
      "clinical_risk": "intermediate",
      "missing_data_for_scores": ["BP", "cholesterol"],
      "red_flags": ["new onset", "progressive symptoms"]
    },
    "calculated_scores": {
      "cha2ds2_vasc": {
        "score": 3,
        "confidence": 0.8,
        "components": {
          "age": 1,
          "sex": 0,
          "chf": 1,
          "hypertension": 1,
          "stroke": 0,
          "vascular": 0,
          "diabetes": 0
        },
        "reasoning": "Age 72, history of CHF, hypertension documented"
      }
    }
  }
}
```

### 4. Neurology Report (`/api/report/neurology`)

**Purpose**: Neurological assessment with stroke and headache focus

**Unique Features:**
- NIH Stroke Scale components
- Modified Rankin Scale
- ABCD² Score (TIA risk)
- Migraine pattern analysis
- Neurological deficit mapping

**Specialty-Specific Response Section:**
```json
{
  "neurology_assessment": {
    "neurological_deficits": ["mild left facial droop", "word-finding difficulty"],
    "headache_pattern": {
      "type": "migraine with aura",
      "frequency": "2-3 per month",
      "triggers": ["stress", "lack of sleep"]
    },
    "calculated_scores": {
      "abcd2": {
        "score": 4,
        "risk_category": "moderate",
        "components": {"age": 1, "bp": 1, "clinical": 2, "duration": 0, "diabetes": 0}
      }
    }
  }
}
```

---

### 5. Psychiatry Report (`/api/report/psychiatry`)

**Purpose**: Mental health assessment with mood and anxiety screening

**Unique Features:**
- PHQ-9 Depression screening
- GAD-7 Anxiety assessment
- CAGE questionnaire (alcohol)
- Suicide risk assessment
- Mood episode tracking

**Specialty-Specific Response Section:**
```json
{
  "psychiatry_assessment": {
    "mood_assessment": {
      "primary_concern": "major depressive episode",
      "duration": "3 months",
      "severity": "moderate"
    },
    "calculated_scores": {
      "phq9": {
        "score": 14,
        "severity": "moderate depression",
        "confidence": 0.9,
        "suicidal_ideation": false
      },
      "gad7": {
        "score": 8,
        "severity": "mild anxiety",
        "confidence": 0.85
      }
    },
    "risk_assessment": {
      "suicide_risk": "low",
      "self_harm_risk": "low",
      "violence_risk": "minimal"
    }
  }
}
```

---

### 6. Dermatology Report (`/api/report/dermatology`)

**Purpose**: Skin condition analysis with photo comparison

**Unique Features:**
- ABCDE melanoma criteria
- PASI score (psoriasis)
- Lesion progression tracking
- Photo comparison analysis
- Distribution pattern mapping

**Specialty-Specific Response Section:**
```json
{
  "dermatology_assessment": {
    "lesion_analysis": {
      "primary_morphology": "papulosquamous",
      "distribution": "symmetric, extensor surfaces",
      "evolution": "progressive over 2 months"
    },
    "photo_progression": {
      "change_detected": true,
      "size_change": "+15%",
      "color_change": "darkening centrally"
    },
    "abcde_criteria": {
      "asymmetry": false,
      "border": "regular",
      "color": "uniform",
      "diameter": "4mm",
      "evolving": true
    }
  }
}
```

---

### 7. Gastroenterology Report (`/api/report/gastroenterology`)

**Purpose**: GI symptom analysis with functional disorder assessment

**Unique Features:**
- Rome IV criteria
- Bristol Stool Chart
- GERD symptom scoring
- Alarm symptoms identification
- Dietary trigger analysis

**Specialty-Specific Response Section:**
```json
{
  "gastroenterology_assessment": {
    "primary_gi_concern": "IBS-D by Rome IV criteria",
    "alarm_symptoms": [],
    "bristol_stool_type": "Type 6-7",
    "gerd_assessment": {
      "frequency": "daily",
      "severity": "moderate",
      "ppi_response": "partial"
    },
    "dietary_triggers": ["dairy", "high FODMAP foods"]
  }
}
```

---

### 8. Endocrinology Report (`/api/report/endocrinology`)

**Purpose**: Metabolic and hormonal disorder assessment

**Unique Features:**
- Diabetes risk scoring
- Thyroid symptom analysis
- Metabolic syndrome criteria
- Hormonal pattern analysis
- Weight trend evaluation

**Specialty-Specific Response Section:**
```json
{
  "endocrinology_assessment": {
    "metabolic_status": {
      "diabetes_risk": "high",
      "metabolic_syndrome_criteria": 3,
      "insulin_resistance_markers": ["acanthosis nigricans", "central obesity"]
    },
    "thyroid_assessment": {
      "clinical_score": 6,
      "symptoms": ["fatigue", "cold intolerance", "weight gain"],
      "risk": "hypothyroidism likely"
    }
  }
}
```

---

### 9. Pulmonology Report (`/api/report/pulmonology`)

**Purpose**: Respiratory assessment with functional evaluation

**Unique Features:**
- mMRC Dyspnea Scale
- CAT Score (COPD)
- Asthma control assessment
- Sleep apnea risk (STOP-BANG)
- Cough characterization

**Specialty-Specific Response Section:**
```json
{
  "pulmonology_assessment": {
    "dyspnea_assessment": {
      "mmrc_grade": 2,
      "functional_impact": "moderate limitation"
    },
    "cough_characterization": {
      "duration": "chronic",
      "quality": "productive",
      "timing": "morning predominant"
    },
    "calculated_scores": {
      "cat_score": 18,
      "asthma_control": "partly controlled"
    }
  }
}
```

---

### 10. Primary Care Report (`/api/report/primary-care`)

**Purpose**: Comprehensive overview for primary care management

**Unique Features:**
- Multi-system review
- Preventive care gaps
- Vaccination status
- Cancer screening needs
- Social determinants

**Specialty-Specific Response Section:**
```json
{
  "primary_care_assessment": {
    "systems_affected": ["cardiovascular", "endocrine"],
    "preventive_gaps": ["colonoscopy overdue", "mammogram due"],
    "medication_concerns": ["potential interaction between X and Y"],
    "social_determinants": {
      "housing": "stable",
      "food_security": "adequate",
      "transportation": "limited"
    }
  }
}
```

---

### 11. Orthopedics Report (`/api/report/orthopedics`)

**Purpose**: Musculoskeletal assessment with functional scoring

**Unique Features:**
- Pain scale assessments
- Functional limitation scoring
- Range of motion estimates
- Activity modification tracking
- Injury mechanism analysis

**Specialty-Specific Response Section:**
```json
{
  "orthopedics_assessment": {
    "joint_assessment": {
      "affected_joints": ["right knee", "left hip"],
      "pain_characteristics": "mechanical, worse with activity",
      "functional_score": 45
    },
    "range_of_motion": {
      "right_knee": "flexion 90°, extension -10°",
      "limitations": "significant"
    },
    "activity_impact": {
      "work": "modified duties",
      "adl": "difficulty with stairs",
      "sports": "unable"
    }
  }
}
```

---

### 12. Rheumatology Report (`/api/report/rheumatology`)

**Purpose**: Inflammatory arthritis and autoimmune assessment

**Unique Features:**
- DAS28 calculation
- HAQ-DI estimation
- Morning stiffness duration
- Joint count (tender/swollen)
- Inflammatory markers

**Specialty-Specific Response Section:**
```json
{
  "rheumatology_assessment": {
    "inflammatory_markers": {
      "morning_stiffness": "45 minutes",
      "joint_pattern": "symmetric polyarthritis",
      "systemic_features": ["fatigue", "low-grade fever"]
    },
    "calculated_scores": {
      "das28": {
        "score": 4.2,
        "activity": "moderate",
        "tender_joints": 8,
        "swollen_joints": 5
      }
    }
  }
}
```

## Handling Incomplete Data

### Visual Indicators
```javascript
status_indicators = {
  "active": "🔄 Assessment in Progress",
  "analysis_ready": "✅ Analysis Ready",
  "completed": "✅ Completed",
  "abandoned": "❌ Abandoned"
}
```

### Context Enhancement for Partial Data
When a session is active without final_analysis:
1. Extract data from questions array
2. Add status indicator: "🔄 Assessment in Progress"
3. Include note: "Using partial data from ongoing assessment"
4. Add action item: "Continue Assessment"

### Example Report Context with Mixed Sessions
```
PRIMARY INTERACTIONS:
- Deep Dives: 3
  Session Status Summary:
  [
    {
      "id": "uuid1",
      "date": "2025-01-20",
      "status": "✅ Completed",
      "questions_answered": 6,
      "confidence": "85%"
    },
    {
      "id": "uuid2",
      "date": "2025-01-21",
      "status": "🔄 Assessment in Progress",
      "questions_answered": 3,
      "note": "Using partial data from ongoing assessment",
      "action_needed": "Continue Assessment"
    },
    {
      "id": "uuid3",
      "date": "2025-01-22",
      "status": "✅ Analysis Ready",
      "questions_answered": 5,
      "confidence": "78%",
      "note": "Initial analysis complete, additional questions available"
    }
  ]
```

## Complete API Examples

### Example 1: Cardiology Report with Mixed Session Status

**Request:**
```json
POST /api/report/cardiology
{
  "analysis_id": "abc123-def456",
  "user_id": "user-789",
  "quick_scan_ids": ["scan-001", "scan-002"],
  "deep_dive_ids": ["dive-001", "dive-002"],  // dive-001 is complete, dive-002 is active
  "general_assessment_ids": ["general-001"]
}
```

**Response:**
```json
{
  "report_id": "report-xyz-789",
  "specialty": "cardiology",
  "status": "success",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "68-year-old male with progressive exertional chest pain...",
      "key_findings": [
        "Typical angina pattern with CCS Class II symptoms",
        "Cardiovascular risk factors: hypertension, dyslipidemia",
        "One assessment still in progress - partial data included"
      ],
      "patterns_identified": [
        "Symptoms worse in morning",
        "Cold weather trigger identified"
      ],
      "chief_complaints": ["chest pressure", "dyspnea on exertion"],
      "action_items": [
        "Urgent: Cardiac stress test recommended",
        "Continue incomplete deep dive assessment",
        "Initiate antiplatelet therapy"
      ],
      "specialist_focus": "cardiology",
      "target_audience": "cardiologist"
    },
    "clinical_summary": {
      "chief_complaint": "Chest pressure with exertion for 3 weeks",
      "hpi": "Patient reports substernal chest pressure...",
      "symptom_timeline": [
        {
          "date": "2025-01-01",
          "symptoms": "chest pressure",
          "severity": 6,
          "context": "walking uphill",
          "duration": "5 minutes",
          "resolution": "rest"
        }
      ],
      "pattern_analysis": {
        "frequency": "daily with exertion",
        "triggers": ["exertion", "cold weather", "stress"],
        "alleviating_factors": ["rest", "nitroglycerin"],
        "progression": "worsening over 3 weeks"
      }
    },
    "cardiology_assessment": {
      "angina_classification": {
        "ccs_class": "II",
        "typical_features": ["substernal", "exertional", "relieved by rest"],
        "atypical_features": []
      },
      "functional_capacity": {
        "current": "4-6 METs",
        "baseline": "8-10 METs",
        "specific_limitations": ["stops after 2 blocks"]
      },
      "risk_stratification": {
        "clinical_risk": "intermediate-high",
        "missing_data_for_scores": ["LDL cholesterol", "A1c"],
        "red_flags": ["progressive symptoms", "new onset"]
      },
      "calculated_scores": {
        "cha2ds2_vasc": {
          "score": 3,
          "confidence": 0.85,
          "components": {
            "congestive_heart_failure": 0,
            "hypertension": 1,
            "age_75": 0,
            "diabetes": 0,
            "stroke": 0,
            "vascular_disease": 1,
            "age_65_74": 1,
            "sex_female": 0
          },
          "reasoning": "Age 68 (1 point), HTN documented (1 point), possible vascular disease (1 point)"
        }
      }
    },
    "diagnostic_priorities": {
      "immediate": ["ECG", "Troponin", "Stress test"],
      "short_term": ["Echo", "Coronary CTA"],
      "long_term": ["Lipid optimization", "Risk factor modification"]
    },
    "treatment_recommendations": {
      "lifestyle": ["Cardiac rehabilitation", "Low sodium diet"],
      "medical": ["Aspirin 81mg daily", "Statin therapy", "Beta blocker"],
      "follow_up": ["Cardiology within 1 week"]
    },
    "follow_up_plan": {
      "timeline": "1 week",
      "next_steps": ["Complete stress test", "Finish incomplete deep dive"],
      "monitoring": ["Daily symptom diary", "BP monitoring"]
    },
    "data_completeness": {
      "complete_sessions": 3,
      "in_progress_sessions": 1,
      "data_quality": "good",
      "note": "One deep dive assessment in progress - partial data included"
    }
  },
  "confidence_score": 82,
  "model_used": "deepseek/deepseek-chat",
  "created_at": "2025-01-22T10:30:00Z",
  "usage": {
    "prompt_tokens": 2456,
    "completion_tokens": 1823,
    "total_tokens": 4279
  }
}
```

### Example 2: Neurology Report - Headache Focus

**Request:**
```json
POST /api/report/neurology
{
  "analysis_id": "neuro-analysis-456",
  "user_id": "user-321",
  "quick_scan_ids": ["headache-scan-001"],
  "deep_dive_ids": ["migraine-dive-001"]
}
```

**Response:**
```json
{
  "report_id": "neuro-report-999",
  "specialty": "neurology",
  "status": "success",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "32-year-old female with chronic migraine with aura...",
      "key_findings": [
        "Migraine with visual aura meeting ICHD-3 criteria",
        "Frequency increasing to 8-10 per month",
        "Significant functional impairment"
      ],
      "action_items": [
        "Initiate migraine prophylaxis",
        "MRI brain to rule out secondary causes",
        "Headache diary for trigger identification"
      ]
    },
    "neurology_assessment": {
      "headache_pattern": {
        "type": "migraine with aura",
        "frequency": "8-10 per month",
        "duration": "4-72 hours",
        "triggers": ["stress", "menses", "weather changes"],
        "aura_characteristics": ["visual scotoma", "fortification spectra"]
      },
      "neurological_exam": {
        "deficits": [],
        "red_flags_absent": true
      },
      "disability_assessment": {
        "midas_score": 18,
        "category": "severe disability"
      }
    }
  }
}
```

## Best Practices

### 1. Data Inclusion
- Always include non-abandoned sessions
- Use partial data from active sessions
- Clearly indicate session status

### 2. Confidence Handling
- Don't artificially reduce confidence for incomplete sessions
- Trust the deep dive's own confidence mechanism
- Report the actual confidence from the assessment

### 3. Action Items
- Add "Continue Assessment" for active sessions
- Include "Schedule Follow-up" for complex cases
- Suggest "Complete Deep Dive" when more data would help

### 4. Report Quality
- Prioritize selected interactions over supplementary data
- Use medical profile for context
- Include relevant clinical scales
- Document assumptions clearly

## Database Schema Requirements

### Required Tables
- `deep_dive_sessions` - Body-specific deep dives
- `general_deepdive_sessions` - General health deep dives
- `quick_scans` - Rapid assessments
- `general_assessments` - General health quick assessments
- `photo_analyses` - Photo-based assessments
- `medical` - Patient demographics and history
- `medical_reports` - Generated reports storage
- `report_analyses` - Report configuration

### Status Constraints
```sql
CHECK (status IN ('active', 'analysis_ready', 'completed', 'abandoned'))
```

## Error Handling

### Common Issues and Solutions

1. **Missing final_analysis**
   - Use questions array data
   - Flag as in-progress
   - Don't skip the session

2. **Empty questions array**
   - Check for form_data
   - Use initial complaint
   - Mark as "Data Limited"

3. **Mixed session types**
   - Process each type separately
   - Combine insights coherently
   - Maintain type indicators

## Testing Scenarios

### Scenario 1: All Complete Sessions
- Expected: Full analysis with high confidence
- Action items: Routine follow-up

### Scenario 2: Mixed Complete and Active
- Expected: Comprehensive analysis with partial data noted
- Action items: Continue active assessments

### Scenario 3: Only Active Sessions
- Expected: Preliminary analysis based on available data
- Action items: Complete assessments for full evaluation

## Future Enhancements

1. **Auto-continuation**: Prompt users to complete active sessions
2. **Confidence Weighting**: Adjust report sections based on data completeness
3. **Progressive Reports**: Update automatically as sessions complete
4. **Smart Triage**: Prioritize completion based on symptom severity
5. **Integration Points**: Connect with scheduling for follow-ups

## Configuration

### Environment Variables
```bash
# Models for report generation
REPORT_MODEL="deepseek/deepseek-chat"
REPORT_FALLBACK_MODEL="google/gemini-2.5-pro"
```

### Report Generation Settings
```python
REPORT_CONFIG = {
    "include_incomplete": True,  # Include active sessions
    "min_confidence": 60,        # Minimum confidence to include
    "max_tokens": 4096,          # LLM response limit
    "temperature": 0.3           # Lower for consistency
}
```

## Monitoring and Analytics

### Key Metrics
- Reports with incomplete data: Track percentage
- Average sessions per report: Monitor completeness
- Action item completion rate: User engagement
- Report accuracy feedback: Quality assurance

### Logging
```python
logger.info(f"Report generated with {complete_count} complete and {active_count} active sessions")
```

---

Last Updated: 2025-01-22
Version: 1.0.0