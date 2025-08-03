"""Specialist Report API endpoints (8 specialty-specific reports)"""
from fastapi import APIRouter
from datetime import datetime, timezone
import json
import uuid
import logging

from models.requests import SpecialistReportRequest, SpecialtyTriageRequest
from supabase_client import supabase
from business_logic import call_llm
from utils.json_parser import extract_json_from_response
from utils.data_gathering import (
    gather_report_data,
    gather_comprehensive_data,
    gather_selected_data,
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

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/report", tags=["reports-specialist"])

@router.post("/specialty-triage")
async def triage_specialty(request: SpecialtyTriageRequest):
    """AI determines which specialist(s) are needed based on selected quick scans/deep dives"""
    try:
        context_parts = []
        
        # Gather Quick Scan data if provided
        if request.quick_scan_ids:
            context_parts.append("QUICK SCAN DATA:")
            for scan_id in request.quick_scan_ids:
                scan_response = supabase.table("quick_scans")\
                    .select("*")\
                    .eq("id", scan_id)\
                    .execute()
                
                if scan_response.data:
                    scan = scan_response.data[0]
                    context_parts.append(f"""
Quick Scan ID: {scan_id}
Date: {scan['created_at'][:10]}
Body Part: {scan['body_part']}
Initial Symptoms: {json.dumps(scan.get('form_data', {}), indent=2)}
Analysis Result: {json.dumps(scan.get('analysis_result', {}), indent=2)}
Confidence Score: {scan.get('confidence_score')}
Urgency Level: {scan.get('urgency_level')}
LLM Summary: {scan.get('llm_summary', 'N/A')}
""")
        
        # Gather Deep Dive data if provided
        if request.deep_dive_ids:
            context_parts.append("\nDEEP DIVE DATA:")
            for dive_id in request.deep_dive_ids:
                dive_response = supabase.table("deep_dive_sessions")\
                    .select("*")\
                    .eq("id", dive_id)\
                    .execute()
                
                if dive_response.data:
                    dive = dive_response.data[0]
                    context_parts.append(f"""
Deep Dive ID: {dive_id}
Date: {dive['created_at'][:10]}
Body Part: {dive['body_part']}
Initial Form Data: {json.dumps(dive.get('form_data', {}), indent=2)}

Questions and Answers:
{json.dumps(dive.get('questions', []), indent=2)}

Final Analysis: {json.dumps(dive.get('final_analysis', {}), indent=2)}
Final Confidence: {dive.get('final_confidence')}
Status: {dive.get('status')}
""")
        
        # Build context for triage
        context = f"""Analyze the complete patient interactions to determine the most appropriate specialist referral.

{chr(10).join(context_parts)}

Based on all the information from these interactions, determine which specialist should see this patient."""

        system_prompt = """You are a medical triage specialist. Analyze symptoms and recommend appropriate specialist referrals.

Return JSON:
{
  "primary_specialty": "most appropriate specialty",
  "confidence": 0.0-1.0,
  "reasoning": "clinical reasoning for recommendation",
  "secondary_specialties": [
    {
      "specialty": "alternative specialty",
      "confidence": 0.0-1.0,
      "reason": "why to consider"
    }
  ],
  "urgency": "routine|urgent|emergent",
  "red_flags": ["concerning symptoms if any"],
  "recommended_timing": "when to see specialist"
}

Specialties: cardiology, neurology, psychiatry, dermatology, gastroenterology, endocrinology, pulmonology, primary-care"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="google/gemini-2.0-flash-exp:free",
            temperature=0.3,
            max_tokens=1000
        )
        
        triage_data = extract_json_from_response(llm_response.get("content", ""))
        
        if not triage_data:
            triage_data = {
                "primary_specialty": "primary-care",
                "confidence": 0.5,
                "reasoning": "Unable to determine specific specialty, recommend primary care evaluation",
                "urgency": "routine"
            }
        
        return {
            "status": "success",
            "triage_result": triage_data,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        print(f"Error in specialty triage: {e}")
        return {"error": str(e), "status": "error"}

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
        
        # Check if specific interactions are selected
        if request.quick_scan_ids or request.deep_dive_ids or request.photo_session_ids or request.general_assessment_ids or request.general_deep_dive_ids:
            # Gather only selected data
            data = await gather_selected_data(
                user_id=request.user_id or analysis["user_id"],
                quick_scan_ids=request.quick_scan_ids,
                deep_dive_ids=request.deep_dive_ids,
                photo_session_ids=request.photo_session_ids,
                general_assessment_ids=request.general_assessment_ids,
                general_deep_dive_ids=request.general_deep_dive_ids
            )
            # Photo analyses are already included in gather_selected_data
            photo_analyses = data.get("photo_analyses", [])
        else:
            # Fallback to comprehensive data from time range
            data = await gather_report_data(request.user_id or analysis["user_id"], config)
            
            # Get photo analysis data if available
            photo_analyses = []
            if hasattr(request, 'photo_session_ids') and request.photo_session_ids:
                photo_analyses_result = supabase.table('photo_analyses')\
                    .select('*')\
                    .in_('session_id', request.photo_session_ids)\
                    .order('created_at.desc')\
                    .execute()
                photo_analyses = photo_analyses_result.data or []
        
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
        
        # Add photo analysis data if available
        if photo_analyses:
            context += f"""

Photo Analysis Data:
{json.dumps([{
    'date': pa['created_at'][:10],
    'visual_assessment': pa['analysis_data'].get('primary_assessment'),
    'visual_observations': pa['analysis_data'].get('visual_observations', [])[:3],
    'confidence': pa.get('confidence_score'),
    'red_flags': pa['analysis_data'].get('red_flags', [])
} for pa in photo_analyses[:5]], indent=2)}"""

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
    logger.info("=== CARDIOLOGY REPORT START ===")
    logger.info(f"Analysis ID: {request.analysis_id}")
    logger.info(f"User ID: {request.user_id}")
    logger.info(f"Quick scan IDs: {request.quick_scan_ids}")
    logger.info(f"Deep dive IDs: {request.deep_dive_ids}")
    logger.info(f"General assessment IDs: {request.general_assessment_ids}")
    logger.info(f"General deep dive IDs: {request.general_deep_dive_ids}")
    logger.info(f"Photo session IDs: {request.photo_session_ids}")
    
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        logger.info(f"Report config loaded: {config}")
        
        # Check if specific interactions are selected
        if request.quick_scan_ids or request.deep_dive_ids or request.photo_session_ids or request.general_assessment_ids or request.general_deep_dive_ids:
            # Gather only selected data
            all_data = await gather_selected_data(
                user_id=request.user_id or analysis["user_id"],
                quick_scan_ids=request.quick_scan_ids,
                deep_dive_ids=request.deep_dive_ids,
                photo_session_ids=request.photo_session_ids,
                general_assessment_ids=request.general_assessment_ids,
                general_deep_dive_ids=request.general_deep_dive_ids
            )
        else:
            # Fallback to comprehensive data from time range
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

        system_prompt = """Generate a detailed cardiology specialist report analyzing the patient's cardiac symptoms and history.

CLINICAL SCALE CALCULATIONS:
1. Automatically calculate relevant standardized scales based on available data
2. For each scale:
   - Provide the calculated score
   - Include confidence level (0.0-1.0) based on data completeness
   - Explain your reasoning for each component
   - List any missing data that would improve accuracy
3. Use your medical knowledge to infer reasonable values when data is indirect
4. Always err on the side of caution - when uncertain, indicate lower confidence

For Cardiology, automatically calculate when relevant:
- CHA₂DS₂-VASc (for any atrial fibrillation or stroke risk assessment)
- HAS-BLED (if anticoagulation is being considered)
- NYHA Functional Classification (for heart failure symptoms)
- Canadian Cardiovascular Society (CCS) Angina Grade

BEST PRACTICES FOR SCALE CALCULATION:
- If age is mentioned as "elderly" infer 75+ for scoring
- If "history of stroke" mentioned, count as positive even without dates
- For functional capacity, use activity descriptions to estimate METs
- Document all assumptions made in the reasoning field

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive clinical overview for cardiologist",
    "key_findings": ["most clinically significant findings"],
    "patterns_identified": ["temporal or trigger patterns"],
    "chief_complaints": ["primary cardiac concerns"],
    "action_items": ["immediate actions needed"],
    "specialist_focus": "cardiology",
    "target_audience": "cardiologist"
  },
  
  "clinical_summary": {
    "chief_complaint": "Primary cardiac concern in patient's words",
    "hpi": "Detailed history of present illness with timeline",
    "symptom_timeline": [
      {
        "date": "ISO date",
        "symptoms": "specific symptoms reported",
        "severity": 1-10,
        "context": "what patient was doing",
        "duration": "how long it lasted",
        "resolution": "what helped"
      }
    ],
    "pattern_analysis": {
      "frequency": "how often symptoms occur",
      "triggers": ["identified triggers"],
      "alleviating_factors": ["what helps"],
      "progression": "getting worse/better/stable over time"
    }
  },
  
  "cardiology_assessment": {
    "angina_classification": {
      "ccs_class": "I-IV based on functional limitation",
      "typical_features": ["substernal", "exertional", "relieved by rest"],
      "atypical_features": ["any unusual characteristics"]
    },
    "functional_capacity": {
      "current": "estimated METs based on activities",
      "baseline": "prior exercise tolerance if known",
      "specific_limitations": ["cannot climb stairs", "stops after 1 block", "etc"]
    },
    "risk_stratification": {
      "clinical_risk": "low/intermediate/high based on symptoms",
      "missing_data_for_scores": ["BP", "cholesterol", "smoking status"],
      "red_flags": ["concerning features requiring urgent evaluation"]
    }
  },
  
  "cardiologist_specific_findings": {
    "chest_pain_characterization": {
      "quality": "pressure/sharp/burning/etc",
      "location": "specific location described",
      "radiation": "if pain spreads anywhere",
      "associated_symptoms": ["dyspnea", "diaphoresis", "nausea", "palpitations"]
    },
    "symptom_pattern_insights": {
      "temporal_patterns": "morning vs evening, weekday vs weekend",
      "activity_correlation": "symptoms with specific activities",
      "stress_relationship": "emotional trigger patterns noted"
    },
    "functional_decline": {
      "trajectory": "how function has changed over time",
      "compensatory_behaviors": ["avoiding stairs", "stopping activities"]
    }
  },
  
  "diagnostic_priorities": {
    "immediate": [
      {
        "test": "ECG",
        "rationale": "baseline assessment, check for ischemic changes",
        "timing": "same day"
      }
    ],
    "short_term": [
      {
        "test": "Exercise stress test or pharmacologic if cannot exercise",
        "rationale": "assess for inducible ischemia",
        "timing": "within 1 week given symptom progression"
      },
      {
        "test": "Lipid panel, A1C, TSH",
        "rationale": "risk stratification and secondary causes",
        "timing": "with next blood draw"
      }
    ],
    "contingent": [
      {
        "test": "Coronary CTA or angiography",
        "condition": "if stress test positive or high clinical suspicion",
        "rationale": "define coronary anatomy"
      }
    ]
  },
  
  "treatment_recommendations": {
    "immediate_medical_therapy": [
      {
        "medication": "Aspirin 81mg daily",
        "rationale": "antiplatelet for suspected CAD"
      },
      {
        "medication": "Atorvastatin 40mg daily",
        "rationale": "high-intensity statin for ASCVD risk reduction"
      },
      {
        "medication": "Metoprolol 25mg BID",
        "rationale": "rate control and anti-anginal effect"
      }
    ],
    "symptom_management": {
      "prn_medications": ["Sublingual nitroglycerin for acute episodes"],
      "activity_modification": "avoid known triggers until evaluated",
      "monitoring": "keep symptom diary"
    },
    "lifestyle_interventions": {
      "diet": "Mediterranean or DASH diet for cardiovascular health",
      "exercise": "cardiac rehab referral after evaluation",
      "risk_factor_modification": ["smoking cessation if applicable", "weight management", "stress reduction"]
    }
  },
  
  "care_coordination": {
    "referral_urgency": "routine/urgent/emergent",
    "pre_visit_preparation": [
      "bring list of all medications",
      "document symptom episodes",
      "gather family cardiac history"
    ],
    "follow_up_plan": {
      "cardiology": "within 2 weeks",
      "primary_care": "after cardiac workup for risk factor management",
      "emergency_plan": "call 911 for rest pain or prolonged symptoms"
    }
  },
  
  "data_quality_notes": {
    "completeness": "good symptom description, missing risk factor data",
    "consistency": "symptoms consistent across reports",
    "gaps": ["family history needed", "BP readings helpful", "prior ECGs if available"]
  },
  
  "clinical_scales": {
    "CHA2DS2_VASc": {
      "calculated": "score based on available data",
      "confidence": 0.0-1.0,
      "confidence_level": "high/medium/low",
      "reasoning": "Detailed explanation of how score was calculated",
      "breakdown": {
        "age": 0-2,
        "sex": 0-1,
        "chf": 0-1,
        "hypertension": 0-1,
        "stroke": 0-2,
        "vascular": 0-1,
        "diabetes": 0-1
      },
      "missing_data": ["specific data points that would improve accuracy"],
      "interpretation": "Risk level and anticoagulation recommendation",
      "annual_stroke_risk": "percentage based on score"
    },
    "NYHA_Classification": {
      "class": "I-IV",
      "confidence": 0.0-1.0,
      "reasoning": "Based on functional limitations described",
      "functional_description": "What patient can/cannot do"
    },
    "CCS_Angina_Grade": {
      "grade": "I-IV",
      "confidence": 0.0-1.0,
      "reasoning": "Based on angina patterns and limitations",
      "typical_activities_affected": ["specific examples"]
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
        
        # Check if specific interactions are selected
        if request.quick_scan_ids or request.deep_dive_ids or request.photo_session_ids or request.general_assessment_ids or request.general_deep_dive_ids:
            # Gather only selected data
            all_data = await gather_selected_data(
                user_id=request.user_id or analysis["user_id"],
                quick_scan_ids=request.quick_scan_ids,
                deep_dive_ids=request.deep_dive_ids,
                photo_session_ids=request.photo_session_ids,
                general_assessment_ids=request.general_assessment_ids,
                general_deep_dive_ids=request.general_deep_dive_ids
            )
        else:
            # Fallback to comprehensive data from time range
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

        system_prompt = """Generate a detailed neurology specialist report focusing on neurological symptoms and patterns.

CLINICAL SCALE CALCULATIONS:
1. Automatically calculate relevant standardized scales based on available data
2. For each scale:
   - Provide the calculated score
   - Include confidence level (0.0-1.0) based on data completeness
   - Explain your reasoning for each component
   - List any missing data that would improve accuracy
3. Use your medical knowledge to infer reasonable values when data is indirect

For Neurology, automatically calculate when relevant:
- MIDAS (Migraine Disability Assessment) - estimate days affected from symptom reports
- HIT-6 (Headache Impact Test) - infer from functional limitations
- ICHD-3 criteria matching - pattern match symptoms to headache types
- PHQ-9 (if mood symptoms present with neurological complaints)

BEST PRACTICES FOR SCALE CALCULATION:
- For MIDAS: Count reported days with limitations in work/household/social activities
- For headache classification: Match patterns to ICHD-3 diagnostic criteria
- If cognitive complaints present, estimate MoCA/MMSE based on described deficits
- Document all inferences and assumptions

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive clinical overview for neurologist",
    "key_findings": ["most clinically significant neurological findings"],
    "patterns_identified": ["temporal patterns, triggers, progression"],
    "chief_complaints": ["primary neurological concerns"],
    "action_items": ["immediate evaluations or treatments needed"],
    "specialist_focus": "neurology",
    "target_audience": "neurologist"
  },
  
  "clinical_summary": {
    "chief_complaint": "Primary neurological concern",
    "hpi": "Detailed neurological history with timeline",
    "symptom_timeline": [
      {
        "date": "ISO date",
        "symptoms": "specific neurological symptoms",
        "location": "anatomical location",
        "severity": 1-10,
        "duration": "episode duration",
        "associated_symptoms": ["accompanying symptoms"]
      }
    ]
  },
  
  "neurology_assessment": {
    "headache_characterization": {
      "classification": "Probable diagnosis per ICHD-3 criteria",
      "frequency": "episodes per month",
      "pattern": {
        "typical_onset": "time of day patterns",
        "duration": "typical episode length",
        "laterality": "unilateral/bilateral percentages"
      }
    },
    "red_flag_screen": {
      "thunderclap_onset": "present/absent",
      "progressive_pattern": "worsening/stable",
      "focal_deficits": "any reported",
      "systemic_symptoms": "fever/weight loss",
      "papilledema_risk": "symptoms suggesting increased ICP"
    }
  },
  
  "neurologist_specific_findings": {
    "headache_phenomenology": {
      "pain_quality": "throbbing/pressure/sharp/burning",
      "location_specifics": "precise anatomical description",
      "radiation_pattern": "if pain spreads",
      "triggers": {
        "identified": ["specific triggers from history"],
        "suspected": ["possible triggers to test"],
        "protective": ["what prevents episodes"]
      }
    },
    "associated_phenomena": {
      "autonomic": ["lacrimation", "rhinorrhea", "ptosis"],
      "sensory": ["photophobia", "phonophobia", "osmophobia"],
      "aura": "visual/sensory/speech symptoms if present"
    },
    "medication_patterns": {
      "current_use": {
        "acute": "medications and frequency",
        "preventive": "if any tried",
        "overuse_risk": "days per month of analgesic use"
      },
      "treatment_response": "what has helped/failed"
    }
  },
  
  "diagnostic_plan": {
    "imaging": {
      "mri_brain": {
        "indicated": "yes/no",
        "rationale": "red flags or atypical features",
        "protocol": "with/without contrast",
        "urgency": "routine/urgent"
      }
    },
    "laboratory": [
      {
        "test": "ESR, CRP",
        "rationale": "if giant cell arteritis suspected"
      },
      {
        "test": "Thyroid function",
        "rationale": "can trigger headaches"
      }
    ],
    "specialized": {
      "sleep_study": "if sleep-related headaches",
      "lumbar_puncture": "only if specific indications"
    }
  },
  
  "treatment_recommendations": {
    "acute_management": {
      "first_line": [
        {
          "medication": "Sumatriptan 100mg",
          "instructions": "at onset, may repeat in 2 hours",
          "contraindications": "vascular disease"
        }
      ],
      "rescue": "if first-line fails",
      "limits": "maximum days per month to avoid MOH"
    },
    "preventive_strategy": {
      "lifestyle": {
        "essential": ["sleep hygiene", "meal regularity", "hydration"],
        "triggers_to_avoid": "based on diary"
      },
      "medications": [
        {
          "drug": "Topiramate",
          "starting_dose": "25mg daily",
          "target": "50-100mg BID",
          "side_effects": "cognitive, weight loss"
        },
        {
          "drug": "Propranolol",
          "starting_dose": "20mg BID",
          "target": "80-160mg daily",
          "contraindications": "asthma, bradycardia"
        }
      ],
      "expected_response": "50% reduction in 3 months"
    },
    "non_pharmacologic": {
      "recommended": ["CBT for chronic pain", "biofeedback", "acupuncture"],
      "physical_therapy": "if cervicogenic component"
    }
  },
  
  "follow_up_plan": {
    "neurology_visit": "4-6 weeks to assess treatment",
    "headache_diary": {
      "track": ["frequency", "triggers", "medication use"],
      "apps_recommended": ["specific tracking apps"]
    },
    "warning_signs": [
      "sudden severe headache",
      "neurological deficits",
      "fever with headache"
    ]
  },
  
  "data_insights": {
    "pattern_recognition": "episodic migraine progressing to chronic",
    "comorbidities": ["anxiety noted in reports", "sleep issues"],
    "prognosis": "good with appropriate prophylaxis"
  },
  
  "clinical_scales": {
    "MIDAS": {
      "calculated": "total score based on disability days",
      "confidence": 0.0-1.0,
      "confidence_level": "high/medium/low",
      "grade": "I-IV",
      "interpretation": "disability level and treatment implications",
      "reasoning": "How days were calculated from symptom reports",
      "breakdown": {
        "missed_work_school": "estimated days",
        "reduced_productivity_work": "estimated days",
        "missed_household": "estimated days",
        "reduced_productivity_household": "estimated days",
        "missed_social": "estimated days"
      },
      "missing_data": ["specific data that would improve accuracy"],
      "treatment_recommendation": "based on severity grade"
    },
    "ICHD3_Classification": {
      "diagnosis": "Most likely headache type per ICHD-3",
      "confidence": 0.0-1.0,
      "criteria_met": ["specific criteria fulfilled"],
      "criteria_missing": ["criteria that couldn't be assessed"],
      "differential_diagnoses": ["other possible headache types"],
      "reasoning": "Why this classification was chosen"
    },
    "HIT6_Estimate": {
      "estimated_score": "score based on functional impact",
      "confidence": 0.0-1.0,
      "severity_category": "little/moderate/substantial/severe impact",
      "reasoning": "How impact was assessed from reports"
    },
    "Cognitive_Screen": {
      "assessment": "if cognitive complaints present",
      "estimated_MoCA": "score range if applicable",
      "confidence": 0.0-1.0,
      "domains_affected": ["memory", "attention", "language", "etc"],
      "reasoning": "Based on reported cognitive symptoms"
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
        
        # Check if specific interactions are selected
        if request.quick_scan_ids or request.deep_dive_ids or request.photo_session_ids or request.general_assessment_ids or request.general_deep_dive_ids:
            # Gather only selected data
            all_data = await gather_selected_data(
                user_id=request.user_id or analysis["user_id"],
                quick_scan_ids=request.quick_scan_ids,
                deep_dive_ids=request.deep_dive_ids,
                photo_session_ids=request.photo_session_ids,
                general_assessment_ids=request.general_assessment_ids,
                general_deep_dive_ids=request.general_deep_dive_ids
            )
        else:
            # Fallback to comprehensive data from time range
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

        system_prompt = """Generate a detailed psychiatry specialist report analyzing mental health symptoms and psychosocial factors.

CLINICAL SCALE CALCULATIONS:
1. Automatically calculate relevant standardized scales based on available data
2. For each scale:
   - Provide the calculated score
   - Include confidence level (0.0-1.0) based on data completeness
   - Map reported symptoms to questionnaire items
   - Explain your reasoning for each item score
   - List any missing data that would improve accuracy

For Psychiatry, automatically calculate when relevant:
- PHQ-9 (Patient Health Questionnaire) - map symptoms to 9 items
- GAD-7 (Generalized Anxiety Disorder) - map anxiety symptoms to 7 items
- Columbia Suicide Severity Rating Scale - if any SI mentioned
- MADRS (Montgomery-Åsberg Depression Rating Scale) - for detailed depression assessment
- Mood Disorder Questionnaire (MDQ) - if bipolar symptoms suspected

BEST PRACTICES FOR SCALE CALCULATION:
- Map "feeling down" to PHQ-9 item 2, "little interest" to item 1
- For GAD-7, look for worry, restlessness, irritability patterns
- Always assess suicide risk carefully - err on side of caution
- Consider frequency: "nearly every day" = 3, "more than half the days" = 2, "several days" = 1
- Document how each item score was derived

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive clinical overview for psychiatrist",
    "key_findings": ["most clinically significant psychiatric findings"],
    "patterns_identified": ["mood patterns, triggers, cycles"],
    "chief_complaints": ["primary mental health concerns"],
    "action_items": ["immediate safety or treatment needs"],
    "specialist_focus": "psychiatry",
    "target_audience": "psychiatrist"
  },
  
  "clinical_summary": {
    "chief_complaint": "Primary mental health concern",
    "hpi": "Psychiatric history with precipitants and timeline",
    "symptom_timeline": [
      {
        "date": "ISO date",
        "symptoms": "mood/anxiety/psychotic symptoms",
        "severity": "mild/moderate/severe",
        "triggers": "identified stressors",
        "impact": "functional impairment"
      }
    ]
  },
  
  "psychiatry_assessment": {
    "diagnostic_impression": {
      "primary": "Most likely DSM-5 diagnosis",
      "differential": ["other considerations"],
      "specifiers": ["with anxious distress", "severity", "etc"],
      "timeline": "acute/chronic, first episode/recurrent"
    },
    "risk_assessment": {
      "suicide_risk": {
        "current_ideation": "none/passive/active",
        "plan_intent": "present/absent",
        "risk_level": "low/moderate/high",
        "protective_factors": ["identified protections"]
      },
      "violence_risk": "assessment if indicated",
      "self_harm": "non-suicidal self-injury patterns"
    }
  },
  
  "psychiatrist_specific_findings": {
    "mental_status_elements": {
      "mood_symptoms": ["depression", "anhedonia", "hopelessness"],
      "anxiety_symptoms": ["worry", "panic", "avoidance"],
      "cognitive_symptoms": ["concentration", "memory", "decision-making"],
      "neurovegetative": ["sleep", "appetite", "energy", "psychomotor"]
    },
    "functional_analysis": {
      "occupational": "impact on work/school",
      "social": "relationship effects",
      "adls": "self-care status",
      "behavioral_activation": "activity level changes"
    },
    "psychosocial_factors": {
      "stressors": ["identified triggers"],
      "supports": ["family", "friends", "community"],
      "coping_mechanisms": ["adaptive", "maladaptive"]
    }
  },
  
  "treatment_planning": {
    "psychopharmacology": {
      "recommended_medication": {
        "class": "SSRI/SNRI/other",
        "specific_drug": "medication name",
        "starting_dose": "initial dose",
        "titration": "increase schedule",
        "monitoring": "side effects to watch"
      },
      "past_medications": {
        "tried": ["what has been tried"],
        "response": "effectiveness and tolerability"
      },
      "augmentation_options": "if partial response"
    },
    "psychotherapy": {
      "modality": "CBT/DBT/IPT/supportive",
      "frequency": "weekly/biweekly",
      "focus": ["specific targets"],
      "duration": "expected treatment length"
    },
    "behavioral_interventions": {
      "immediate": ["sleep hygiene", "exercise", "routine"],
      "behavioral_activation": ["pleasant activities", "social contact"],
      "coping_skills": ["specific techniques"]
    }
  },
  
  "safety_planning": {
    "warning_signs": ["personal triggers"],
    "coping_strategies": ["internal strategies"],
    "support_contacts": ["who to reach out to"],
    "professional_contacts": ["therapist", "crisis line"],
    "environment_safety": ["means restriction if needed"],
    "follow_up": "next appointment timing"
  },
  
  "coordination_of_care": {
    "primary_care": "communicate about medications",
    "therapy_referral": {
      "type": "specific therapy modality",
      "urgency": "routine/expedited",
      "expected_wait": "typical timeframe"
    },
    "community_resources": ["support groups", "peer support"],
    "monitoring_plan": {
      "frequency": "follow-up schedule",
      "symptom_tracking": "PHQ-9 q2weeks",
      "medication_monitoring": "labs if needed"
    }
  },
  
  "prognosis_factors": {
    "positive_indicators": ["help-seeking", "support system", "insight"],
    "challenges": ["chronicity", "comorbidities", "stressors"],
    "expected_trajectory": "with appropriate treatment"
  },
  
  "clinical_scales": {
    "PHQ9": {
      "calculated": "total score 0-27",
      "confidence": 0.0-1.0,
      "confidence_level": "high/medium/low",
      "severity": "minimal/mild/moderate/moderately severe/severe",
      "interpretation": "Depression severity and treatment implications",
      "reasoning": "How each item was scored based on symptoms",
      "item_scores": {
        "little_interest": 0-3,
        "feeling_down": 0-3,
        "sleep_problems": 0-3,
        "tired_no_energy": 0-3,
        "appetite_problems": 0-3,
        "feeling_bad_about_self": 0-3,
        "concentration_problems": 0-3,
        "moving_slowly_or_restless": 0-3,
        "suicidal_thoughts": 0-3
      },
      "suicide_item_score": 0-3,
      "suicide_risk": "none/low/moderate/high",
      "missing_data": ["symptoms not explicitly assessed"],
      "treatment_recommendation": "based on severity"
    },
    "GAD7": {
      "calculated": "total score 0-21",
      "confidence": 0.0-1.0,
      "severity": "minimal/mild/moderate/severe",
      "interpretation": "Anxiety severity",
      "reasoning": "How anxiety symptoms mapped to scale items",
      "item_mapping": {
        "feeling_nervous": 0-3,
        "cant_stop_worrying": 0-3,
        "worrying_too_much": 0-3,
        "trouble_relaxing": 0-3,
        "restless": 0-3,
        "easily_annoyed": 0-3,
        "feeling_afraid": 0-3
      },
      "treatment_recommendation": "based on severity"
    },
    "Columbia_SSR": {
      "calculated": "if SI present",
      "confidence": 0.0-1.0,
      "ideation_type": "none/passive/active",
      "plan": "present/absent",
      "intent": "present/absent",
      "risk_level": "low/moderate/high/imminent",
      "protective_factors": ["identified protective elements"],
      "reasoning": "How risk was assessed"
    },
    "MADRS": {
      "estimated_score": "if sufficient depression data",
      "confidence": 0.0-1.0,
      "severity_category": "based on score ranges",
      "key_items_assessed": ["apparent sadness", "reported sadness", "inner tension", "etc"],
      "reasoning": "Items that could be scored from available data"
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
        
        # Check if specific interactions are selected
        if request.quick_scan_ids or request.deep_dive_ids or request.photo_session_ids or request.general_assessment_ids or request.general_deep_dive_ids:
            # Gather only selected data
            all_data = await gather_selected_data(
                user_id=request.user_id or analysis["user_id"],
                quick_scan_ids=request.quick_scan_ids,
                deep_dive_ids=request.deep_dive_ids,
                photo_session_ids=request.photo_session_ids,
                general_assessment_ids=request.general_assessment_ids,
                general_deep_dive_ids=request.general_deep_dive_ids
            )
            # For dermatology, photo_data comes from photo_analyses in all_data
            photo_data = all_data.get("photo_analyses", [])
        else:
            # Fallback to comprehensive data from time range
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

        system_prompt = """Generate a detailed dermatology specialist report analyzing skin conditions with photo documentation insights.

CLINICAL SCALE CALCULATIONS:
1. Automatically calculate relevant standardized scales based on available data
2. For each scale:
   - Provide the calculated score
   - Include confidence level (0.0-1.0) based on data completeness
   - Explain your reasoning
   - List any missing data that would improve accuracy

For Dermatology, automatically calculate when relevant:
- PASI (Psoriasis Area and Severity Index) - for psoriasis
- DLQI (Dermatology Life Quality Index) - quality of life impact
- SCORAD (for atopic dermatitis)
- IGA (Investigator's Global Assessment)

BEST PRACTICES:
- Use photo analysis to estimate body surface area affected
- Assess erythema, induration, and desquamation for PASI
- Map patient-reported impacts to DLQI questions
- Document visual findings that support scoring

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive clinical overview for dermatologist",
    "key_findings": ["most significant dermatological findings"],
    "patterns_identified": ["distribution patterns, evolution"],
    "chief_complaints": ["primary skin concerns"],
    "action_items": ["immediate evaluations or treatments"],
    "specialist_focus": "dermatology",
    "target_audience": "dermatologist"
  },
  "clinical_summary": {
    "chief_complaint": "Primary skin concern",
    "hpi": "Detailed history of skin condition",
    "lesion_timeline": [
      {
        "date": "ISO date",
        "description": "appearance and changes",
        "location": "anatomical sites",
        "symptoms": "itching/pain/burning",
        "triggers": "identified factors"
      }
    ]
  },
  
  "dermatology_assessment": {
    "lesion_characterization": {
      "morphology": "papules/plaques/vesicles/etc",
      "configuration": "scattered/grouped/linear",
      "distribution": "body areas affected",
      "color": "erythematous/hyperpigmented/etc",
      "surface_changes": "scale/crust/erosion",
      "size": "measurements from photos"
    },
    "clinical_diagnosis": {
      "primary_impression": "most likely diagnosis",
      "differential": ["other possibilities"],
      "confidence": "high/moderate/low",
      "supporting_features": ["classic signs present"]
    },
    "severity_assessment": {
      "bsa_affected": "percent of body surface",
      "pasi_estimate": "if psoriasis suspected",
      "impact_score": "quality of life impact 1-10"
    }
  },
  
  "dermatologist_specific_findings": {
    "photo_analysis": {
      "quality": "good/fair/poor lighting and angles",
      "evolution_documented": "changes over time visible",
      "key_features": ["specific findings in photos"],
      "comparison": "improvement/worsening/stable"
    },
    "clinical_patterns": {
      "koebner_phenomenon": "present/absent",
      "distribution_pattern": "extensor/flexural/sun-exposed",
      "symmetry": "bilateral/unilateral",
      "dermatomal": "follows nerve distribution"
    },
    "associated_findings": {
      "nail_changes": "pitting/onycholysis/etc",
      "scalp_involvement": "if present",
      "mucosal_involvement": "oral/genital",
      "joint_symptoms": "if psoriatic arthritis risk"
    }
  },
  
  "diagnostic_plan": {
    "biopsy_recommendation": {
      "indicated": "yes/no",
      "rationale": "uncertain diagnosis/rule out malignancy",
      "type": "punch/shave/excisional",
      "sites": "where to biopsy"
    },
    "laboratory": [
      {
        "test": "KOH prep",
        "indication": "if fungal suspected"
      },
      {
        "test": "Patch testing",
        "indication": "if contact dermatitis"
      }
    ],
    "imaging": "dermoscopy if available"
  },
  
  "treatment_recommendations": {
    "topical_therapy": {
      "first_line": [
        {
          "medication": "Clobetasol 0.05% ointment",
          "instructions": "BID to affected areas x 2 weeks",
          "then": "weekend pulse therapy"
        }
      ],
      "adjuncts": [
        {
          "medication": "Calcipotriene",
          "role": "maintenance therapy",
          "combination": "with topical steroid"
        }
      ],
      "vehicles": "ointment for dry areas, cream for moist"
    },
    "systemic_considerations": {
      "threshold": "BSA >10% or QOL impact",
      "options": [
        {
          "medication": "Methotrexate",
          "dose": "15-25mg weekly",
          "monitoring": "LFTs, CBC"
        }
      ],
      "phototherapy": "NB-UVB if widespread"
    },
    "skin_care": {
      "moisturizers": "thick creams/ointments daily",
      "bathing": "lukewarm water, gentle cleansers",
      "triggers_to_avoid": ["harsh soaps", "hot water"]
    }
  },
  
  "patient_education": {
    "disease_course": "chronic with flares and remissions",
    "trigger_avoidance": ["stress", "skin trauma", "infections"],
    "treatment_expectations": "improvement in 4-6 weeks",
    "when_to_follow_up": [
      "no improvement in 4 weeks",
      "side effects from treatment",
      "new lesions appearing"
    ]
  },
  
  "follow_up_plan": {
    "timing": "4-6 weeks for treatment response",
    "photo_documentation": "take photos before starting treatment",
    "treatment_diary": "track what helps/worsens"
  },
  
  "clinical_scales": {
    "PASI": {
      "calculated": "score if psoriasis suspected",
      "confidence": 0.0-1.0,
      "confidence_level": "high/medium/low",
      "severity_category": "mild/moderate/severe",
      "reasoning": "How score was estimated from photos and descriptions",
      "body_regions": {
        "head": {"area": 0-6, "erythema": 0-4, "induration": 0-4, "desquamation": 0-4},
        "trunk": {"area": 0-6, "erythema": 0-4, "induration": 0-4, "desquamation": 0-4},
        "upper_extremities": {"area": 0-6, "erythema": 0-4, "induration": 0-4, "desquamation": 0-4},
        "lower_extremities": {"area": 0-6, "erythema": 0-4, "induration": 0-4, "desquamation": 0-4}
      },
      "missing_data": ["areas not photographed", "scale/crust detail needed"]
    },
    "DLQI": {
      "estimated_score": "0-30 based on QOL impact",
      "confidence": 0.0-1.0,
      "impact_level": "no effect/small/moderate/very large/extremely large",
      "reasoning": "How life impacts were assessed",
      "domains_affected": ["symptoms", "daily activities", "leisure", "work/school", "relationships", "treatment"]
    },
    "IGA": {
      "score": "0-4 (clear to severe)",
      "confidence": 0.0-1.0,
      "reasoning": "Based on overall lesion appearance",
      "change_from_baseline": "if follow-up photos available"
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
        
        # Check if specific interactions are selected
        if request.quick_scan_ids or request.deep_dive_ids or request.photo_session_ids or request.general_assessment_ids or request.general_deep_dive_ids:
            # Gather only selected data
            all_data = await gather_selected_data(
                user_id=request.user_id or analysis["user_id"],
                quick_scan_ids=request.quick_scan_ids,
                deep_dive_ids=request.deep_dive_ids,
                photo_session_ids=request.photo_session_ids,
                general_assessment_ids=request.general_assessment_ids,
                general_deep_dive_ids=request.general_deep_dive_ids
            )
        else:
            # Fallback to comprehensive data from time range
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

        system_prompt = """Generate a detailed gastroenterology specialist report analyzing GI symptoms and patterns.

CLINICAL SCALE CALCULATIONS:
1. Automatically calculate relevant standardized scales based on available data
2. For each scale, provide score, confidence, reasoning, and missing data

For Gastroenterology, automatically calculate when relevant:
- Rome IV Criteria (for IBS, functional dyspepsia)
- Bristol Stool Scale patterns
- IBS-SSS (IBS Symptom Severity Score)
- Mayo Score (for UC) or CDAI (for Crohn's) if IBD suspected

BEST PRACTICES:
- Map bowel patterns to Bristol Stool Scale (1-7)
- Assess Rome IV criteria for functional disorders
- Track symptom frequency and severity for IBS-SSS
- Note alarm features that override functional diagnosis

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive clinical overview for gastroenterologist",
    "key_findings": ["most significant GI findings"],
    "patterns_identified": ["dietary triggers, bowel patterns"],
    "chief_complaints": ["primary GI concerns"],
    "action_items": ["immediate evaluations needed"],
    "specialist_focus": "gastroenterology",
    "target_audience": "gastroenterologist"
  },
  "clinical_summary": {
    "chief_complaint": "Primary GI concern",
    "hpi": "Detailed GI history with timeline",
    "symptom_timeline": [
      {
        "date": "ISO date",
        "symptoms": "specific GI symptoms",
        "severity": 1-10,
        "timing": "relation to meals",
        "bowel_pattern": "changes noted"
      }
    ]
  },
  
  "gastroenterology_assessment": {
    "symptom_characterization": {
      "abdominal_pain": {
        "location": "epigastric/periumbilical/RLQ/etc",
        "quality": "cramping/burning/sharp",
        "timing": "before/during/after meals",
        "relief": "with BM/antacids/nothing"
      },
      "bowel_patterns": {
        "frequency": "times per day/week",
        "consistency": "Bristol stool scale",
        "blood": "present/absent",
        "mucus": "present/absent"
      },
      "associated_symptoms": {
        "nausea": "frequency and triggers",
        "bloating": "timing and severity",
        "weight_change": "amount and timeframe"
      }
    },
    "alarm_features": {
      "present": ["list any red flags"],
      "absent": ["important negatives"],
      "risk_assessment": "low/moderate/high for serious pathology"
    }
  },
  
  "gi_specific_findings": {
    "dietary_analysis": {
      "trigger_foods": ["identified from history"],
      "safe_foods": ["well tolerated"],
      "meal_patterns": "regular/irregular",
      "fodmap_sensitivity": "suspected based on symptoms"
    },
    "functional_assessment": {
      "rome_criteria": "meets criteria for IBS/functional dyspepsia",
      "symptom_pattern": "post-infectious/stress-related/dietary",
      "quality_of_life_impact": "work/social/sleep"
    },
    "medication_history": {
      "current": ["what patient takes now"],
      "previous_trials": ["what helped/failed"],
      "otc_use": "antacids/laxatives frequency"
    }
  },
  
  "diagnostic_recommendations": {
    "laboratory": [
      {
        "test": "CBC, CMP, TSH",
        "rationale": "baseline and rule out metabolic causes"
      },
      {
        "test": "Celiac panel",
        "rationale": "if chronic diarrhea or bloating"
      },
      {
        "test": "H. pylori testing",
        "rationale": "if dyspepsia symptoms"
      }
    ],
    "endoscopy": {
      "colonoscopy": {
        "indicated": "yes/no based on symptoms and age",
        "urgency": "routine/expedited",
        "prep_considerations": "standard/modified"
      },
      "upper_endoscopy": {
        "indicated": "if GERD/dyspepsia/alarm symptoms",
        "biopsies": "H. pylori, celiac if indicated"
      }
    },
    "imaging": {
      "ct_abdomen": "only if suspicion of structural issue",
      "other": "HIDA scan if biliary symptoms"
    }
  },
  
  "treatment_plan": {
    "dietary_modifications": {
      "immediate": ["food diary", "regular meals", "avoid triggers"],
      "trial_diets": ["low FODMAP", "gluten-free if indicated"],
      "nutritionist_referral": "if complex dietary needs"
    },
    "medications": {
      "acid_suppression": {
        "ppi": "omeprazole 20mg daily x 8 weeks",
        "timing": "30 min before breakfast"
      },
      "motility": {
        "if_constipation": "PEG 3350 daily",
        "if_diarrhea": "loperamide PRN"
      },
      "antispasmodics": "dicyclomine for cramping"
    },
    "lifestyle": {
      "stress_management": "noted correlation with symptoms",
      "exercise": "regular activity helps motility",
      "sleep": "poor sleep worsens GI symptoms"
    }
  },
  
  "follow_up_plan": {
    "timing": "4-6 weeks to assess response",
    "symptom_diary": "track triggers and patterns",
    "red_flags": [
      "persistent vomiting",
      "GI bleeding",
      "severe pain",
      "unintended weight loss"
    ]
  },
  
  "clinical_scales": {
    "Rome_IV_Assessment": {
      "diagnosis": "IBS/functional dyspepsia/none",
      "confidence": 0.0-1.0,
      "criteria_met": ["specific Rome IV criteria fulfilled"],
      "criteria_missing": ["criteria that need assessment"],
      "subtype": "IBS-C/IBS-D/IBS-M if applicable",
      "reasoning": "How diagnosis was determined"
    },
    "Bristol_Stool_Pattern": {
      "predominant_type": "1-7",
      "range": "types seen",
      "consistency": "how consistent the pattern is",
      "confidence": 0.0-1.0,
      "reasoning": "Based on stool descriptions"
    },
    "IBS_SSS": {
      "estimated_score": "0-500",
      "severity": "mild/moderate/severe",
      "confidence": 0.0-1.0,
      "components": {
        "pain_severity": "0-100",
        "pain_frequency": "0-100",
        "distension_severity": "0-100",
        "bowel_dissatisfaction": "0-100",
        "life_interference": "0-100"
      },
      "reasoning": "How scores were estimated"
    },
    "GERD_Assessment": {
      "reflux_frequency": "episodes per week",
      "impact_score": "if GERD symptoms present",
      "confidence": 0.0-1.0,
      "alarm_features": ["dysphagia", "weight loss", "anemia"]
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
        
        # Check if specific interactions are selected
        if request.quick_scan_ids or request.deep_dive_ids or request.photo_session_ids or request.general_assessment_ids or request.general_deep_dive_ids:
            # Gather only selected data
            all_data = await gather_selected_data(
                user_id=request.user_id or analysis["user_id"],
                quick_scan_ids=request.quick_scan_ids,
                deep_dive_ids=request.deep_dive_ids,
                photo_session_ids=request.photo_session_ids,
                general_assessment_ids=request.general_assessment_ids,
                general_deep_dive_ids=request.general_deep_dive_ids
            )
        else:
            # Fallback to comprehensive data from time range
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

        system_prompt = """Generate a detailed endocrinology specialist report analyzing metabolic and hormonal symptoms.

CLINICAL SCALE CALCULATIONS:
1. Automatically calculate relevant standardized scales based on available data
2. For each scale, provide score, confidence, reasoning, and missing data

For Endocrinology, automatically calculate when relevant:
- FINDRISC (Finnish Diabetes Risk Score)
- Thyroid symptom scores
- ADAM questionnaire (for male hypogonadism)
- Cushingoid features assessment

BEST PRACTICES:
- Assess diabetes risk from weight, family history, activity
- Map symptoms to thyroid dysfunction (hyper/hypo)
- Consider hormonal patterns in symptom timing
- Note metabolic syndrome components

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive clinical overview for endocrinologist",
    "key_findings": ["significant metabolic/hormonal findings"],
    "patterns_identified": ["hormonal cycles, metabolic patterns"],
    "chief_complaints": ["primary endocrine concerns"],
    "action_items": ["immediate hormonal evaluations"],
    "specialist_focus": "endocrinology",
    "target_audience": "endocrinologist"
  },
  
  "clinical_summary": {
    "chief_complaint": "Primary endocrine concern",
    "hpi": "Detailed metabolic/hormonal history",
    "symptom_timeline": [
      {
        "date": "ISO date",
        "symptoms": "specific endocrine symptoms",
        "severity": 1-10,
        "timing": "relation to meals/time of day",
        "associated_factors": "stress, diet, sleep"
      }
    ]
  },
  
  "endocrinology_assessment": {
    "suspected_disorders": {
      "primary": "most likely endocrine disorder",
      "differential": ["other possibilities"],
      "confidence": "high/medium/low"
    },
    "metabolic_status": {
      "weight_trajectory": "gaining/stable/losing",
      "glucose_patterns": "if diabetic symptoms",
      "lipid_concerns": "based on history"
    },
    "hormonal_patterns": {
      "thyroid_symptoms": "hyper/hypo/mixed/none",
      "adrenal_symptoms": "if present",
      "reproductive_hormones": "if relevant"
    }
  },
  
  "diagnostic_priorities": {
    "immediate": [
      {
        "test": "specific hormone panels",
        "rationale": "clinical reasoning",
        "timing": "urgency level"
      }
    ],
    "comprehensive_workup": [
      "metabolic panel",
      "hormonal assessments",
      "imaging if indicated"
    ]
  },
  
  "treatment_recommendations": {
    "hormonal_therapy": {
      "indicated": "yes/no",
      "options": ["specific hormones if deficient"]
    },
    "metabolic_management": {
      "medications": ["if diabetes/lipids"],
      "lifestyle": "critical for endocrine health"
    },
    "monitoring": "hormone levels, metabolic markers"
  },
  
  "clinical_scales": {
    "FINDRISC": {
      "calculated": "score 0-26",
      "confidence": 0.0-1.0,
      "risk_category": "low/slightly elevated/moderate/high/very high",
      "10_year_diabetes_risk": "percentage",
      "reasoning": "How score components were assessed",
      "components": {
        "age": "points",
        "BMI": "points",
        "waist_circumference": "points",
        "physical_activity": "points",
        "vegetable_intake": "points",
        "hypertension_meds": "points",
        "high_glucose_history": "points",
        "family_history": "points"
      },
      "missing_data": ["specific measurements needed"]
    },
    "Thyroid_Symptom_Score": {
      "hyperthyroid_score": "0-10+",
      "hypothyroid_score": "0-10+",
      "predominant_pattern": "hyper/hypo/mixed/euthyroid",
      "confidence": 0.0-1.0,
      "key_symptoms": ["most significant thyroid symptoms"],
      "reasoning": "Based on symptom pattern"
    },
    "Metabolic_Syndrome_Components": {
      "components_present": "0-5",
      "meets_criteria": "yes/no (3+ components)",
      "identified": ["which components present"],
      "missing_assessment": ["labs needed for full assessment"]
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
        
        # Check if specific interactions are selected
        if request.quick_scan_ids or request.deep_dive_ids or request.photo_session_ids or request.general_assessment_ids or request.general_deep_dive_ids:
            # Gather only selected data
            all_data = await gather_selected_data(
                user_id=request.user_id or analysis["user_id"],
                quick_scan_ids=request.quick_scan_ids,
                deep_dive_ids=request.deep_dive_ids,
                photo_session_ids=request.photo_session_ids,
                general_assessment_ids=request.general_assessment_ids,
                general_deep_dive_ids=request.general_deep_dive_ids
            )
        else:
            # Fallback to comprehensive data from time range
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

        system_prompt = """Generate a detailed pulmonology specialist report analyzing respiratory symptoms and patterns.

CLINICAL SCALE CALCULATIONS:
1. Automatically calculate relevant standardized scales based on available data
2. For each scale, provide score, confidence, reasoning, and missing data

For Pulmonology, automatically calculate when relevant:
- CAT (COPD Assessment Test)
- mMRC Dyspnea Scale
- ACT (Asthma Control Test)
- STOP-BANG (for sleep apnea risk)
- Borg Scale for exertional dyspnea

BEST PRACTICES:
- Grade dyspnea based on functional limitations
- Assess control for asthma symptoms
- Screen for sleep apnea risk factors
- Evaluate impact on daily activities

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive clinical overview for pulmonologist",
    "key_findings": ["significant respiratory findings"],
    "patterns_identified": ["triggers, diurnal variation, seasonal patterns"],
    "chief_complaints": ["primary respiratory concerns"],
    "action_items": ["immediate pulmonary evaluations"],
    "specialist_focus": "pulmonology",
    "target_audience": "pulmonologist"
  },
  
  "clinical_summary": {
    "chief_complaint": "Primary respiratory concern",
    "hpi": "Detailed respiratory history with timeline",
    "symptom_timeline": [
      {
        "date": "ISO date",
        "symptoms": "specific respiratory symptoms",
        "severity": 1-10,
        "triggers": "identified precipitants",
        "relieving_factors": "what helps"
      }
    ]
  },
  
  "pulmonology_assessment": {
    "suspected_diagnosis": {
      "primary": "most likely pulmonary condition",
      "differential": ["other considerations"],
      "phenotype": "if asthma/COPD subtype"
    },
    "functional_assessment": {
      "exercise_tolerance": "specific limitations",
      "dyspnea_pattern": "at rest/exertion/nocturnal",
      "impact_on_adls": "specific activities affected"
    },
    "environmental_factors": {
      "exposures": ["smoking, occupational, allergens"],
      "home_environment": "triggers identified"
    }
  },
  
  "diagnostic_recommendations": {
    "pulmonary_function": {
      "spirometry": "pre/post bronchodilator",
      "dlco": "if indicated",
      "lung_volumes": "if restriction suspected"
    },
    "imaging": {
      "chest_xray": "baseline",
      "hrct": "if ILD or bronchiectasis suspected"
    },
    "other_tests": [
      "sleep study if OSA suspected",
      "methacholine challenge if asthma unclear"
    ]
  },
  
  "treatment_plan": {
    "pharmacotherapy": {
      "controller_medications": ["ICS/LABA, etc"],
      "rescue_medications": "SABA frequency",
      "add_on_therapy": "if needed"
    },
    "non_pharmacologic": {
      "pulmonary_rehab": "candidacy assessment",
      "oxygen_therapy": "if hypoxemia",
      "environmental_control": ["specific modifications"]
    }
  },
  
  "clinical_scales": {
    "mMRC_Dyspnea": {
      "grade": "0-4",
      "confidence": 0.0-1.0,
      "description": "specific functional limitation",
      "reasoning": "Based on activity tolerance described"
    },
    "CAT_Score": {
      "estimated_total": "0-40",
      "confidence": 0.0-1.0,
      "impact_level": "low/medium/high/very high",
      "reasoning": "How symptoms mapped to CAT items",
      "domains": {
        "cough": "0-5",
        "phlegm": "0-5",
        "chest_tightness": "0-5",
        "breathlessness": "0-5",
        "activity_limitation": "0-5",
        "confidence": "0-5",
        "sleep": "0-5",
        "energy": "0-5"
      }
    },
    "ACT_Score": {
      "estimated_total": "5-25",
      "control_level": "well controlled/not well controlled/very poorly controlled",
      "confidence": 0.0-1.0,
      "reasoning": "Based on symptom frequency and impact",
      "rescue_inhaler_use": "times per week"
    },
    "STOP_BANG": {
      "score": "0-8",
      "risk_category": "low/intermediate/high",
      "confidence": 0.0-1.0,
      "positive_factors": ["which risk factors present"],
      "reasoning": "How risk was assessed"
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

@router.post("/primary-care")
async def generate_primary_care_report(request: SpecialistReportRequest):
    """Generate comprehensive primary care/internal medicine report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Check if specific interactions are selected
        if request.quick_scan_ids or request.deep_dive_ids or request.photo_session_ids or request.general_assessment_ids or request.general_deep_dive_ids:
            # Gather only selected data
            all_data = await gather_selected_data(
                user_id=request.user_id or analysis["user_id"],
                quick_scan_ids=request.quick_scan_ids,
                deep_dive_ids=request.deep_dive_ids,
                photo_session_ids=request.photo_session_ids,
                general_assessment_ids=request.general_assessment_ids,
                general_deep_dive_ids=request.general_deep_dive_ids
            )
        else:
            # Fallback to comprehensive data from time range
            all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Build comprehensive primary care context
        context = f"""Generate a comprehensive primary care evaluation report.

PATIENT DATA:
Total Quick Scans: {len(all_data.get('quick_scans', []))}
Total Deep Dives: {len(all_data.get('deep_dives', []))}
Total Symptom Entries: {len(all_data.get('symptom_tracking', []))}

RECENT HEALTH CONCERNS (Last 10 entries):
{json.dumps([{
    'date': s['created_at'][:10],
    'symptoms': s.get('form_data', {}).get('symptoms'),
    'body_part': s.get('body_part'),
    'severity': s.get('form_data', {}).get('painLevel')
} for s in all_data['quick_scans'][-10:]], indent=2)}

SYMPTOM TRACKING PATTERNS:
{json.dumps([{
    'symptom': s.get('symptom_name'),
    'frequency': s.get('frequency'),
    'last_reported': s.get('created_at', '')[:10]
} for s in all_data['symptom_tracking'][-20:]], indent=2)}

TIME RANGE: {config['time_range']['start'][:10]} to {config['time_range']['end'][:10]}"""

        system_prompt = """Generate a comprehensive primary care report focusing on overall health assessment and coordination of care.

Return JSON format:
{
  "clinical_summary": {
    "chief_complaints": ["main health concerns"],
    "hpi": "comprehensive history of present illness",
    "review_of_systems": {
      "constitutional": ["fatigue", "weight changes", "fever"],
      "cardiovascular": ["chest pain", "palpitations"],
      "respiratory": ["cough", "dyspnea"],
      "gastrointestinal": ["abdominal pain", "bowel changes"],
      "genitourinary": ["urinary symptoms"],
      "musculoskeletal": ["joint pain", "stiffness"],
      "neurological": ["headaches", "dizziness"],
      "psychiatric": ["mood", "anxiety", "sleep"],
      "endocrine": ["energy", "temperature intolerance"],
      "dermatologic": ["rashes", "lesions"]
    }
  },
  
  "preventive_care_gaps": {
    "screening_due": ["colonoscopy", "mammogram", "etc based on age/sex"],
    "immunizations_needed": ["flu", "covid booster", "etc"],
    "health_maintenance": ["annual physical", "dental", "vision"]
  },
  
  "chronic_disease_assessment": {
    "identified_conditions": [
      {
        "condition": "condition name",
        "control_status": "well-controlled/poorly-controlled/needs assessment",
        "last_evaluation": "date or unknown",
        "management_gaps": ["what needs attention"]
      }
    ],
    "risk_factors": {
      "cardiovascular": ["identified risks"],
      "metabolic": ["weight, diet, exercise patterns"],
      "cancer": ["family history, lifestyle factors"]
    }
  },
  
  "medication_reconciliation": {
    "current_medications": ["if mentioned in reports"],
    "adherence_concerns": ["if any patterns noted"],
    "potential_interactions": ["to discuss with pharmacist"]
  },
  
  "specialist_coordination": {
    "current_specialists": ["based on report patterns"],
    "recommended_referrals": [
      {
        "specialty": "specialty name",
        "reason": "clinical indication",
        "urgency": "routine/urgent",
        "pre_referral_workup": ["tests to order first"]
      }
    ],
    "care_gaps": ["specialists needed but not yet seen"]
  },
  
  "diagnostic_plan": {
    "laboratory": [
      {
        "test": "CBC, CMP, Lipid panel",
        "rationale": "baseline/screening",
        "frequency": "annual/one-time"
      }
    ],
    "imaging": ["if indicated by symptoms"],
    "screening": ["age-appropriate cancer screening"]
  },
  
  "health_optimization": {
    "lifestyle_counseling": {
      "diet": ["specific recommendations"],
      "exercise": ["realistic goals"],
      "sleep": ["hygiene tips if issues noted"],
      "stress": ["management strategies"]
    },
    "behavioral_health": {
      "mood_screening": "PHQ-9 recommended if symptoms",
      "substance_use": "screening indicated",
      "support_resources": ["if needed"]
    }
  },
  
  "care_plan_summary": {
    "immediate_actions": ["urgent items"],
    "short_term_goals": ["1-3 month targets"],
    "long_term_goals": ["6-12 month targets"],
    "follow_up_schedule": {
      "next_visit": "recommended timing",
      "monitoring_plan": "for chronic conditions"
    }
  },
  
  "patient_engagement": {
    "strengths": ["good tracking, seeking care, etc"],
    "barriers": ["identified challenges"],
    "education_priorities": ["key topics to address"]
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="google/gemini-2.0-flash-exp:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "clinical_summary": {
                    "chief_complaints": ["Unable to generate report"],
                    "hpi": "Report generation failed. Please retry."
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "primary_care", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "primary_care",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating primary care report: {e}")
        return {"error": str(e), "status": "error"}