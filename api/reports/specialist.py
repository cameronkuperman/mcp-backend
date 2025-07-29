"""Specialist Report API endpoints (8 specialty-specific reports)"""
from fastapi import APIRouter
from datetime import datetime, timezone
import json
import uuid

from models.requests import SpecialistReportRequest, SpecialtyTriageRequest
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

@router.post("/specialty-triage")
async def triage_specialty(request: SpecialtyTriageRequest):
    """AI determines which specialist(s) are needed based on symptoms"""
    try:
        # Gather user data
        data = await gather_report_data(request.user_id, {"time_range": {"start": "2020-01-01"}})
        
        # Build context for triage
        context = f"""Analyze patient data to determine appropriate specialist referral.

Recent Symptoms:
{json.dumps([{
    'date': s['created_at'][:10],
    'symptoms': s.get('form_data', {}).get('symptoms', ''),
    'body_part': s.get('body_part', ''),
    'severity': s.get('form_data', {}).get('painLevel', 0)
} for s in data['quick_scans'][-10:]], indent=2)}

Symptom Tracking:
{json.dumps([{
    'symptom': s.get('symptom_name'),
    'frequency': s.get('frequency'),
    'severity': s.get('severity')
} for s in data['symptom_tracking'][-20:]], indent=2)}

Patient Concern: {request.primary_concern}"""

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

        system_prompt = """Generate a detailed cardiology specialist report analyzing the patient's cardiac symptoms and history.

Return JSON format:
{
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

        system_prompt = """Generate a detailed neurology specialist report focusing on neurological symptoms and patterns.

Return JSON format:
{
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
    "clinical_scales": {
      "midas_score": {
        "calculated": "score if data available",
        "grade": "I-IV disability level",
        "breakdown": {
          "missed_work": "days",
          "reduced_productivity": "days",
          "household_impact": "days",
          "social_impact": "days"
        }
      },
      "functional_impact": {
        "work_days_affected": "number in past 3 months",
        "emergency_visits": "if any",
        "quality_of_life": "specific impacts noted"
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

        system_prompt = """Generate a detailed psychiatry specialist report analyzing mental health symptoms and psychosocial factors.

Return JSON format:
{
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
    "standardized_assessments": {
      "phq9_score": {
        "total": "calculated from symptoms",
        "interpretation": "severity level",
        "item_9": "suicide item score",
        "functional_impact": "last question score"
      },
      "gad7_estimate": "if anxiety symptoms present",
      "other_scales": "as indicated by symptoms"
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

        system_prompt = """Generate a detailed dermatology specialist report analyzing skin conditions with photo documentation insights.

Return JSON format:
{
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

@router.post("/primary-care")
async def generate_primary_care_report(request: SpecialistReportRequest):
    """Generate comprehensive primary care/internal medicine report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
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