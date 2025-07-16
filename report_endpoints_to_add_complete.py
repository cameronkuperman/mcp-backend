# Complete Report Endpoints to Add to run_oracle.py

# 1. First, add these imports at the top of run_oracle.py (if not already present):
from sqlalchemy import desc  # Add this if not present

# 2. Add these Pydantic models after the existing models (around line 100-200):

class SpecialistReportRequest(BaseModel):
    analysis_id: str
    user_id: Optional[str] = None
    specialty: Optional[str] = None

class TimePeriodReportRequest(BaseModel):
    user_id: str
    include_wearables: Optional[bool] = False

class DoctorNotesRequest(BaseModel):
    doctor_npi: str
    specialty: str
    notes: str
    sections_reviewed: List[str]
    diagnosis: Optional[str] = None
    plan_modifications: Optional[Dict[str, Any]] = None
    follow_up_instructions: Optional[str] = None

class ShareReportRequest(BaseModel):
    shared_by_npi: str
    recipient_npi: str
    access_level: str = "read_only"  # read_only, full_access
    expiration_days: int = 30
    notes: Optional[str] = None
    base_url: str

class RateReportRequest(BaseModel):
    doctor_npi: str
    usefulness_score: int  # 1-5
    accuracy_score: int    # 1-5
    time_saved: int       # minutes
    would_recommend: bool
    feedback: Optional[str] = None

# 3. Add these helper functions after existing helpers (around line 600):

async def load_analysis(analysis_id: str):
    """Load analysis from database"""
    response = supabase.table("report_analyses")\
        .select("*")\
        .eq("id", analysis_id)\
        .execute()
    
    if not response.data:
        raise ValueError("Analysis not found")
    
    return response.data[0]

async def gather_comprehensive_data(user_id: str, config: dict):
    """Gather ALL available data for time-based reports"""
    time_range = config.get("time_range", {})
    
    # Quick Scans
    scans = supabase.table("quick_scans")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    # Deep Dives
    dives = supabase.table("deep_dive_sessions")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("status", "completed")\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    # Symptom Tracking
    tracking = supabase.table("symptom_tracking")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    # Long-term tracking data
    tracking_configs = supabase.table("tracking_configurations")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("status", "approved")\
        .execute()
    
    tracking_data = []
    for config_item in (tracking_configs.data or []):
        points = supabase.table("tracking_data_points")\
            .select("*")\
            .eq("configuration_id", config_item["id"])\
            .gte("recorded_at", time_range.get("start", "2020-01-01"))\
            .lte("recorded_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
            .order("recorded_at")\
            .execute()
        
        if points.data:
            tracking_data.append({
                "metric": config_item["metric_name"],
                "data_points": points.data
            })
    
    # LLM Chat Summaries
    chats = supabase.table("oracle_chats")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    return {
        "quick_scans": scans.data or [],
        "deep_dives": dives.data or [],
        "symptom_tracking": tracking.data or [],
        "tracking_data": tracking_data,
        "llm_summaries": chats.data or [],
        "wearables": {}  # Placeholder for wearables integration
    }

async def extract_cardiac_patterns(data: dict) -> str:
    """Extract cardiac-specific patterns from data"""
    cardiac_symptoms = ["chest pain", "palpitations", "shortness of breath", "dizziness", "heart"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(symptom in form_data_str for symptom in cardiac_symptoms):
            relevant_data.append({
                "date": scan["created_at"],
                "symptoms": scan.get("form_data", {}).get("symptoms"),
                "severity": scan.get("form_data", {}).get("painLevel"),
                "analysis": scan.get("analysis_result", {})
            })
    
    for dive in data.get("deep_dives", []):
        dive_str = str(dive).lower()
        if any(symptom in dive_str for symptom in cardiac_symptoms):
            relevant_data.append({
                "date": dive["created_at"],
                "body_part": dive["body_part"],
                "final_analysis": dive.get("final_analysis", {})
            })
    
    return f"Cardiac-specific data found: {len(relevant_data)} relevant entries\n" + json.dumps(relevant_data, indent=2)

async def extract_neuro_patterns(data: dict) -> str:
    """Extract neurology-specific patterns from data"""
    neuro_symptoms = ["headache", "migraine", "dizziness", "numbness", "tingling", "vision"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(symptom in form_data_str for symptom in neuro_symptoms):
            relevant_data.append({
                "date": scan["created_at"],
                "symptoms": scan.get("form_data", {}).get("symptoms"),
                "severity": scan.get("form_data", {}).get("painLevel"),
                "analysis": scan.get("analysis_result", {})
            })
    
    return f"Neurological data found: {len(relevant_data)} relevant entries\n" + json.dumps(relevant_data, indent=2)

async def extract_mental_health_patterns(data: dict) -> str:
    """Extract mental health patterns from data"""
    psych_keywords = ["anxiety", "depression", "stress", "mood", "sleep", "panic", "worry"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in psych_keywords):
            relevant_data.append({
                "date": scan["created_at"],
                "symptoms": scan.get("form_data", {}).get("symptoms"),
                "analysis": scan.get("analysis_result", {})
            })
    
    return f"Mental health data found: {len(relevant_data)} relevant entries\n" + json.dumps(relevant_data, indent=2)

async def extract_dermatology_patterns(data: dict, photo_data: dict) -> str:
    """Extract dermatology patterns including photo data"""
    derm_keywords = ["rash", "skin", "itching", "lesion", "mole", "spot"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in derm_keywords):
            relevant_data.append(scan)
    
    return f"Dermatology data found: {len(relevant_data)} text entries, {len(photo_data)} photos\n" + json.dumps(relevant_data[:5], indent=2)

async def extract_gi_patterns(data: dict) -> str:
    """Extract GI patterns from data"""
    gi_keywords = ["stomach", "abdominal", "nausea", "diarrhea", "constipation", "bloating"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in gi_keywords):
            relevant_data.append(scan)
    
    return f"GI data found: {len(relevant_data)} relevant entries\n" + json.dumps(relevant_data[:10], indent=2)

async def extract_endocrine_patterns(data: dict) -> str:
    """Extract endocrine patterns from data"""
    endo_keywords = ["fatigue", "weight", "thyroid", "diabetes", "energy", "temperature"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in endo_keywords):
            relevant_data.append(scan)
    
    return f"Endocrine data found: {len(relevant_data)} relevant entries\n" + json.dumps(relevant_data[:10], indent=2)

async def extract_pulmonary_patterns(data: dict) -> str:
    """Extract pulmonary patterns from data"""
    pulm_keywords = ["breathing", "cough", "wheeze", "asthma", "shortness", "chest"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in pulm_keywords):
            relevant_data.append(scan)
    
    return f"Pulmonary data found: {len(relevant_data)} relevant entries\n" + json.dumps(relevant_data[:10], indent=2)

async def gather_photo_data(user_id: str, config: dict):
    """Placeholder for photo data gathering"""
    # This would integrate with your photo storage system
    return []

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

async def group_data_by_month(all_data: dict):
    """Group health data by month for annual reports"""
    monthly_data = {}
    
    for scan in all_data.get("quick_scans", []):
        month = scan["created_at"][:7]  # YYYY-MM
        if month not in monthly_data:
            monthly_data[month] = {"quick_scans": 0, "deep_dives": 0, "symptoms": {}, "total_interactions": 0}
        monthly_data[month]["quick_scans"] += 1
        
        # Count symptoms
        symptoms = scan.get("form_data", {}).get("symptoms", "")
        if symptoms:
            if symptoms not in monthly_data[month]["symptoms"]:
                monthly_data[month]["symptoms"][symptoms] = 0
            monthly_data[month]["symptoms"][symptoms] += 1
    
    for dive in all_data.get("deep_dives", []):
        month = dive["created_at"][:7]
        if month not in monthly_data:
            monthly_data[month] = {"quick_scans": 0, "deep_dives": 0, "symptoms": {}, "total_interactions": 0}
        monthly_data[month]["deep_dives"] += 1
    
    # Calculate totals
    for month in monthly_data:
        monthly_data[month]["total_interactions"] = (
            monthly_data[month]["quick_scans"] + 
            monthly_data[month]["deep_dives"]
        )
    
    return monthly_data

def count_symptoms_by_frequency(all_data: dict):
    """Count symptom frequency across all data"""
    symptom_counts = {}
    
    for scan in all_data.get("quick_scans", []):
        symptoms = scan.get("form_data", {}).get("symptoms", "")
        if symptoms:
            if symptoms not in symptom_counts:
                symptom_counts[symptoms] = {"count": 0, "severity_sum": 0}
            symptom_counts[symptoms]["count"] += 1
            severity = scan.get("form_data", {}).get("painLevel", 5)
            symptom_counts[symptoms]["severity_sum"] += severity
    
    # Calculate averages
    result = []
    for symptom, data in symptom_counts.items():
        result.append({
            "symptom": symptom,
            "frequency": data["count"],
            "average_severity": round(data["severity_sum"] / data["count"], 1)
        })
    
    return sorted(result, key=lambda x: x["frequency"], reverse=True)

def analyze_seasonal_patterns(all_data: dict):
    """Analyze seasonal patterns in health data"""
    seasonal_data = {
        "winter": {"months": ["12", "01", "02"], "symptoms": {}},
        "spring": {"months": ["03", "04", "05"], "symptoms": {}},
        "summer": {"months": ["06", "07", "08"], "symptoms": {}},
        "fall": {"months": ["09", "10", "11"], "symptoms": {}}
    }
    
    for scan in all_data.get("quick_scans", []):
        month = scan["created_at"][5:7]  # MM
        symptoms = scan.get("form_data", {}).get("symptoms", "")
        
        for season, data in seasonal_data.items():
            if month in data["months"] and symptoms:
                if symptoms not in data["symptoms"]:
                    data["symptoms"][symptoms] = 0
                data["symptoms"][symptoms] += 1
    
    # Get top symptoms per season
    result = {}
    for season, data in seasonal_data.items():
        top_symptoms = sorted(data["symptoms"].items(), key=lambda x: x[1], reverse=True)[:3]
        result[season] = [s[0] for s in top_symptoms]
    
    return result

async def get_average_rating(report_id: str, field: str):
    """Get average rating for a report"""
    response = supabase.table("report_ratings")\
        .select(field)\
        .eq("report_id", report_id)\
        .execute()
    
    if not response.data:
        return None
    
    ratings = [r[field] for r in response.data if r[field] is not None]
    return round(sum(ratings) / len(ratings), 1) if ratings else None

# 4. Add ALL the new specialist endpoints (add after existing report endpoints, around line 2300):

@app.post("/api/report/cardiology")
async def generate_cardiology_report(request: SpecialistReportRequest):
    """Generate cardiology-specific report"""
    try:
        # Load analysis and gather data
        analysis = await load_analysis(request.analysis_id)
        data = await gather_report_data(request.user_id or analysis["user_id"], analysis.get("report_config", {}))
        
        # Extract cardiac-specific data
        cardiac_context = await extract_cardiac_patterns(data)
        
        system_prompt = """Generate a cardiology report with these sections. Return valid JSON:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive cardiac assessment",
    "chief_complaints": ["cardiac-related symptoms"],
    "key_findings": ["important cardiac findings"],
    "urgency_indicators": ["red flags requiring immediate attention"],
    "action_items": ["recommended cardiac workup"]
  },
  "timeline_and_patterns": {
    "symptom_progression": "How cardiac symptoms evolved",
    "pattern_analysis": {
      "seems_to_pop_up_when": ["triggers identified"],
      "correlation_with_activity": "exertional vs rest patterns",
      "time_of_day_patterns": "when symptoms occur"
    }
  },
  "cardiac_specific": {
    "chest_pain_analysis": {
      "descriptions_found": ["patient's words for pain"],
      "exertional_component": "worse with activity?",
      "associated_symptoms": ["SOB, sweating, nausea"],
      "relief_factors": ["what helped"]
    },
    "risk_assessment": {
      "identified_risk_factors": ["from patient data"],
      "family_history_noted": "any mentions",
      "lifestyle_factors": ["smoking, exercise, stress"]
    },
    "vital_trends": {
      "heart_rate_patterns": "if wearable data available",
      "blood_pressure_mentions": "any BP data",
      "exercise_tolerance": "changes noted"
    }
  },
  "cardiology_workup": {
    "labs_to_consider": [
      {"test": "Troponin", "reason": "if acute symptoms"},
      {"test": "Lipid Panel", "reason": "risk assessment"},
      {"test": "BNP", "reason": "if HF suspected"}
    ],
    "cardiac_tests": ["EKG", "Echo", "Stress Test"],
    "red_flags_requiring_er": ["specific urgent indicators"]
  },
  "clinical_support": {
    "soap_note": {
      "subjective": "pre-filled from data",
      "objective": "vitals if available",
      "assessment": "differential diagnoses",
      "plan": "leave for doctor"
    },
    "icd10_suggestions": ["I20.9", "R07.9"],
    "follow_up_timing": "urgency-based recommendation"
  }
}"""
        
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": cardiac_context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=3000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", ""))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Cardiac assessment based on available data",
                    "chief_complaints": ["Cardiac symptoms reported"],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Clinical evaluation recommended"]
                }
            }
        
        # Save and return
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

@app.post("/api/report/neurology")
async def generate_neurology_report(request: SpecialistReportRequest):
    """Generate neurology-specific report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        data = await gather_report_data(request.user_id or analysis["user_id"], analysis.get("report_config", {}))
        
        neuro_context = await extract_neuro_patterns(data)
        
        system_prompt = """Generate a neurology report. Return valid JSON:
{
  "executive_summary": {
    "one_page_summary": "Neurological assessment summary",
    "chief_complaints": ["neurological symptoms"],
    "key_findings": ["important neuro findings"],
    "urgency_indicators": ["red flags"],
    "action_items": ["recommended workup"]
  },
  "timeline_and_patterns": {
    "symptom_progression": "How symptoms evolved",
    "pattern_analysis": {
      "seems_to_pop_up_when": ["identified triggers"],
      "sleep_correlation": "relationship with sleep",
      "stress_correlation": "stress impact",
      "food_triggers": "dietary correlations"
    }
  },
  "neurological_specific": {
    "headache_characterization": {
      "user_descriptions": ["throbbing, sharp, dull"],
      "location_patterns": ["where pain occurs"],
      "duration_patterns": "how long episodes last",
      "associated_symptoms": ["nausea, light sensitivity"]
    },
    "neurological_symptoms": {
      "vision_complaints": "any mentioned",
      "balance_issues": "dizziness, vertigo",
      "numbness_tingling": "locations and patterns",
      "cognitive_concerns": "memory, focus issues"
    },
    "trigger_analysis": {
      "environmental": ["weather, lights"],
      "behavioral": ["sleep, stress"],
      "dietary": ["foods mentioned"],
      "medication_response": "what helped/didn't"
    }
  },
  "neurology_workup": {
    "labs_to_consider": [
      {"test": "B12/Folate", "reason": "if numbness"},
      {"test": "Thyroid Panel", "reason": "multiple symptoms"},
      {"test": "Inflammatory Markers", "reason": "if indicated"}
    ],
    "imaging_considerations": ["MRI brain if red flags"],
    "specialized_tests": ["EEG if seizure concern"],
    "preventive_options": ["medication classes to discuss"]
  },
  "clinical_support": {
    "soap_note": {
      "subjective": "from patient data",
      "objective": "neuro exam template",
      "assessment": "differential list",
      "plan": "for doctor completion"
    },
    "icd10_suggestions": ["G43.909", "R51"],
    "headache_diary_recommendation": true
  }
}"""
        
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": neuro_context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=3000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", ""))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Neurological assessment based on available data",
                    "chief_complaints": ["Neurological symptoms reported"],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Clinical evaluation recommended"]
                }
            }
        
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

@app.post("/api/report/psychiatry")
async def generate_psychiatry_report(request: SpecialistReportRequest):
    """Generate psychiatry-specific report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        data = await gather_report_data(request.user_id or analysis["user_id"], analysis.get("report_config", {}))
        
        psych_context = await extract_mental_health_patterns(data)
        
        system_prompt = """Generate a psychiatry report. Return valid JSON:
{
  "executive_summary": {
    "one_page_summary": "Mental health assessment",
    "chief_complaints": ["mental health concerns"],
    "key_findings": ["important patterns"],
    "urgency_indicators": ["safety concerns"],
    "action_items": ["recommended interventions"]
  },
  "timeline_and_patterns": {
    "mood_progression": "How mood changed over time",
    "pattern_analysis": {
      "seems_worse_when": ["identified triggers"],
      "sleep_impact": "sleep-mood correlation",
      "stress_patterns": "stress response patterns",
      "social_factors": "isolation or support"
    }
  },
  "mental_health_specific": {
    "mood_patterns": {
      "emotional_keywords": ["anxious, depressed, stressed"],
      "energy_levels": "fatigue mentions",
      "sleep_quality": "insomnia, hypersomnia",
      "appetite_changes": "if mentioned"
    },
    "behavioral_insights": {
      "coping_strategies": "what user tried",
      "functional_impact": {
        "work_performance": "concerns noted",
        "relationships": "social impacts",
        "daily_activities": "ADL changes"
      },
      "substance_use": "if disclosed"
    },
    "symptom_severity": {
      "frequency": "how often symptoms occur",
      "intensity": "severity indicators",
      "duration": "episode lengths"
    }
  },
  "mental_health_workup": {
    "screening_tools": ["PHQ-9", "GAD-7", "others indicated"],
    "labs_to_consider": [
      {"test": "TSH", "reason": "rule out thyroid"},
      {"test": "Vitamin D", "reason": "mood correlation"},
      {"test": "B12", "reason": "if fatigue"}
    ],
    "therapy_modalities": ["CBT", "DBT", "others appropriate"],
    "medication_considerations": "general classes if severe"
  },
  "clinical_support": {
    "soap_note": {
      "subjective": "mood and symptoms",
      "objective": "MSE template",
      "assessment": "diagnostic considerations",
      "plan": "for psychiatrist"
    },
    "icd10_suggestions": ["F41.9", "F32.9"],
    "safety_planning": "if indicated"
  }
}"""
        
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": psych_context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=3000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", ""))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Mental health assessment based on available data",
                    "chief_complaints": ["Mental health concerns reported"],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Clinical evaluation recommended"]
                }
            }
        
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

@app.post("/api/report/dermatology")
async def generate_dermatology_report(request: SpecialistReportRequest):
    """Generate dermatology-specific report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        data = await gather_report_data(request.user_id or analysis["user_id"], analysis.get("report_config", {}))
        
        # Special handling for photo data
        photo_data = await gather_photo_data(request.user_id, analysis.get("report_config", {}))
        derm_context = await extract_dermatology_patterns(data, photo_data)
        
        system_prompt = """Generate a dermatology report. Return valid JSON:
{
  "executive_summary": {
    "one_page_summary": "Skin condition assessment",
    "chief_complaints": ["skin concerns"],
    "key_findings": ["important observations"],
    "urgency_indicators": ["concerning changes"],
    "action_items": ["recommended evaluation"]
  },
  "timeline_and_patterns": {
    "progression": "How condition changed",
    "pattern_analysis": {
      "environmental_triggers": ["weather, products"],
      "seasonal_patterns": "time of year impact",
      "product_correlations": "skincare/detergent links"
    }
  },
  "dermatology_specific": {
    "lesion_characterization": {
      "descriptions": ["user's words"],
      "locations": ["affected areas"],
      "symptoms": ["itching, pain, burning"],
      "evolution": "how it changed"
    },
    "photo_analysis": {
      "changes_noted": ["size, color, border"],
      "concerning_features": ["asymmetry, irregular borders"],
      "progression_rate": "speed of change"
    },
    "distribution_patterns": {
      "body_areas": ["where lesions appear"],
      "symmetry": "bilateral or unilateral",
      "pattern_type": "grouped, linear, scattered"
    }
  },
  "dermatology_workup": {
    "immediate_evaluation": "if concerning features",
    "biopsy_consideration": "indications",
    "labs_if_systemic": [
      {"test": "ANA", "reason": "if autoimmune suspected"},
      {"test": "CBC", "reason": "if infection"}
    ],
    "treatment_considerations": ["topical options", "systemic if needed"]
  },
  "clinical_support": {
    "soap_note": {
      "subjective": "skin complaints",
      "objective": "lesion description template",
      "assessment": "differential list",
      "plan": "for dermatologist"
    },
    "icd10_suggestions": ["L30.9", "specific codes"],
    "photo_documentation": "importance noted"
  }
}"""
        
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": derm_context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=3000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", ""))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Dermatological assessment based on available data",
                    "chief_complaints": ["Skin concerns reported"],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Clinical evaluation recommended"]
                }
            }
        
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

@app.post("/api/report/gastroenterology")
async def generate_gastroenterology_report(request: SpecialistReportRequest):
    """Generate gastroenterology-specific report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        data = await gather_report_data(request.user_id or analysis["user_id"], analysis.get("report_config", {}))
        
        gi_context = await extract_gi_patterns(data)
        
        system_prompt = """Generate a gastroenterology report. Return valid JSON:
{
  "executive_summary": {
    "one_page_summary": "GI assessment summary",
    "chief_complaints": ["digestive symptoms"],
    "key_findings": ["important GI findings"],
    "urgency_indicators": ["red flags"],
    "action_items": ["recommended workup"]
  },
  "timeline_and_patterns": {
    "symptom_progression": "How GI symptoms evolved",
    "pattern_analysis": {
      "food_correlations": ["triggers identified"],
      "meal_timing": "relation to eating",
      "stress_impact": "stress-gut connection",
      "bowel_patterns": "frequency changes"
    }
  },
  "gi_specific": {
    "symptom_characterization": {
      "pain_location": ["epigastric, RLQ, etc"],
      "pain_quality": ["cramping, burning, sharp"],
      "associated_symptoms": ["nausea, bloating, diarrhea"],
      "relief_factors": ["what helps"]
    },
    "dietary_analysis": {
      "trigger_foods": ["identified triggers"],
      "safe_foods": ["well-tolerated"],
      "meal_patterns": "eating schedule impact",
      "hydration": "fluid intake patterns"
    },
    "bowel_patterns": {
      "frequency_changes": "constipation/diarrhea",
      "consistency_changes": "if mentioned",
      "blood_or_mucus": "concerning features",
      "urgency_incontinence": "if present"
    }
  },
  "gi_workup": {
    "labs_to_consider": [
      {"test": "CBC", "reason": "anemia screen"},
      {"test": "CMP", "reason": "electrolytes"},
      {"test": "Celiac Panel", "reason": "if indicated"},
      {"test": "H. pylori", "reason": "if dyspepsia"}
    ],
    "imaging_endoscopy": ["considerations based on symptoms"],
    "stool_studies": ["if diarrhea prominent"]
  },
  "clinical_support": {
    "soap_note": {
      "subjective": "GI complaints",
      "objective": "abdominal exam template",
      "assessment": "differential diagnoses",
      "plan": "for GI specialist"
    },
    "icd10_suggestions": ["K30", "K58.9"],
    "dietary_counseling": "recommendations"
  }
}"""
        
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": gi_context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=3000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", ""))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "GI assessment based on available data",
                    "chief_complaints": ["GI symptoms reported"],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Clinical evaluation recommended"]
                }
            }
        
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

@app.post("/api/report/endocrinology")
async def generate_endocrinology_report(request: SpecialistReportRequest):
    """Generate endocrinology-specific report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        data = await gather_report_data(request.user_id or analysis["user_id"], analysis.get("report_config", {}))
        
        endo_context = await extract_endocrine_patterns(data)
        
        system_prompt = """Generate an endocrinology report. Return valid JSON:
{
  "executive_summary": {
    "one_page_summary": "Endocrine assessment",
    "chief_complaints": ["metabolic/hormonal symptoms"],
    "key_findings": ["important findings"],
    "urgency_indicators": ["concerning features"],
    "action_items": ["recommended evaluation"]
  },
  "timeline_and_patterns": {
    "symptom_progression": "How symptoms evolved",
    "pattern_analysis": {
      "energy_patterns": ["fatigue timing"],
      "weight_changes": "gain/loss patterns",
      "temperature_regulation": "hot/cold intolerance",
      "mood_correlation": "hormonal-mood links"
    }
  },
  "endocrine_specific": {
    "metabolic_symptoms": {
      "energy_levels": ["fatigue patterns"],
      "weight_changes": ["unexplained changes"],
      "appetite_changes": ["increased/decreased"],
      "thirst_urination": ["polyuria/polydipsia"]
    },
    "hormonal_indicators": {
      "thyroid_symptoms": ["hyper/hypo features"],
      "adrenal_symptoms": ["cortisol patterns"],
      "reproductive": ["cycle changes if applicable"],
      "growth_changes": ["if relevant"]
    },
    "physical_changes": {
      "skin_changes": ["dryness, texture"],
      "hair_changes": ["loss, texture"],
      "temperature_intolerance": ["heat/cold"],
      "sweating_patterns": ["increased/decreased"]
    }
  },
  "endocrine_workup": {
    "labs_essential": [
      {"test": "TSH, Free T4", "reason": "thyroid screen"},
      {"test": "Fasting Glucose, HbA1c", "reason": "diabetes screen"},
      {"test": "Cortisol", "reason": "if indicated"},
      {"test": "Vitamin D", "reason": "common deficiency"}
    ],
    "additional_tests": ["based on presentation"],
    "imaging": ["thyroid US if nodule"]
  },
  "clinical_support": {
    "soap_note": {
      "subjective": "endocrine symptoms",
      "objective": "physical findings",
      "assessment": "differential list",
      "plan": "for endocrinologist"
    },
    "icd10_suggestions": ["E04.9", "E11.9"],
    "lifestyle_factors": "diet, exercise impact"
  }
}"""
        
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": endo_context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=3000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", ""))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Endocrine assessment based on available data",
                    "chief_complaints": ["Endocrine symptoms reported"],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Clinical evaluation recommended"]
                }
            }
        
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

@app.post("/api/report/pulmonology")
async def generate_pulmonology_report(request: SpecialistReportRequest):
    """Generate pulmonology-specific report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        data = await gather_report_data(request.user_id or analysis["user_id"], analysis.get("report_config", {}))
        
        pulm_context = await extract_pulmonary_patterns(data)
        
        system_prompt = """Generate a pulmonology report. Return valid JSON:
{
  "executive_summary": {
    "one_page_summary": "Respiratory assessment",
    "chief_complaints": ["breathing concerns"],
    "key_findings": ["important findings"],
    "urgency_indicators": ["red flags"],
    "action_items": ["recommended workup"]
  },
  "timeline_and_patterns": {
    "symptom_progression": "How breathing issues evolved",
    "pattern_analysis": {
      "exertional_patterns": ["activity tolerance"],
      "environmental_triggers": ["allergens, weather"],
      "time_of_day": ["nocturnal symptoms"],
      "seasonal_variation": ["worse in specific seasons"]
    }
  },
  "pulmonary_specific": {
    "breathing_symptoms": {
      "dyspnea_characterization": ["SOB patterns"],
      "cough_description": ["dry, productive, timing"],
      "sputum_production": ["color, amount if mentioned"],
      "wheezing_stridor": ["if present"]
    },
    "associated_symptoms": {
      "chest_tightness": ["location, triggers"],
      "exercise_tolerance": ["METs, stairs"],
      "orthopnea_pnd": ["positional breathing"],
      "constitutional": ["fever, weight loss"]
    },
    "exposure_history": {
      "smoking": ["pack-years if mentioned"],
      "occupational": ["dust, chemicals"],
      "environmental": ["mold, pets"],
      "travel": ["TB risk areas"]
    }
  },
  "pulmonary_workup": {
    "labs_to_consider": [
      {"test": "CBC", "reason": "infection/eosinophilia"},
      {"test": "ABG", "reason": "if hypoxia suspected"},
      {"test": "D-dimer", "reason": "if PE concern"}
    ],
    "pulmonary_tests": ["PFTs", "CXR", "CT if indicated"],
    "specialized": ["sleep study if OSA suspected"]
  },
  "clinical_support": {
    "soap_note": {
      "subjective": "respiratory complaints",
      "objective": "lung exam findings",
      "assessment": "differential list",
      "plan": "for pulmonologist"
    },
    "icd10_suggestions": ["J44.0", "J45.909"],
    "inhaler_education": "if prescribed"
  }
}"""
        
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": pulm_context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=3000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", ""))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Pulmonary assessment based on available data",
                    "chief_complaints": ["Breathing concerns reported"],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Clinical evaluation recommended"]
                }
            }
        
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

# Time-Based Report Endpoints

@app.post("/api/report/30-day")
async def generate_30_day_report(request: TimePeriodReportRequest):
    """Generate comprehensive 30-day health summary"""
    try:
        # Set 30-day time range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)
        
        config = {
            "time_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
        
        # Gather ALL data from last 30 days
        all_data = await gather_comprehensive_data(request.user_id, config)
        
        # Build context with everything
        context = f"""Generate a comprehensive 30-day health report summarizing ALL health data:

OVERVIEW:
- Total Quick Scans: {len(all_data['quick_scans'])}
- Total Deep Dives: {len(all_data['deep_dives'])}
- Total Symptoms Tracked: {len(all_data['symptom_tracking'])}
- LLM Chat Sessions: {len(all_data.get('llm_summaries', []))}

QUICK SCANS DATA:
{json.dumps([{
    'date': s['created_at'][:10],
    'body_part': s['body_part'],
    'symptoms': s.get('form_data', {}).get('symptoms'),
    'severity': s.get('form_data', {}).get('painLevel'),
    'analysis': s.get('analysis_result', {}).get('primaryCondition')
} for s in all_data['quick_scans']], indent=2)}

DEEP DIVE SESSIONS:
{json.dumps([{
    'date': d['created_at'][:10],
    'body_part': d['body_part'],
    'final_analysis': d.get('final_analysis', {}).get('primaryCondition'),
    'recommendations': d.get('final_analysis', {}).get('recommendations', [])[:3]
} for d in all_data['deep_dives']], indent=2)}

LONG-TERM TRACKING DATA:
{json.dumps(all_data.get('tracking_data', []), indent=2)}

WEARABLE DATA (if available):
{json.dumps(all_data.get('wearables', {}), indent=2)}"""

        system_prompt = """Generate a 30-day comprehensive health report. Return valid JSON:
{
  "executive_dashboard": {
    "health_interaction_summary": {
      "total_interactions": number,
      "quick_scans": number,
      "deep_dives": number,
      "photos_tracked": number
    },
    "top_symptoms_by_frequency": [
      {"symptom": "name", "count": number, "average_severity": number}
    ],
    "overall_trend": "improving/stable/declining",
    "key_patterns_identified": ["pattern 1", "pattern 2", "pattern 3"]
  },
  "pattern_analysis": {
    "symptom_correlations": {
      "primary_correlations": [
        {"symptoms": ["A", "B"], "correlation_strength": "87%", "pattern": "A occurs 2-3 days after B"}
      ],
      "seems_to_pop_up_when": [
        {"trigger": "poor sleep", "affected_symptoms": ["headache", "fatigue"], "confidence": "high"}
      ]
    },
    "temporal_patterns": {
      "time_of_day": {"worst_times": ["2-4pm"], "best_times": ["morning"]},
      "day_of_week": {"worst_days": ["Monday", "Tuesday"], "best_days": ["Saturday"]}
    }
  },
  "effectiveness_tracking": {
    "what_helped": [
      {"intervention": "Ibuprofen", "success_rate": "7/10 times", "symptoms_helped": ["headache"]}
    ],
    "what_didnt_help": [
      {"intervention": "name", "symptoms_tried_for": ["list"]}
    ]
  },
  "data_insights": {
    "all_symptoms_summary": "narrative of health journey",
    "progress_indicators": ["improvements noted"],
    "concerning_trends": ["if any"],
    "data_quality": "completeness of tracking"
  },
  "forward_looking": {
    "patterns_to_monitor": ["specific things to watch"],
    "suggested_tracking_additions": ["what else to track"],
    "when_to_seek_care": ["specific triggers"],
    "next_month_priorities": ["health goals"]
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", ""))
        
        if not report_data:
            report_data = {
                "executive_dashboard": {
                    "health_interaction_summary": {
                        "total_interactions": len(all_data['quick_scans']) + len(all_data['deep_dives']),
                        "quick_scans": len(all_data['quick_scans']),
                        "deep_dives": len(all_data['deep_dives']),
                        "photos_tracked": 0
                    },
                    "overall_trend": "stable"
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "report_type": "30_day",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "time_range": config["time_range"],
            "data_sources": {
                "quick_scans": len(all_data['quick_scans']),
                "deep_dives": len(all_data['deep_dives']),
                "tracking_points": len(all_data['symptom_tracking'])
            }
        }
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "30_day",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating 30-day report: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/annual")
async def generate_annual_report(request: TimePeriodReportRequest):
    """Generate comprehensive annual health summary"""
    try:
        # Set 1-year time range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=365)
        
        config = {
            "time_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
        
        # Gather ALL data from last year
        all_data = await gather_comprehensive_data(request.user_id, config)
        
        # Group data by month for trends
        monthly_summary = await group_data_by_month(all_data)
        
        context = f"""Generate a comprehensive annual health report for the past year:

YEAR OVERVIEW:
- Total Health Interactions: {sum(len(v) for v in all_data.values() if isinstance(v, list))}
- Months with Data: {len(monthly_summary)}
- Most Active Month: {max(monthly_summary.items(), key=lambda x: x[1]['total_interactions'])[0] if monthly_summary else 'N/A'}

MONTHLY BREAKDOWN:
{json.dumps(monthly_summary, indent=2)}

ALL SYMPTOMS BY FREQUENCY:
{json.dumps(count_symptoms_by_frequency(all_data), indent=2)}

SEASONAL PATTERNS:
{json.dumps(analyze_seasonal_patterns(all_data), indent=2)}

FULL YEAR DATA:
- Quick Scans: {len(all_data['quick_scans'])}
- Deep Dives: {len(all_data['deep_dives'])}
- Tracking Points: {len(all_data['symptom_tracking'])}
"""

        system_prompt = """Generate an annual health report. Return valid JSON:
{
  "year_at_a_glance": {
    "monthly_health_scores": {"month": score},
    "major_health_events": [
      {"date": "YYYY-MM", "event": "description", "impact": "how it affected health"}
    ],
    "seasonal_patterns": {
      "winter": ["common issues"],
      "spring": ["common issues"],
      "summer": ["common issues"],
      "fall": ["common issues"]
    },
    "year_over_year_comparison": "if previous year data available"
  },
  "comprehensive_analysis": {
    "all_symptoms_ranked": [
      {"symptom": "name", "total_occurrences": number, "average_severity": number, "trend": "increasing/stable/decreasing"}
    ],
    "treatment_effectiveness_summary": {
      "most_effective": ["interventions that worked"],
      "least_effective": ["interventions that didn't help"],
      "adherence_patterns": "consistency of self-care"
    },
    "pattern_evolution": {
      "new_patterns_emerged": ["patterns that appeared this year"],
      "resolved_patterns": ["issues that went away"],
      "persistent_patterns": ["ongoing concerns"]
    },
    "breakthrough_moments": ["significant improvements or discoveries"]
  },
  "system_by_system_review": {
    "cardiovascular": {"status": "summary", "concerns": [], "improvements": []},
    "neurological": {"status": "summary", "concerns": [], "improvements": []},
    "musculoskeletal": {"status": "summary", "concerns": [], "improvements": []},
    "mental_health": {"status": "summary", "concerns": [], "improvements": []},
    "digestive": {"status": "summary", "concerns": [], "improvements": []},
    "other_systems": {}
  },
  "preventive_care": {
    "age_appropriate_screenings": ["based on age/risk factors"],
    "vaccinations_due": ["standard adult vaccines"],
    "risk_based_recommendations": ["based on patterns"],
    "specialist_referrals_suggested": ["if patterns warrant"]
  },
  "next_year_planning": {
    "health_goals_based_on_data": ["specific, measurable goals"],
    "monitoring_recommendations": ["what to track more closely"],
    "lifestyle_modifications": ["evidence-based suggestions"],
    "preventive_priorities": ["proactive health measures"]
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=5000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", ""))
        
        if not report_data:
            report_data = {
                "year_at_a_glance": {
                    "monthly_health_scores": {},
                    "major_health_events": [],
                    "seasonal_patterns": {}
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "report_type": "annual",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "time_range": config["time_range"],
            "year": end_date.year,
            "data_sources": {
                "quick_scans": len(all_data['quick_scans']),
                "deep_dives": len(all_data['deep_dives']),
                "tracking_points": len(all_data['symptom_tracking']),
                "months_with_data": len(monthly_summary)
            }
        }
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "annual",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating annual report: {e}")
        return {"error": str(e), "status": "error"}

# Doctor Collaboration Endpoints

@app.put("/api/report/{report_id}/doctor-notes")
async def add_doctor_notes(report_id: str, request: DoctorNotesRequest):
    """Allow doctors to add notes and edit reports"""
    try:
        # Verify report exists
        report = supabase.table("medical_reports")\
            .select("*")\
            .eq("id", report_id)\
            .execute()
        
        if not report.data:
            return {"error": "Report not found", "status": "error"}
        
        # Add doctor notes to report
        updated_report_data = report.data[0]["report_data"]
        if "doctor_notes" not in updated_report_data:
            updated_report_data["doctor_notes"] = []
        
        doctor_note = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "npi": request.doctor_npi,
            "specialty": request.specialty,
            "notes": request.notes,
            "sections_reviewed": request.sections_reviewed,
            "diagnosis_added": request.diagnosis,
            "plan_modifications": request.plan_modifications,
            "follow_up_instructions": request.follow_up_instructions
        }
        
        updated_report_data["doctor_notes"].append(doctor_note)
        updated_report_data["doctor_reviewed"] = True
        updated_report_data["last_doctor_review"] = datetime.now(timezone.utc).isoformat()
        
        # Update report
        supabase.table("medical_reports")\
            .update({
                "report_data": updated_report_data,
                "doctor_reviewed": True,
                "last_modified": datetime.now(timezone.utc).isoformat()
            })\
            .eq("id", report_id)\
            .execute()
        
        # Also save to doctor_notes table
        note_record = {
            "report_id": report_id,
            "doctor_npi": request.doctor_npi,
            "specialty": request.specialty,
            "notes": request.notes,
            "sections_reviewed": request.sections_reviewed,
            "diagnosis_added": request.diagnosis,
            "plan_modifications": request.plan_modifications,
            "follow_up_instructions": request.follow_up_instructions
        }
        
        supabase.table("report_doctor_notes").insert(note_record).execute()
        
        return {
            "report_id": report_id,
            "notes_added": True,
            "timestamp": doctor_note["timestamp"],
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error adding doctor notes: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/{report_id}/share")
async def share_report(report_id: str, request: ShareReportRequest):
    """Share report with other healthcare providers"""
    try:
        # Create share record
        share_id = str(uuid.uuid4())
        share_data = {
            "id": share_id,
            "report_id": report_id,
            "shared_by_npi": request.shared_by_npi,
            "shared_with_npi": request.recipient_npi,
            "access_level": request.access_level,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=request.expiration_days)).isoformat(),
            "share_notes": request.notes,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("report_shares").insert(share_data).execute()
        
        # Generate secure share link
        share_link = f"{request.base_url}/shared-report/{share_id}"
        
        return {
            "share_id": share_id,
            "share_link": share_link,
            "expires_at": share_data["expires_at"],
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error sharing report: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/{report_id}/rate")
async def rate_report(report_id: str, request: RateReportRequest):
    """Allow doctors to rate report usefulness"""
    try:
        rating_data = {
            "id": str(uuid.uuid4()),
            "report_id": report_id,
            "doctor_npi": request.doctor_npi,
            "usefulness_score": request.usefulness_score,  # 1-5
            "accuracy_score": request.accuracy_score,      # 1-5
            "time_saved_minutes": request.time_saved,
            "would_recommend": request.would_recommend,
            "feedback_text": request.feedback,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("report_ratings").insert(rating_data).execute()
        
        return {
            "rating_recorded": True,
            "average_usefulness": await get_average_rating(report_id, "usefulness_score"),
            "average_accuracy": await get_average_rating(report_id, "accuracy_score"),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error rating report: {e}")
        return {"error": str(e), "status": "error"}

# Outbreak Detection Endpoint

@app.get("/api/population-health/alerts")
async def get_population_health_alerts(location: str, symptoms: Optional[List[str]] = None):
    """Get local outbreak alerts and population health insights"""
    try:
        # Query similar symptoms in the area (last 14 days)
        recent_date = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        
        # Get symptom clusters
        symptom_clusters = supabase.table("quick_scans")\
            .select("form_data, created_at")\
            .gte("created_at", recent_date)\
            .execute()
        
        # Analyze patterns
        symptom_counts = {}
        for scan in (symptom_clusters.data or []):
            if scan.get("form_data", {}).get("symptoms"):
                symptom = scan["form_data"]["symptoms"].lower()
                symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1
        
        # Identify unusual increases
        alerts = []
        for symptom, count in symptom_counts.items():
            if count > 5:  # Threshold for alert
                alerts.append({
                    "symptom": symptom,
                    "case_count": count,
                    "trend": "increasing" if count > 10 else "elevated",
                    "recommendation": f"Consider {symptom} in differential"
                })
        
        # Check outbreak tracking table
        outbreak_data = supabase.table("outbreak_tracking")\
            .select("*")\
            .eq("status", "active")\
            .execute()
        
        # Mock CDC alerts (would integrate with real API)
        cdc_alerts = [
            {
                "condition": "Influenza A",
                "status": "High activity",
                "region": location,
                "updated": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        return {
            "local_symptom_clusters": alerts,
            "outbreak_data": outbreak_data.data or [],
            "cdc_alerts": cdc_alerts,
            "similar_cases_this_week": len([s for s in symptom_counts.values() if s > 3]),
            "recommendation": "Standard precautions" if not alerts else "Heightened awareness",
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error getting population health alerts: {e}")
        return {"error": str(e), "status": "error"}

# 5. Update the root endpoint to include ALL new report types (around line 3100):
# Replace the existing reports section in the root endpoint with this complete list:

"reports": {
    "analyze": "POST /api/report/analyze",
    "comprehensive": "POST /api/report/comprehensive",
    "urgent_triage": "POST /api/report/urgent-triage",
    "photo_progression": "POST /api/report/photo-progression",
    "symptom_timeline": "POST /api/report/symptom-timeline",
    "specialist": "POST /api/report/specialist",
    "annual_summary": "POST /api/report/annual-summary",
    # NEW SPECIALIST ENDPOINTS
    "cardiology": "POST /api/report/cardiology",
    "neurology": "POST /api/report/neurology",
    "psychiatry": "POST /api/report/psychiatry",
    "dermatology": "POST /api/report/dermatology",
    "gastroenterology": "POST /api/report/gastroenterology",
    "endocrinology": "POST /api/report/endocrinology",
    "pulmonology": "POST /api/report/pulmonology",
    # TIME-BASED REPORTS
    "30_day": "POST /api/report/30-day",
    "annual": "POST /api/report/annual",
    # DOCTOR COLLABORATION
    "add_doctor_notes": "PUT /api/report/{report_id}/doctor-notes",
    "share_report": "POST /api/report/{report_id}/share",
    "rate_report": "POST /api/report/{report_id}/rate",
    # POPULATION HEALTH
    "outbreak_alerts": "GET /api/population-health/alerts",
    # EXISTING
    "list_user_reports": "GET /api/reports?user_id=USER_ID",
    "get_report": "GET /api/reports/{report_id}",
    "mark_accessed": "POST /api/reports/{report_id}/access"
}