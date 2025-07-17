"""Specialist Report API endpoints (8 specialty-specific reports)"""
from fastapi import APIRouter
from datetime import datetime, timezone
import json
import uuid

from models.requests import SpecialistReportRequest
from supabase_client import supabase
from business_logic import call_llm
from utils.json_parser import extract_json_from_response
from utils.data_gathering import (
    gather_report_data,
    gather_comprehensive_data, 
    extract_cardiac_patterns,
    extract_neuro_patterns,
    extract_mental_health_patterns,
    extract_dermatology_patterns,
    extract_gi_patterns,
    extract_endocrine_patterns,
    extract_pulmonary_patterns,
    gather_photo_data,
    safe_insert_report
)

router = APIRouter(prefix="/api/report", tags=["reports-specialist"])

async def load_analysis(analysis_id: str):
    """Load analysis from database"""
    response = supabase.table("report_analyses")\
        .select("*")\
        .eq("id", analysis_id)\
        .execute()
    
    if not response.data:
        raise ValueError("Analysis not found")
    
    return response.data[0]

async def save_specialist_report(report_id: str, request, specialty: str, report_data: dict):
    """Save specialist report to database"""
    report_record = {
        "id": report_id,
        "user_id": request.user_id,
        "analysis_id": request.analysis_id,
        "report_type": specialty,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "report_data": report_data,
        "executive_summary": report_data.get("executive_summary", {}).get("one_page_summary", ""),
        "confidence_score": 85,
        "model_used": "tngtech/deepseek-r1t-chimera:free",
        "specialty": specialty
    }
    
    await safe_insert_report(report_record)

@router.post("/specialist")
async def generate_specialist_report(request: SpecialistReportRequest):
    """Generate specialist-focused report"""
    try:
        analysis_response = supabase.table("report_analyses")\
            .select("*")\
            .eq("id", request.analysis_id)\
            .execute()
        
        if not analysis_response.data:
            return {"error": "Analysis not found", "status": "error"}
        
        analysis = analysis_response.data[0]
        config = analysis.get("report_config", {})
        
        # Gather all data
        data = await gather_report_data(request.user_id or analysis["user_id"], config)
        
        # Build specialist context
        specialty = request.specialty or "specialist"
        context = f"""Generate a {specialty} referral report.

Time Range: {config['time_range']['start'][:10]} to {config['time_range']['end'][:10]}
Specialty Focus: {specialty}
Primary Concern: {config.get('primary_focus', 'general health')}

Clinical Data:
{json.dumps([{
    'date': s['created_at'][:10],
    'assessment': s.get('analysis_result', {}).get('primaryCondition'),
    'confidence': s.get('confidence_score'),
    'red_flags': s.get('analysis_result', {}).get('redFlags', [])
} for s in data['quick_scans']], indent=2)}

Symptom History:
{json.dumps([{
    'date': s['created_at'][:10],
    'symptom': s.get('symptom_name'),
    'severity': s.get('severity')
} for s in data['symptom_tracking']], indent=2)}"""

        system_prompt = f"""Generate a specialist referral report for {specialty}. Return JSON:
{{
  "executive_summary": {{
    "one_page_summary": "Clinical summary for specialist",
    "chief_complaints": ["primary concerns"],
    "key_findings": ["clinically relevant findings"],
    "referral_reason": "why specialist consultation needed"
  }},
  "clinical_presentation": {{
    "presenting_symptoms": ["current symptoms"],
    "symptom_duration": "timeline of symptoms",
    "progression": "how symptoms have changed",
    "previous_treatments": ["treatments tried"],
    "response_to_treatment": "treatment responses"
  }},
  "specialist_focus": {{
    "relevant_findings": ["findings relevant to {specialty}"],
    "diagnostic_considerations": ["differential diagnoses"],
    "specific_questions": ["questions for specialist"],
    "urgency_assessment": "routine/urgent/emergent"
  }},
  "recommendations": {{
    "suggested_workup": ["recommended tests/procedures"],
    "clinical_questions": ["specific questions to address"],
    "timing": "recommended timeframe for consultation"
  }}
}}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=2000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": f"Specialist referral report for {specialty} consultation.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "referral_reason": "Clinical evaluation needed"
                },
                "clinical_presentation": {},
                "specialist_focus": {},
                "recommendations": {
                    "timing": "Within 2-4 weeks"
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "analysis_id": request.analysis_id,
            "report_type": "specialist_focused",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "executive_summary": report_data["executive_summary"]["one_page_summary"],
            "confidence_score": 85,
            "model_used": "tngtech/deepseek-r1t-chimera:free"
        }
        
        # Add specialty field for future use
        report_record["specialty"] = specialty
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "specialist_focused",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "specialty": specialty,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating specialist report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/cardiology")
async def generate_cardiology_report(request: SpecialistReportRequest):
    """Generate cardiology specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Extract cardiac-specific patterns
        cardiac_data = await extract_cardiac_patterns(all_data)
        
        # Build cardiology context
        context = f"""Generate a comprehensive cardiology report.

CARDIAC DATA:
{cardiac_data}

VITAL SIGNS AND METRICS:
- Latest recorded blood pressure: [To be integrated with wearables]
- Heart rate patterns: [To be integrated]
- Exercise tolerance: Based on reported symptoms

SYMPTOMS OF INTEREST:
- Chest pain/pressure/discomfort
- Palpitations or irregular heartbeat
- Shortness of breath
- Dizziness or lightheadedness
- Fatigue with exertion
- Swelling in legs/ankles

RISK FACTORS:
[Analyze from patient data for diabetes, hypertension, smoking, family history]

PATIENT PROFILE:
{json.dumps(analysis.get("user_data", {}), indent=2)}"""

        system_prompt = """Generate a cardiology specialist report. Include both general medical sections AND cardiology-specific analysis.

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Complete cardiovascular assessment summary",
    "chief_complaints": ["primary cardiac concerns"],
    "key_findings": ["significant cardiovascular findings"],
    "urgency_indicators": ["any concerning cardiac symptoms"],
    "action_items": ["immediate cardiac care needs"]
  },
  "patient_story": {
    "cardiac_symptoms_timeline": [
      {
        "date": "ISO date",
        "symptom": "chest pain/palpitations/etc",
        "severity": 1-10,
        "triggers": ["exertion", "stress", "rest"],
        "duration": "minutes/hours",
        "relief_factors": ["rest", "medication"]
      }
    ],
    "cardiac_risk_factors": {
      "modifiable": ["smoking", "diet", "exercise"],
      "non_modifiable": ["age", "family history", "gender"],
      "comorbidities": ["diabetes", "hypertension", "obesity"]
    }
  },
  "medical_analysis": {
    "cardiac_assessment": {
      "rhythm_concerns": ["arrhythmia patterns if any"],
      "ischemic_symptoms": ["chest pain characteristics"],
      "heart_failure_signs": ["dyspnea", "edema", "fatigue"],
      "vascular_symptoms": ["claudication", "cold extremities"]
    },
    "differential_diagnosis": [
      {
        "condition": "Condition name",
        "icd10_code": "IXX.X",
        "likelihood": "High/Medium/Low",
        "supporting_evidence": ["evidence points"]
      }
    ],
    "pattern_analysis": {
      "symptom_triggers": ["identified triggers"],
      "temporal_patterns": ["when symptoms occur"],
      "progression": "stable/worsening/improving"
    }
  },
  "cardiology_specific": {
    "recommended_tests": {
      "immediate": ["ECG", "Troponin if chest pain"],
      "routine": ["Echo", "Stress test", "Holter monitor"],
      "advanced": ["Cardiac MRI", "Coronary angiography if indicated"]
    },
    "risk_stratification": {
      "ascvd_risk": "Calculate if data available",
      "heart_failure_risk": "Low/Medium/High",
      "arrhythmia_risk": "Low/Medium/High"
    },
    "medication_considerations": {
      "indicated": ["Aspirin", "Statin", "Beta-blocker", "ACE-I/ARB"],
      "contraindicated": ["based on symptoms"],
      "monitoring_required": ["lab work needed"]
    }
  },
  "action_plan": {
    "immediate_actions": ["911 if acute symptoms", "urgent cardiology if concerning"],
    "diagnostic_pathway": {
      "week_1": ["Initial tests"],
      "week_2_4": ["Follow-up tests"],
      "ongoing": ["Monitoring plan"]
    },
    "lifestyle_modifications": {
      "diet": ["DASH diet", "sodium restriction"],
      "exercise": ["cardiac rehab if indicated", "activity recommendations"],
      "risk_reduction": ["smoking cessation", "weight management"]
    },
    "follow_up": {
      "cardiology_appointment": "Urgent/Routine/As needed",
      "primary_care": "Frequency of monitoring",
      "red_flags": ["When to seek immediate care"]
    }
  },
  "billing_optimization": {
    "suggested_codes": {
      "icd10": ["Primary and secondary diagnosis codes"],
      "cpt": ["Recommended procedure codes for workup"]
    },
    "pre_authorization": ["Tests that may need prior auth"],
    "documentation_tips": ["Key elements to document for billing"]
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Cardiology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "cardiology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "cardiology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating cardiology report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/neurology")
async def generate_neurology_report(request: SpecialistReportRequest):
    """Generate neurology specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Extract neurological patterns
        neuro_data = await extract_neuro_patterns(all_data)
        
        # Build neurology context
        context = f"""Generate a comprehensive neurology report.

NEUROLOGICAL DATA:
{neuro_data}

NEUROLOGICAL SYMPTOMS OF INTEREST:
- Headaches (type, location, frequency, triggers)
- Dizziness/vertigo
- Numbness/tingling (location, distribution)
- Weakness (focal vs generalized)
- Vision changes
- Speech difficulties
- Memory/cognitive issues
- Seizure-like activity
- Tremor/movement disorders

ASSOCIATED SYMPTOMS:
- Sleep disturbances
- Mood changes
- Autonomic symptoms"""

        system_prompt = """Generate a neurology specialist report. Include both general medical sections AND neurology-specific analysis.

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Complete neurological assessment summary",
    "chief_complaints": ["primary neurological concerns"],
    "key_findings": ["significant neurological findings"],
    "urgency_indicators": ["red flags requiring immediate attention"],
    "action_items": ["immediate neurological care needs"]
  },
  "patient_story": {
    "neurological_timeline": [
      {
        "date": "ISO date",
        "symptom": "headache/numbness/etc",
        "location": "specific location",
        "quality": "sharp/dull/burning/etc",
        "severity": 1-10,
        "duration": "minutes/hours/days",
        "associated_symptoms": ["accompanying symptoms"]
      }
    ],
    "functional_impact": {
      "daily_activities": ["activities affected"],
      "work_impact": "impact on work/school",
      "quality_of_life": "overall impact"
    }
  },
  "medical_analysis": {
    "neurological_assessment": {
      "headache_classification": "primary/secondary, type if applicable",
      "sensory_findings": ["numbness, tingling patterns"],
      "motor_findings": ["weakness patterns"],
      "cognitive_concerns": ["memory, concentration issues"],
      "red_flags": ["concerning neurological signs"]
    },
    "localization": {
      "suspected_location": "central/peripheral/both",
      "anatomical_correlation": "suspected structures involved"
    },
    "differential_diagnosis": [
      {
        "condition": "Neurological condition",
        "icd10_code": "GXX.X",
        "likelihood": "High/Medium/Low",
        "supporting_evidence": ["clinical features"]
      }
    ]
  },
  "neurology_specific": {
    "recommended_tests": {
      "imaging": ["MRI brain/spine", "CT if urgent"],
      "electrophysiology": ["EEG", "EMG/NCS if indicated"],
      "laboratory": ["B12", "thyroid", "inflammatory markers"],
      "specialized": ["LP if indicated", "autonomic testing"]
    },
    "headache_management": {
      "abortive_options": ["acute treatment options"],
      "preventive_options": ["prophylactic medications"],
      "lifestyle_triggers": ["identified triggers to avoid"]
    },
    "treatment_recommendations": {
      "pharmacological": ["medication options by condition"],
      "non_pharmacological": ["PT", "cognitive therapy", "biofeedback"],
      "referrals_needed": ["subspecialty referrals if needed"]
    }
  },
  "action_plan": {
    "immediate_actions": ["urgent steps if red flags"],
    "diagnostic_timeline": {
      "urgent": ["tests needed immediately"],
      "routine": ["scheduled evaluations"],
      "follow_up": ["reassessment timeline"]
    },
    "symptom_diary": {
      "tracking_recommendations": ["what to track"],
      "trigger_identification": ["potential triggers to monitor"]
    }
  },
  "billing_optimization": {
    "suggested_codes": {
      "icd10": ["neurological diagnosis codes"],
      "cpt": ["procedure codes for workup"]
    }
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Neurology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "neurology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "neurology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating neurology report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/psychiatry")
async def generate_psychiatry_report(request: SpecialistReportRequest):
    """Generate psychiatry specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Extract mental health patterns
        mental_health_data = await extract_mental_health_patterns(all_data)
        
        # Build psychiatry context
        context = f"""Generate a comprehensive psychiatry report.

MENTAL HEALTH DATA:
{mental_health_data}

PSYCHIATRIC SYMPTOMS OF INTEREST:
- Mood (depression, mania, mood swings)
- Anxiety (generalized, panic, phobias)
- Sleep disturbances (insomnia, hypersomnia)
- Appetite/weight changes
- Energy levels
- Concentration/focus issues
- Suicidal/homicidal ideation
- Psychotic symptoms (hallucinations, delusions)
- Substance use

FUNCTIONAL ASSESSMENT:
- Work/school performance
- Social relationships
- Self-care abilities
- Coping mechanisms"""

        system_prompt = """Generate a psychiatry specialist report. Include both general medical sections AND psychiatric-specific analysis.

Return JSON format with:
- executive_summary (mental health focus)
- patient_story (psychiatric history and timeline)
- medical_analysis (psychiatric assessment)
- psychiatry_specific section with:
  - mental_status_exam components
  - risk_assessment (suicide, violence, self-harm)
  - diagnostic_formulation (DSM-5 considerations)
  - medication_recommendations
  - therapy_recommendations
  - safety_planning if indicated
- action_plan (psychiatric treatment focused)
- billing_optimization"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Psychiatry report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "psychiatry", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "psychiatry",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating psychiatry report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/dermatology")
async def generate_dermatology_report(request: SpecialistReportRequest):
    """Generate dermatology specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data including photos
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        photo_data = await gather_photo_data(request.user_id, config)
        
        # Extract dermatology patterns
        derm_data = await extract_dermatology_patterns(all_data, photo_data)
        
        # Build dermatology context
        context = f"""Generate a comprehensive dermatology report.

DERMATOLOGICAL DATA:
{derm_data}

SKIN SYMPTOMS OF INTEREST:
- Rash characteristics (morphology, distribution)
- Itching/pruritus
- Color changes
- Texture changes
- Hair/nail involvement
- Mucosal involvement

PHOTO DOCUMENTATION:
- Number of photos: {len(photo_data)}
- Body areas documented: [from photo metadata]
- Evolution over time
- Response to treatments
- Environmental triggers"""

        system_prompt = """Generate a dermatology specialist report. Include both general medical sections AND dermatology-specific analysis.

Return JSON format with:
- executive_summary (dermatological focus)
- patient_story (skin condition timeline)
- medical_analysis (dermatological assessment)
- dermatology_specific section with:
  - lesion_descriptions (morphology, distribution)
  - photo_analysis_summary
  - differential_diagnosis (skin conditions)
  - biopsy_recommendations if indicated
  - treatment_plan (topical, systemic, procedures)
  - sun_protection_counseling
- action_plan (dermatology focused)
- billing_optimization"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Dermatology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "dermatology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "dermatology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating dermatology report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/gastroenterology")
async def generate_gastroenterology_report(request: SpecialistReportRequest):
    """Generate gastroenterology specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Extract GI patterns
        gi_data = await extract_gi_patterns(all_data)
        
        # Build gastroenterology context
        context = f"""Generate a comprehensive gastroenterology report.

GASTROINTESTINAL DATA:
{gi_data}

GI SYMPTOMS OF INTEREST:
- Abdominal pain (location, quality, timing)
- Nausea/vomiting
- Diarrhea/constipation
- Bloating/gas
- Heartburn/reflux
- Blood in stool
- Weight changes
- Appetite changes

DIETARY PATTERNS:
- Food triggers
- Meal timing
- Dietary restrictions
- Symptom-food correlations"""

        system_prompt = """Generate a gastroenterology specialist report. Include both general medical sections AND GI-specific analysis.

Return JSON format with:
- executive_summary (GI focus)
- patient_story (GI symptoms timeline)
- medical_analysis (GI assessment)
- gastroenterology_specific section with:
  - symptom_patterns (relation to meals, bowel habits)
  - alarm_symptoms (bleeding, weight loss, etc)
  - recommended_tests (endoscopy, colonoscopy, imaging)
  - dietary_recommendations
  - medication_options (PPIs, antispasmodics, etc)
  - probiotic_recommendations
- action_plan (GI focused)
- billing_optimization"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Gastroenterology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "gastroenterology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "gastroenterology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating gastroenterology report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/endocrinology")
async def generate_endocrinology_report(request: SpecialistReportRequest):
    """Generate endocrinology specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Extract endocrine patterns
        endo_data = await extract_endocrine_patterns(all_data)
        
        # Build endocrinology context
        context = f"""Generate a comprehensive endocrinology report.

ENDOCRINE DATA:
{endo_data}

ENDOCRINE SYMPTOMS OF INTEREST:
- Fatigue/energy levels
- Weight changes
- Temperature intolerance
- Hair/skin changes
- Menstrual irregularities
- Libido changes
- Mood changes
- Excessive thirst/urination

METABOLIC INDICATORS:
- Blood sugar patterns
- Weight trends
- Energy fluctuations
- Sleep quality"""

        system_prompt = """Generate an endocrinology specialist report. Include both general medical sections AND endocrine-specific analysis.

Return JSON format with:
- executive_summary (endocrine focus)
- patient_story (metabolic/hormonal timeline)
- medical_analysis (endocrine assessment)
- endocrinology_specific section with:
  - suspected_hormonal_imbalances
  - recommended_labs (thyroid, diabetes, hormones)
  - metabolic_assessment
  - treatment_options (hormone replacement, medications)
  - lifestyle_modifications (diet, exercise, stress)
  - monitoring_plan
- action_plan (endocrine focused)
- billing_optimization"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Endocrinology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "endocrinology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "endocrinology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating endocrinology report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/pulmonology")
async def generate_pulmonology_report(request: SpecialistReportRequest):
    """Generate pulmonology specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Extract pulmonary patterns
        pulm_data = await extract_pulmonary_patterns(all_data)
        
        # Build pulmonology context
        context = f"""Generate a comprehensive pulmonology report.

PULMONARY DATA:
{pulm_data}

RESPIRATORY SYMPTOMS OF INTEREST:
- Cough (productive/dry, timing)
- Shortness of breath (at rest/exertion)
- Wheezing
- Chest tightness
- Sputum production
- Hemoptysis
- Exercise tolerance
- Sleep apnea symptoms

ENVIRONMENTAL FACTORS:
- Smoking history
- Occupational exposures
- Allergens
- Air quality"""

        system_prompt = """Generate a pulmonology specialist report. Include both general medical sections AND pulmonary-specific analysis.

Return JSON format with:
- executive_summary (pulmonary focus)
- patient_story (respiratory timeline)
- medical_analysis (pulmonary assessment)
- pulmonology_specific section with:
  - breathing_pattern_analysis
  - suspected_conditions (asthma, COPD, etc)
  - recommended_tests (PFTs, chest CT, sleep study)
  - inhaler_recommendations
  - oxygen_assessment
  - pulmonary_rehab_candidacy
  - environmental_modifications
- action_plan (pulmonary focused)
- billing_optimization"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Pulmonology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "pulmonology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "pulmonology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating pulmonology report: {e}")
        return {"error": str(e), "status": "error"}