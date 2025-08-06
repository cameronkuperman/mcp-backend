"""Extended Specialist Report API endpoints (additional specialties)"""
from fastapi import APIRouter
from datetime import datetime, timezone
import json
import uuid
import logging

from models.requests import SpecialistReportRequest
from business_logic import call_llm
from utils.json_parser import extract_json_from_response
from utils.data_gathering import (
    gather_comprehensive_data,
    gather_selected_data,
    safe_insert_report
)

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/report", tags=["reports-specialist-extended"])

async def load_analysis(analysis_id: str):
    """Load analysis from database"""
    from supabase_client import supabase
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
        "model_used": "google/gemini-2.5-flash",
        "specialty": specialty
    }
    
    await safe_insert_report(report_record)

@router.post("/nephrology")
async def generate_nephrology_report(request: SpecialistReportRequest):
    """Generate nephrology specialist report"""
    try:
        # Log incoming request data
        logger.info(f"[NEPHROLOGY] Incoming request - quick_scan_ids: {request.quick_scan_ids}, "
                    f"deep_dive_ids: {request.deep_dive_ids}, photo_session_ids: {request.photo_session_ids}")
        
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # ALWAYS use selected data mode for specialist reports
        # Convert None to empty arrays to ensure we don't load unwanted data
        all_data = await gather_selected_data(
            user_id=request.user_id or analysis["user_id"],
            quick_scan_ids=request.quick_scan_ids if request.quick_scan_ids is not None else [],
            deep_dive_ids=request.deep_dive_ids if request.deep_dive_ids is not None else [],
            photo_session_ids=request.photo_session_ids if request.photo_session_ids is not None else [],
            general_assessment_ids=request.general_assessment_ids if request.general_assessment_ids is not None else [],
            general_deep_dive_ids=request.general_deep_dive_ids if request.general_deep_dive_ids is not None else []
        )
        
        # Log data counts
        logger.info(f"[NEPHROLOGY] Data gathered - quick_scans: {len(all_data.get('quick_scans', []))}, "
                    f"deep_dives: {len(all_data.get('deep_dives', []))}, "
                    f"photo_sessions: {len(all_data.get('photo_sessions', []))}")
        
        # Build nephrology context with FULL data
        context = f"""Generate a comprehensive nephrology report.

PATIENT DATA (Selected Interactions Only):
{json.dumps(all_data, indent=2)}"""

        system_prompt = """Generate a detailed nephrology specialist report analyzing kidney function and related conditions.

CLINICAL SCALE CALCULATIONS:
Automatically calculate when relevant:
- CKD-EPI eGFR estimation
- KDIGO CKD staging (G1-G5, A1-A3)
- Kidney Failure Risk Equation (if CKD)
- Volume status assessment

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive clinical overview for nephrologist",
    "key_findings": ["most significant renal findings"],
    "patterns_identified": ["acute vs chronic patterns"],
    "chief_complaints": ["primary renal concerns"],
    "action_items": ["immediate evaluations needed"],
    "specialist_focus": "nephrology",
    "target_audience": "nephrologist"
  },
  
  "clinical_summary": {
    "chief_complaint": "Primary renal concern",
    "hpi": "Detailed history focusing on kidney-related symptoms",
    "risk_factors": ["hypertension", "diabetes", "family history", "medications"]
  },
  
  "nephrology_assessment": {
    "renal_symptoms": {
      "urinary_changes": ["frequency", "color", "volume", "foaming"],
      "edema": ["location", "pitting", "progression"],
      "systemic": ["fatigue", "nausea", "pruritus"]
    },
    "blood_pressure": {
      "control": "controlled/uncontrolled",
      "medications": ["current antihypertensives"],
      "target": "based on comorbidities"
    },
    "volume_status": {
      "assessment": "euvolemic/hypervolemic/hypovolemic",
      "clinical_signs": ["edema", "JVP", "weight changes"]
    }
  },
  
  "diagnostic_recommendations": {
    "laboratory": {
      "immediate": [
        {"test": "BUN, creatinine, eGFR", "rationale": "kidney function"},
        {"test": "Urinalysis with microscopy", "rationale": "proteinuria, hematuria"},
        {"test": "Urine protein/creatinine ratio", "rationale": "quantify proteinuria"}
      ],
      "additional": [
        {"test": "Renal ultrasound", "indication": "size, obstruction"},
        {"test": "24-hour urine", "indication": "if needed for clearance"}
      ]
    }
  },
  
  "treatment_recommendations": {
    "ckd_management": {
      "blood_pressure": {"target": "<130/80", "medications": "ACE/ARB preferred"},
      "proteinuria": {"target": "reduce by 30-50%", "interventions": ["ACE/ARB", "SGLT2i"]},
      "mineral_bone": {"phosphate_control": "diet/binders", "vitamin_d": "if deficient"}
    },
    "acute_issues": {
      "volume": "diuretic adjustment if needed",
      "electrolytes": "specific corrections",
      "uremia": "dialysis planning if advanced"
    },
    "lifestyle": {
      "diet": ["sodium restriction", "protein moderation", "potassium as indicated"],
      "fluid": "restriction if volume overload",
      "nephrotoxins": ["avoid NSAIDs", "contrast precautions"]
    }
  },
  
  "clinical_scales": {
    "CKD_Staging": {
      "estimated_gfr": "mL/min/1.73m²",
      "ckd_stage": "G1-G5",
      "albuminuria_category": "A1-A3",
      "confidence": 0.0-1.0,
      "reasoning": "Based on symptoms and risk factors",
      "prognosis": "risk of progression"
    },
    "Volume_Assessment": {
      "status": "euvolemic/hypervolemic/hypovolemic",
      "confidence": 0.0-1.0,
      "clinical_basis": ["edema", "BP", "symptoms"]
    }
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="google/gemini-2.5-flash",
            temperature=0.3,
            max_tokens=3000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Nephrology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "nephrology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "nephrology",
            "specialty": "nephrology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating nephrology report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/urology")
async def generate_urology_report(request: SpecialistReportRequest):
    """Generate urology specialist report"""
    try:
        # Log incoming request data
        logger.info(f"[UROLOGY] Incoming request - quick_scan_ids: {request.quick_scan_ids}, "
                    f"deep_dive_ids: {request.deep_dive_ids}, photo_session_ids: {request.photo_session_ids}")
        
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # ALWAYS use selected data mode for specialist reports
        # Convert None to empty arrays to ensure we don't load unwanted data
        all_data = await gather_selected_data(
            user_id=request.user_id or analysis["user_id"],
            quick_scan_ids=request.quick_scan_ids if request.quick_scan_ids is not None else [],
            deep_dive_ids=request.deep_dive_ids if request.deep_dive_ids is not None else [],
            photo_session_ids=request.photo_session_ids if request.photo_session_ids is not None else [],
            general_assessment_ids=request.general_assessment_ids if request.general_assessment_ids is not None else [],
            general_deep_dive_ids=request.general_deep_dive_ids if request.general_deep_dive_ids is not None else []
        )
        
        # Log data counts
        logger.info(f"[UROLOGY] Data gathered - quick_scans: {len(all_data.get('quick_scans', []))}, "
                    f"deep_dives: {len(all_data.get('deep_dives', []))}, "
                    f"photo_sessions: {len(all_data.get('photo_sessions', []))}")
        
        # Build urology context with FULL data
        context = f"""Generate a comprehensive urology report.

PATIENT DATA (Selected Interactions Only):
{json.dumps(all_data, indent=2)}"""

        system_prompt = """Generate a detailed urology specialist report analyzing urinary and male reproductive symptoms.

CLINICAL SCALE CALCULATIONS:
Automatically calculate when relevant:
- IPSS (International Prostate Symptom Score)
- AUA Symptom Score
- SHIM (Sexual Health Inventory for Men) if applicable
- NIH-CPSI for chronic prostatitis

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive clinical overview for urologist",
    "key_findings": ["most significant urologic findings"],
    "patterns_identified": ["obstructive vs irritative patterns"],
    "chief_complaints": ["primary urologic concerns"],
    "action_items": ["immediate evaluations needed"],
    "specialist_focus": "urology",
    "target_audience": "urologist"
  },
  
  "clinical_summary": {
    "chief_complaint": "Primary urologic concern",
    "hpi": "Detailed history of urinary/reproductive symptoms",
    "review_of_systems": {
      "lower_urinary_tract": ["frequency", "urgency", "nocturia", "stream"],
      "pain": ["location", "character", "timing"],
      "sexual_function": ["if relevant to complaint"]
    }
  },
  
  "urology_assessment": {
    "luts_characterization": {
      "storage_symptoms": ["frequency", "urgency", "nocturia"],
      "voiding_symptoms": ["hesitancy", "weak stream", "straining", "intermittency"],
      "post_micturition": ["incomplete emptying", "dribbling"]
    },
    "pain_assessment": {
      "location": ["suprapubic", "perineal", "testicular", "penile"],
      "timing": "with voiding/ejaculation/constant",
      "severity": "0-10 scale"
    },
    "sexual_function": {
      "erectile_function": "if applicable",
      "ejaculatory_function": "if applicable",
      "libido": "changes noted"
    }
  },
  
  "diagnostic_recommendations": {
    "laboratory": [
      {"test": "Urinalysis and culture", "rationale": "infection, hematuria"},
      {"test": "PSA", "indication": "if male >50 or symptoms"},
      {"test": "Creatinine", "rationale": "renal function"}
    ],
    "imaging": [
      {"test": "Renal/bladder ultrasound", "indication": "obstruction, stones"},
      {"test": "Post-void residual", "indication": "retention assessment"}
    ],
    "specialized": [
      {"test": "Uroflowmetry", "indication": "objective flow assessment"},
      {"test": "Cystoscopy", "indication": "if hematuria or suspicious symptoms"}
    ]
  },
  
  "treatment_recommendations": {
    "medical_therapy": {
      "alpha_blockers": {"indication": "BPH symptoms", "options": ["tamsulosin", "alfuzosin"]},
      "5ari": {"indication": "large prostate", "options": ["finasteride", "dutasteride"]},
      "anticholinergics": {"indication": "overactive bladder", "cautions": "retention risk"}
    },
    "behavioral": {
      "fluid_management": "timing and volume",
      "bladder_training": "if urgency/frequency",
      "pelvic_floor": "exercises if indicated"
    },
    "surgical_options": {
      "indications": ["failed medical therapy", "retention", "complications"],
      "procedures": ["based on pathology"]
    }
  },
  
  "clinical_scales": {
    "IPSS": {
      "total_score": "0-35",
      "severity": "mild/moderate/severe",
      "confidence": 0.0-1.0,
      "symptom_breakdown": {
        "incomplete_emptying": 0-5,
        "frequency": 0-5,
        "intermittency": 0-5,
        "urgency": 0-5,
        "weak_stream": 0-5,
        "straining": 0-5,
        "nocturia": "times per night"
      },
      "qol_score": "0-6",
      "reasoning": "How symptoms were mapped to scores"
    },
    "Bladder_Diary": {
      "daytime_frequency": "voids per day",
      "nocturia": "times per night",
      "urgency_episodes": "per day",
      "incontinence": "episodes if any"
    }
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="google/gemini-2.5-flash",
            temperature=0.3,
            max_tokens=3000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Urology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "urology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "urology",
            "specialty": "urology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating urology report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/gynecology")
async def generate_gynecology_report(request: SpecialistReportRequest):
    """Generate gynecology specialist report"""
    try:
        # Log incoming request data
        logger.info(f"[GYNECOLOGY] Incoming request - quick_scan_ids: {request.quick_scan_ids}, "
                    f"deep_dive_ids: {request.deep_dive_ids}, photo_session_ids: {request.photo_session_ids}")
        
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # ALWAYS use selected data mode for specialist reports
        # Convert None to empty arrays to ensure we don't load unwanted data
        all_data = await gather_selected_data(
            user_id=request.user_id or analysis["user_id"],
            quick_scan_ids=request.quick_scan_ids if request.quick_scan_ids is not None else [],
            deep_dive_ids=request.deep_dive_ids if request.deep_dive_ids is not None else [],
            photo_session_ids=request.photo_session_ids if request.photo_session_ids is not None else [],
            general_assessment_ids=request.general_assessment_ids if request.general_assessment_ids is not None else [],
            general_deep_dive_ids=request.general_deep_dive_ids if request.general_deep_dive_ids is not None else []
        )
        
        # Log data counts
        logger.info(f"[GYNECOLOGY] Data gathered - quick_scans: {len(all_data.get('quick_scans', []))}, "
                    f"deep_dives: {len(all_data.get('deep_dives', []))}, "
                    f"photo_sessions: {len(all_data.get('photo_sessions', []))}")
        
        # Build gynecology context with FULL data
        context = f"""Generate a comprehensive gynecology report.

PATIENT DATA (Selected Interactions Only):
{json.dumps(all_data, indent=2)}"""

        system_prompt = """Generate a detailed gynecology specialist report analyzing women's health concerns.

CLINICAL SCALE CALCULATIONS:
Automatically calculate when relevant:
- Menstrual pattern assessment (regular/irregular)
- PCOS diagnostic criteria
- Menopausal symptom severity
- Pelvic pain assessment scales

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive clinical overview for gynecologist",
    "key_findings": ["most significant gynecologic findings"],
    "patterns_identified": ["menstrual patterns, hormonal symptoms"],
    "chief_complaints": ["primary gynecologic concerns"],
    "action_items": ["immediate evaluations needed"],
    "specialist_focus": "gynecology",
    "target_audience": "gynecologist"
  },
  
  "clinical_summary": {
    "chief_complaint": "Primary gynecologic concern",
    "hpi": "Detailed gynecologic history",
    "menstrual_history": {
      "lmp": "last menstrual period",
      "cycle_length": "days between periods",
      "cycle_regularity": "regular/irregular",
      "flow": "light/moderate/heavy",
      "duration": "days of bleeding"
    },
    "obstetric_history": {
      "gravidity": "number of pregnancies",
      "parity": "number of births",
      "pregnancy_complications": ["if any"]
    }
  },
  
  "gynecologic_assessment": {
    "menstrual_abnormalities": {
      "pattern": "regular/irregular/absent",
      "abnormal_bleeding": ["intermenstrual", "postcoital", "postmenopausal"],
      "dysmenorrhea": "severity and impact"
    },
    "pelvic_symptoms": {
      "pain": ["location", "timing", "character"],
      "pressure": "pelvic pressure symptoms",
      "discharge": "abnormal discharge characteristics"
    },
    "hormonal_symptoms": {
      "vasomotor": ["hot flashes", "night sweats"],
      "mood": ["PMS", "PMDD symptoms"],
      "other": ["acne", "hirsutism", "weight changes"]
    },
    "sexual_health": {
      "dyspareunia": "if present",
      "libido_changes": "if reported",
      "contraception": "current method and satisfaction"
    }
  },
  
  "diagnostic_recommendations": {
    "laboratory": [
      {"test": "CBC", "indication": "if heavy bleeding"},
      {"test": "TSH, prolactin", "indication": "menstrual irregularity"},
      {"test": "FSH, LH, estradiol", "indication": "hormonal assessment"},
      {"test": "Testosterone, DHEAS", "indication": "if PCOS suspected"}
    ],
    "imaging": [
      {"test": "Pelvic ultrasound", "indication": "structural abnormalities"},
      {"test": "Saline sonogram", "indication": "if endometrial pathology"}
    ],
    "procedures": [
      {"test": "Endometrial biopsy", "indication": "abnormal bleeding >45yo"},
      {"test": "Hysteroscopy", "indication": "persistent abnormal bleeding"}
    ]
  },
  
  "treatment_recommendations": {
    "menstrual_management": {
      "hormonal": ["OCPs", "IUD", "other hormonal options"],
      "non_hormonal": ["NSAIDs", "tranexamic acid"],
      "procedural": ["endometrial ablation if indicated"]
    },
    "fertility_considerations": {
      "current_desires": "trying to conceive/contraception/not applicable",
      "fertility_preservation": "if treatment may impact"
    },
    "menopausal_management": {
      "hrt_consideration": "benefits vs risks",
      "non_hormonal": ["SSRIs for hot flashes", "vaginal moisturizers"],
      "bone_health": "calcium, vitamin D, DEXA screening"
    }
  },
  
  "preventive_care": {
    "screening_due": [
      {"test": "Pap smear", "due_date": "based on guidelines"},
      {"test": "HPV testing", "indication": "age-appropriate"},
      {"test": "Mammogram", "timing": "based on age/risk"},
      {"test": "Bone density", "indication": "postmenopausal"}
    ]
  },
  
  "clinical_assessment": {
    "Menstrual_Pattern": {
      "classification": "regular/irregular/amenorrhea",
      "cycle_length": "21-35 days normal",
      "variability": "days of variation",
      "confidence": 0.0-1.0,
      "abnormalities": ["specific patterns identified"]
    },
    "PCOS_Criteria": {
      "rotterdam_criteria_met": "0-3 criteria",
      "features": {
        "oligo_anovulation": "present/absent",
        "hyperandrogenism": "clinical/biochemical",
        "pco_morphology": "if ultrasound done"
      },
      "confidence": 0.0-1.0,
      "additional_workup": ["tests needed for diagnosis"]
    },
    "Bleeding_Assessment": {
      "pattern": "type of abnormal bleeding",
      "severity": "impact on hemoglobin/QOL",
      "etiology": "likely cause based on age/pattern",
      "evaluation_needed": ["specific tests indicated"]
    }
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="google/gemini-2.5-flash",
            temperature=0.3,
            max_tokens=3000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Gynecology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "gynecology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "gynecology",
            "specialty": "gynecology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating gynecology report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/oncology")
async def generate_oncology_report(request: SpecialistReportRequest):
    """Generate oncology specialist report"""
    try:
        # Log incoming request data
        logger.info(f"[ONCOLOGY] Incoming request - quick_scan_ids: {request.quick_scan_ids}, "
                    f"deep_dive_ids: {request.deep_dive_ids}, photo_session_ids: {request.photo_session_ids}")
        
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # ALWAYS use selected data mode for specialist reports
        # Convert None to empty arrays to ensure we don't load unwanted data
        all_data = await gather_selected_data(
            user_id=request.user_id or analysis["user_id"],
            quick_scan_ids=request.quick_scan_ids if request.quick_scan_ids is not None else [],
            deep_dive_ids=request.deep_dive_ids if request.deep_dive_ids is not None else [],
            photo_session_ids=request.photo_session_ids if request.photo_session_ids is not None else [],
            general_assessment_ids=request.general_assessment_ids if request.general_assessment_ids is not None else [],
            general_deep_dive_ids=request.general_deep_dive_ids if request.general_deep_dive_ids is not None else []
        )
        
        # Log data counts
        logger.info(f"[ONCOLOGY] Data gathered - quick_scans: {len(all_data.get('quick_scans', []))}, "
                    f"deep_dives: {len(all_data.get('deep_dives', []))}, "
                    f"photo_sessions: {len(all_data.get('photo_sessions', []))}")
        
        # Build oncology context with FULL data
        context = f"""Generate a comprehensive oncology report.

PATIENT DATA (Selected Interactions Only):
{json.dumps(all_data, indent=2)}"""

        system_prompt = """Generate a detailed oncology specialist report analyzing cancer-related symptoms and screening needs.

CLINICAL SCALE CALCULATIONS:
Automatically calculate when relevant:
- Performance status (ECOG/Karnofsky)
- Constitutional symptom assessment
- Cancer screening risk scores
- Symptom burden scales

Return JSON format with focus on:
1. Constitutional symptoms (weight loss, fatigue, night sweats)
2. Localized symptoms suggesting malignancy
3. Family history and genetic risk
4. Age-appropriate screening recommendations
5. Red flags requiring urgent evaluation

Include sections for:
- Executive summary for oncologist
- Symptom analysis and timeline
- Risk factor assessment
- Screening recommendations
- Diagnostic workup priorities
- Clinical scales with confidence levels"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="google/gemini-2.5-flash",
            temperature=0.3,
            max_tokens=3000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Oncology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "oncology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "oncology",
            "specialty": "oncology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating oncology report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/physical-therapy")
async def generate_physical_therapy_report(request: SpecialistReportRequest):
    """Generate physical therapy report"""
    try:
        # Log incoming request data
        logger.info(f"[PHYSICAL-THERAPY] Incoming request - quick_scan_ids: {request.quick_scan_ids}, "
                    f"deep_dive_ids: {request.deep_dive_ids}, photo_session_ids: {request.photo_session_ids}")
        
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # ALWAYS use selected data mode for specialist reports
        # Convert None to empty arrays to ensure we don't load unwanted data
        all_data = await gather_selected_data(
            user_id=request.user_id or analysis["user_id"],
            quick_scan_ids=request.quick_scan_ids if request.quick_scan_ids is not None else [],
            deep_dive_ids=request.deep_dive_ids if request.deep_dive_ids is not None else [],
            photo_session_ids=request.photo_session_ids if request.photo_session_ids is not None else [],
            general_assessment_ids=request.general_assessment_ids if request.general_assessment_ids is not None else [],
            general_deep_dive_ids=request.general_deep_dive_ids if request.general_deep_dive_ids is not None else []
        )
        
        # Log data counts
        logger.info(f"[PHYSICAL-THERAPY] Data gathered - quick_scans: {len(all_data.get('quick_scans', []))}, "
                    f"deep_dives: {len(all_data.get('deep_dives', []))}, "
                    f"photo_sessions: {len(all_data.get('photo_sessions', []))}")
        
        # Build PT context with FULL data
        context = f"""Generate a comprehensive physical therapy evaluation report.

PATIENT DATA (Selected Interactions Only):
{json.dumps(all_data, indent=2)}"""

        system_prompt = """Generate a detailed physical therapy evaluation report focusing on functional limitations and rehabilitation needs.

CLINICAL SCALE CALCULATIONS:
Automatically calculate when relevant:
- Functional outcome measures (based on activities reported)
- Pain and disability scales
- Balance and fall risk assessment
- Activity limitation scales

Return JSON format with focus on:
1. Functional limitations and impact on daily activities
2. Movement patterns and compensations
3. Pain patterns with movement
4. Strength and flexibility deficits (inferred)
5. Goals for therapy

Include sections for:
- Executive summary for PT
- Functional assessment
- Movement analysis
- Treatment plan with specific exercises
- Expected outcomes and timeline
- Home exercise program recommendations"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="google/gemini-2.5-flash",
            temperature=0.3,
            max_tokens=3000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Physical therapy report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "physical_therapy", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "physical_therapy",
            "specialty": "physical_therapy",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating physical therapy report: {e}")
        return {"error": str(e), "status": "error"}