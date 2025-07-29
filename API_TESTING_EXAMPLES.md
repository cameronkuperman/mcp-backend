# API Testing Examples for Enhanced Specialist Reports

Base URL: `https://web-production-945c4.up.railway.app`

## 1. Specialty Triage Endpoint

```bash
# Get AI recommendation for which specialist to see
curl -X POST https://web-production-945c4.up.railway.app/api/report/specialty-triage \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-user-id",
    "primary_concern": "I have been having chest pain when I walk up stairs",
    "symptoms": ["chest pain", "shortness of breath", "fatigue"]
  }'
```

## 2. Generate Specialist Reports

### Cardiology Report
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/report/cardiology \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-user-id",
    "analysis_id": "your-analysis-id"
  }'
```

### Neurology Report
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/report/neurology \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-user-id",
    "analysis_id": "your-analysis-id"
  }'
```

### Psychiatry Report
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/report/psychiatry \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-user-id",
    "analysis_id": "your-analysis-id"
  }'
```

### Dermatology Report
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/report/dermatology \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-user-id",
    "analysis_id": "your-analysis-id"
  }'
```

### Gastroenterology Report
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/report/gastroenterology \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-user-id",
    "analysis_id": "your-analysis-id"
  }'
```

### Endocrinology Report
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/report/endocrinology \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-user-id",
    "analysis_id": "your-analysis-id"
  }'
```

### Pulmonology Report
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/report/pulmonology \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-user-id",
    "analysis_id": "your-analysis-id"
  }'
```

### Primary Care Report (NEW)
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/report/primary-care \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-user-id",
    "analysis_id": "your-analysis-id"
  }'
```

## 3. Example Responses

### Specialty Triage Response
```json
{
  "status": "success",
  "triage_result": {
    "primary_specialty": "cardiology",
    "confidence": 0.85,
    "reasoning": "Exertional chest pain with dyspnea suggests cardiac evaluation needed",
    "secondary_specialties": [
      {
        "specialty": "pulmonology",
        "confidence": 0.45,
        "reason": "Shortness of breath could indicate pulmonary involvement"
      }
    ],
    "urgency": "urgent",
    "red_flags": ["Progressive exertional symptoms", "New onset chest pain"],
    "recommended_timing": "Cardiology evaluation within 1-2 weeks"
  },
  "generated_at": "2025-01-29T..."
}
```

### Cardiology Report Response (Enhanced)
```json
{
  "report_id": "uuid",
  "report_type": "cardiology",
  "generated_at": "2025-01-29T...",
  "status": "success",
  "report_data": {
    "clinical_summary": {
      "chief_complaint": "Chest pain with exertion",
      "hpi": "45-year-old male presents with 3-month history of substernal chest pressure...",
      "symptom_timeline": [
        {
          "date": "2024-10-15",
          "symptoms": "Chest pressure walking uphill",
          "severity": 6,
          "context": "Cold morning walk to work",
          "duration": "5-10 minutes",
          "resolution": "Rest"
        }
      ],
      "pattern_analysis": {
        "frequency": "Daily with exertion",
        "triggers": ["Walking uphill", "Climbing stairs", "Cold weather"],
        "alleviating_factors": ["Rest within 5-10 minutes"],
        "progression": "Worsening - now occurs with less exertion"
      }
    },
    "cardiology_assessment": {
      "angina_classification": {
        "ccs_class": "II-III",
        "typical_features": ["Substernal location", "Exertional", "Relieved by rest"],
        "atypical_features": ["No radiation to arm"]
      },
      "functional_capacity": {
        "current": "3-4 METs",
        "baseline": "8-10 METs (regular runner 6 months ago)",
        "specific_limitations": ["Cannot climb 1 flight without stopping"]
      },
      "risk_stratification": {
        "clinical_risk": "Intermediate-High",
        "missing_data_for_scores": ["Blood pressure", "Cholesterol levels", "Family history"],
        "red_flags": ["Progressive symptoms", "Decreasing exercise tolerance"]
      }
    },
    "diagnostic_priorities": {
      "immediate": [
        {
          "test": "12-lead ECG",
          "rationale": "Baseline assessment and check for ischemic changes",
          "timing": "Same day"
        }
      ],
      "short_term": [
        {
          "test": "Exercise stress test",
          "rationale": "Assess for inducible ischemia",
          "timing": "Within 1 week"
        },
        {
          "test": "Lipid panel, HbA1c",
          "rationale": "Risk stratification",
          "timing": "With stress test"
        }
      ]
    },
    "treatment_recommendations": {
      "immediate_medical_therapy": [
        {
          "medication": "Aspirin 81mg daily",
          "rationale": "Antiplatelet therapy for suspected CAD"
        },
        {
          "medication": "Atorvastatin 40mg daily",
          "rationale": "High-intensity statin for ASCVD risk reduction"
        }
      ],
      "lifestyle_interventions": {
        "diet": "Mediterranean diet for cardiovascular health",
        "exercise": "Cardiac rehabilitation after evaluation",
        "risk_factor_modification": ["Stress reduction techniques"]
      }
    },
    "care_coordination": {
      "referral_urgency": "urgent",
      "follow_up_plan": {
        "cardiology": "Within 2 weeks",
        "primary_care": "After cardiac workup",
        "emergency_plan": "Call 911 for rest pain or prolonged symptoms"
      }
    }
  }
}
```

## 4. Testing Different Scenarios

### Test 1: Headache Patient (Should recommend Neurology)
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/report/specialty-triage \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-1",
    "primary_concern": "Severe headaches that are getting worse",
    "symptoms": ["headache", "nausea", "light sensitivity", "vision changes"]
  }'
```

### Test 2: Skin Rash (Should recommend Dermatology)
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/report/specialty-triage \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-2",
    "primary_concern": "Red scaly patches on my elbows and knees",
    "symptoms": ["rash", "itching", "scaling skin", "joint pain"]
  }'
```

### Test 3: Mental Health (Should recommend Psychiatry)
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/report/specialty-triage \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-3",
    "primary_concern": "Feeling depressed and anxious for months",
    "symptoms": ["depression", "anxiety", "insomnia", "fatigue"]
  }'
```

## 5. Using with Authorization (if implemented)

```bash
# With Bearer token
curl -X POST https://web-production-945c4.up.railway.app/api/report/cardiology \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -d '{
    "user_id": "your-user-id",
    "analysis_id": "your-analysis-id"
  }'
```

## 6. Error Handling Examples

### Missing Required Fields
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/report/specialty-triage \
  -H "Content-Type: application/json" \
  -d '{}'

# Expected: 422 Validation Error
```

### Invalid Analysis ID
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/report/cardiology \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "analysis_id": "invalid-uuid"
  }'

# Expected: {"error": "Analysis not found", "status": "error"}
```

## 7. Testing with HTTPie (Alternative to curl)

```bash
# Install httpie: pip install httpie

# Specialty triage
http POST https://web-production-945c4.up.railway.app/api/report/specialty-triage \
  user_id="test-user" \
  primary_concern="chest pain when walking"

# Generate report
http POST https://web-production-945c4.up.railway.app/api/report/cardiology \
  user_id="test-user" \
  analysis_id="valid-analysis-id"
```

## 8. Testing with Postman

1. Import this collection:
```json
{
  "info": {
    "name": "Enhanced Specialist Reports",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Specialty Triage",
      "request": {
        "method": "POST",
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"user_id\": \"{{user_id}}\",\n  \"primary_concern\": \"chest pain when walking\"\n}"
        },
        "url": {
          "raw": "{{base_url}}/api/report/specialty-triage",
          "host": ["{{base_url}}"],
          "path": ["api", "report", "specialty-triage"]
        }
      }
    }
  ],
  "variable": [
    {
      "key": "base_url",
      "value": "https://web-production-945c4.up.railway.app"
    },
    {
      "key": "user_id",
      "value": "your-user-id"
    }
  ]
}
```

## Notes:
- Replace `your-user-id` and `your-analysis-id` with actual values
- The API expects JSON content type
- All specialist endpoints follow the same pattern
- The triage endpoint helps determine which specialist report to generate
- Enhanced reports include clinical scales, detailed assessments, and actionable recommendations