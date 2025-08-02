"""Time-based Report API endpoints (30-day, annual, annual summary)"""
from fastapi import APIRouter
from datetime import datetime, timezone, timedelta
import json
import uuid

from models.requests import TimePeriodReportRequest, AnnualSummaryRequest
from supabase_client import supabase
from business_logic import call_llm
from utils.json_parser import extract_json_from_response
from utils.data_gathering import safe_insert_report

router = APIRouter(prefix="/api/report", tags=["reports-time"])

# Helper functions specific to time-based reports
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
    
    # Photo Analysis Sessions and Data
    photo_sessions = supabase.table("photo_sessions")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    photo_analyses = []
    if photo_sessions.data:
        session_ids = [s["id"] for s in photo_sessions.data]
        photo_analyses_result = supabase.table("photo_analyses")\
            .select("*")\
            .in_("session_id", session_ids)\
            .order("created_at.desc")\
            .execute()
        photo_analyses = photo_analyses_result.data or []
    
    # General Assessments (text-based)
    general_assessments = supabase.table("general_assessments")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    # Flash Assessments (quick text analysis)
    flash_assessments = supabase.table("flash_assessments")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    # Health Stories (AI-generated narratives)
    health_stories = supabase.table("health_stories")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    # Population Health Alerts
    population_health = supabase.table("population_health_alerts")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    # Medication Tracking (if exists)
    medications = supabase.table("medication_tracking")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    # User Medical Profile
    medical_profile = supabase.table("medical")\
        .select("*")\
        .eq("id", user_id)\
        .execute()
    
    return {
        "quick_scans": scans.data or [],
        "deep_dives": dives.data or [],
        "symptom_tracking": tracking.data or [],
        "tracking_data": tracking_data,
        "llm_summaries": chats.data or [],
        "photo_sessions": photo_sessions.data or [],
        "photo_analyses": photo_analyses,
        "general_assessments": general_assessments.data or [],
        "flash_assessments": flash_assessments.data or [],
        "health_stories": health_stories.data or [],
        "population_health_alerts": population_health.data or [],
        "medications": medications.data or [],
        "medical_profile": medical_profile.data[0] if medical_profile.data else None,
        "wearables": {}  # Placeholder for wearables integration
    }

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

@router.post("/30-day")
async def generate_30_day_report(request: TimePeriodReportRequest):
    """Generate 30-day aggregate health report"""
    try:
        # Set up 30-day time range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)
        
        config = {
            "time_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
        
        # Gather ALL data for the period
        all_data = await gather_comprehensive_data(request.user_id, config)
        
        # Group data by week
        weekly_data = {}
        for i in range(4):
            week_start = start_date + timedelta(days=i*7)
            week_end = week_start + timedelta(days=7)
            week_key = f"Week {i+1}"
            weekly_data[week_key] = {
                "quick_scans": 0,
                "deep_dives": 0,
                "symptoms": {},
                "severity_avg": 0,
                "notable_events": []
            }
        
        # Process data into weekly buckets
        for scan in all_data.get("quick_scans", []):
            scan_date = datetime.fromisoformat(scan["created_at"].replace('Z', '+00:00'))
            week_num = (scan_date - start_date).days // 7
            if 0 <= week_num < 4:
                week_key = f"Week {week_num + 1}"
                weekly_data[week_key]["quick_scans"] += 1
                
                # Track symptoms
                symptoms = scan.get("form_data", {}).get("symptoms", "Unknown")
                if symptoms not in weekly_data[week_key]["symptoms"]:
                    weekly_data[week_key]["symptoms"][symptoms] = 0
                weekly_data[week_key]["symptoms"][symptoms] += 1
        
        # Calculate symptom frequencies
        symptom_freq = count_symptoms_by_frequency(all_data)
        
        # Extract patterns
        patterns = []
        for scan in all_data.get("quick_scans", []):
            if scan.get("analysis_result", {}).get("primaryCondition"):
                patterns.append({
                    "date": scan["created_at"][:10],
                    "condition": scan["analysis_result"]["primaryCondition"],
                    "severity": scan.get("form_data", {}).get("painLevel", 5)
                })
        
        context = f"""Generate a 30-day comprehensive health report analyzing ALL available health data.

TIME PERIOD: {start_date.strftime('%B %d')} to {end_date.strftime('%B %d, %Y')}

ACTIVITY SUMMARY:
- Total Quick Scans: {len(all_data.get('quick_scans', []))}
- Total Deep Dives: {len(all_data.get('deep_dives', []))}
- Symptom Tracking Entries: {len(all_data.get('symptom_tracking', []))}
- LLM Chat Sessions: {len(all_data.get('llm_summaries', []))}
- Photo Analysis Sessions: {len(all_data.get('photo_sessions', []))}
- General Assessments: {len(all_data.get('general_assessments', []))}
- Flash Assessments: {len(all_data.get('flash_assessments', []))}
- Health Stories Generated: {len(all_data.get('health_stories', []))}
- Population Health Alerts: {len(all_data.get('population_health_alerts', []))}
- Medication Entries: {len(all_data.get('medications', []))}

WEEKLY BREAKDOWN:
{json.dumps(weekly_data, indent=2)}

TOP SYMPTOMS (by frequency):
{json.dumps(symptom_freq[:10], indent=2)}

PATTERN DATA:
{json.dumps(patterns[:20], indent=2)}

PHOTO ANALYSIS INSIGHTS:
{json.dumps([{
    'date': pa['created_at'][:10],
    'condition': pa['analysis_data'].get('primary_assessment'),
    'confidence': pa.get('confidence_score'),
    'visual_changes': pa['analysis_data'].get('visual_observations', [])[:2]
} for pa in all_data.get('photo_analyses', [])[:10]], indent=2)}

GENERAL/FLASH ASSESSMENTS:
{json.dumps([{
    'date': a['created_at'][:10],
    'category': a.get('category', 'general'),
    'severity': a.get('severity_score'),
    'key_finding': a.get('assessment_result', {}).get('primary_finding')
} for a in (all_data.get('general_assessments', []) + all_data.get('flash_assessments', []))[:10]], indent=2)}

MEDICATION ADHERENCE:
{json.dumps([{
    'medication': m.get('medication_name'),
    'adherence_rate': m.get('adherence_percentage'),
    'missed_doses': m.get('missed_doses_count')
} for m in all_data.get('medications', [])[:5]], indent=2)}

USER PROFILE:
Age: {all_data.get('medical_profile', {}).get('age', 'Unknown')}
Chronic Conditions: {all_data.get('medical_profile', {}).get('chronic_conditions', [])}
Allergies: {all_data.get('medical_profile', {}).get('allergies', [])}

WEARABLES DATA: {json.dumps(all_data.get('wearables', {}), indent=2) if request.include_wearables else 'Not included'}"""

        system_prompt = """Generate a comprehensive 30-day aggregate health report analyzing ALL available health data types. Look for patterns, correlations, and actionable insights across all data sources.

IMPORTANT: Analyze correlations between different data types (e.g., symptoms appearing after medication changes, visual changes correlating with symptom reports, etc.)

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive 30-day health overview with key insights",
    "key_findings": ["major insights from the period"],
    "patterns_identified": ["X seems to pop up when Y", "correlation patterns"],
    "action_items": ["specific, actionable recommendations"],
    "health_trajectory": "improving/stable/declining overall"
  },
  "period_overview": {
    "total_health_interactions": 0,
    "engagement_level": "high/medium/low based on consistency",
    "most_active_week": "Week X",
    "primary_concerns": ["top 3-5 health issues"],
    "improvement_areas": ["symptoms that improved with specific examples"],
    "worsening_areas": ["symptoms that worsened with specific dates"],
    "stable_conditions": ["unchanged patterns"],
    "new_symptoms": ["any new health issues that appeared"]
  },
  "multi_source_analysis": {
    "cross_data_correlations": [
      {
        "finding": "Photo shows improvement but symptoms report worsening",
        "data_sources": ["photo_analysis", "symptom_tracking"],
        "dates": ["specific dates"],
        "implication": "possible perception vs reality gap"
      }
    ],
    "medication_impact": {
      "adherence_correlation": "symptoms better/worse with adherence",
      "side_effect_patterns": ["potential side effects identified"],
      "effectiveness_indicators": ["improvements after starting medication"]
    },
    "visual_vs_reported": {
      "consistency": "high/medium/low",
      "discrepancies": ["photo shows X but patient reports Y"]
    }
  },
  "pattern_analysis": {
    "temporal_patterns": {
      "time_of_day": ["morning: headaches", "evening: fatigue"],
      "day_of_week": ["Monday: high stress symptoms", "Weekend: better sleep"],
      "weekly_trends": ["Week 1: declining", "Week 2: improving"],
      "monthly_cycle": ["if applicable, menstrual cycle correlations"]
    },
    "correlation_patterns": {
      "symptom_triggers": ["stress → headaches", "poor sleep → fatigue"],
      "environmental_factors": ["weather changes → joint pain"],
      "activity_correlations": ["exercise → improved mood"],
      "comorbidity_patterns": ["headache + nausea occur together 80% of time"]
    },
    "severity_analysis": {
      "average_severity": 5.2,
      "severity_trend": "improving by 15% week-over-week",
      "high_severity_events": [
        {"date": "2024-01-15", "symptom": "migraine", "severity": 9, "duration": "4 hours"}
      ],
      "severity_predictors": ["lack of sleep predicts high severity next day"]
    }
  },
  "detailed_findings": {
    "by_body_system": {
      "neurological": ["15 headaches, decreasing frequency", "2 episodes of dizziness"],
      "cardiovascular": ["3 reports of palpitations, all during stress"],
      "respiratory": ["mild congestion week 2, resolved"],
      "gastrointestinal": ["intermittent bloating after dairy"],
      "musculoskeletal": ["lower back pain on days without exercise"],
      "dermatological": ["eczema flare week 1, improving with treatment"],
      "mental_health": ["anxiety correlated with work deadlines"]
    },
    "by_data_source": {
      "quick_scans": {"total": 12, "main_findings": ["headaches most common"]},
      "deep_dives": {"total": 3, "insights": ["stress major trigger"]},
      "photo_analyses": {"total": 5, "visual_trends": ["skin improving"]},
      "general_assessments": {"total": 2, "categories": ["mental health", "sleep"]},
      "symptom_tracking": {"total": 45, "most_tracked": ["headache", "fatigue"]}
    }
  },
  "predictive_insights": {
    "emerging_patterns": ["increasing afternoon fatigue → possible blood sugar issues"],
    "risk_indicators": ["3+ days poor sleep → migraine within 48 hours"],
    "preventive_opportunities": ["morning exercise prevents afternoon fatigue"],
    "predicted_challenges": ["upcoming stressful period may trigger symptoms"],
    "early_warning_signs": ["neck tension precedes headaches by 1-2 days"]
  },
  "comparative_analysis": {
    "vs_previous_30_days": "if available, compare to prior period",
    "improvement_rate": "25% reduction in symptom days",
    "new_vs_recurring": {"new_issues": 2, "recurring_issues": 5}
  },
  "recommendations": {
    "immediate_actions": ["address sleep issues - affecting multiple symptoms"],
    "lifestyle_modifications": [
      "implement regular sleep schedule (10pm-6am ideal based on patterns)",
      "add morning walk - data shows 40% symptom reduction on exercise days",
      "eliminate dairy for 2 weeks - possible trigger for GI symptoms"
    ],
    "monitoring_priorities": [
      "track sleep quality more consistently",
      "photo document skin changes weekly",
      "log food intake when GI symptoms occur"
    ],
    "specialist_consultations": [
      {"specialty": "neurology", "reason": "recurring headaches with increasing frequency"},
      {"specialty": "sleep medicine", "reason": "sleep issues affecting overall health"}
    ],
    "follow_up_timeline": "reassess in 2 weeks after implementing sleep changes"
  },
  "medication_insights": {
    "current_medications": ["list with adherence rates"],
    "effectiveness_analysis": "headache medication 70% effective",
    "optimization_opportunities": ["consider preventive medication for headaches"],
    "adherence_impact": "symptoms 2x worse on days medication missed"
  },
  "data_quality_metrics": {
    "data_completeness": "73% - good but room for improvement",
    "consistency_score": "85% - very consistent tracking",
    "data_gaps": ["weekend tracking sporadic", "no evening symptom logs"],
    "most_reliable_data": ["morning quick scans", "photo documentation"],
    "recommendations_for_tracking": ["add evening check-ins", "use reminders for weekend"]
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
                    "one_page_summary": "30-day report generation failed. Please retry.",
                    "key_findings": [],
                    "patterns_identified": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "report_type": "30_day_summary",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "executive_summary": report_data["executive_summary"]["one_page_summary"],
            "confidence_score": 90,
            "model_used": "tngtech/deepseek-r1t-chimera:free",
            "time_range": config["time_range"]
        }
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "30_day_summary",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating 30-day report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/annual")
async def generate_annual_report(request: TimePeriodReportRequest):
    """Generate annual aggregate health report"""
    try:
        # Set up annual time range
        year = datetime.now().year
        start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
        end_date = datetime.now(timezone.utc)
        
        config = {
            "time_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
        
        # Gather ALL data for the year
        all_data = await gather_comprehensive_data(request.user_id, config)
        
        # Group data by month
        monthly_data = await group_data_by_month(all_data)
        
        # Calculate yearly metrics
        total_interactions = sum(m["total_interactions"] for m in monthly_data.values())
        
        # Analyze seasonal patterns
        seasonal_patterns = analyze_seasonal_patterns(all_data)
        
        # Get top conditions throughout the year
        all_conditions = []
        for scan in all_data.get("quick_scans", []):
            condition = scan.get("analysis_result", {}).get("primaryCondition")
            if condition:
                all_conditions.append(condition)
        
        # Count condition frequencies
        condition_counts = {}
        for condition in all_conditions:
            condition_counts[condition] = condition_counts.get(condition, 0) + 1
        
        top_conditions = sorted(condition_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Calculate quarterly breakdowns
        quarterly_data = {
            "Q1": {"interactions": 0, "main_issues": [], "trend": ""},
            "Q2": {"interactions": 0, "main_issues": [], "trend": ""},
            "Q3": {"interactions": 0, "main_issues": [], "trend": ""},
            "Q4": {"interactions": 0, "main_issues": [], "trend": ""}
        }
        
        # Group all interactions by type
        all_interactions = (
            len(all_data.get('quick_scans', [])) +
            len(all_data.get('deep_dives', [])) +
            len(all_data.get('photo_analyses', [])) +
            len(all_data.get('general_assessments', [])) +
            len(all_data.get('flash_assessments', []))
        )
        
        context = f"""Generate a comprehensive annual health report for {year} analyzing ALL health data sources.

YEARLY STATISTICS:
- Total Health Interactions: {all_interactions}
- Quick Scans: {len(all_data.get('quick_scans', []))}
- Deep Dives: {len(all_data.get('deep_dives', []))}
- Symptom Tracking Entries: {len(all_data.get('symptom_tracking', []))}
- Photo Analysis Sessions: {len(all_data.get('photo_sessions', []))}
- General Assessments: {len(all_data.get('general_assessments', []))}
- Flash Assessments: {len(all_data.get('flash_assessments', []))}
- Health Stories: {len(all_data.get('health_stories', []))}
- Population Health Alerts: {len(all_data.get('population_health_alerts', []))}
- Medications Tracked: {len(all_data.get('medications', []))}
- Months with Data: {len(monthly_data)}

MONTHLY BREAKDOWN:
{json.dumps(monthly_data, indent=2)}

TOP CONDITIONS (by frequency):
{json.dumps(top_conditions, indent=2)}

SEASONAL PATTERNS:
{json.dumps(seasonal_patterns, indent=2)}

PHOTO ANALYSIS PROGRESSION (Year Overview):
{json.dumps([{
    'month': pa['created_at'][:7],
    'condition': pa['analysis_data'].get('primary_assessment'),
    'confidence': pa.get('confidence_score'),
    'trend': pa['analysis_data'].get('progression_assessment', 'stable')
} for pa in all_data.get('photo_analyses', [])[:20]], indent=2)}

MEDICATION HISTORY:
{json.dumps([{
    'medication': m.get('medication_name'),
    'started': m.get('start_date', 'Unknown'),
    'adherence': m.get('average_adherence', 'Unknown'),
    'effectiveness': m.get('effectiveness_rating', 'Unknown')
} for m in all_data.get('medications', [])], indent=2)}

TRACKING METRICS SUMMARY:
{json.dumps([{"metric": t["metric"], "data_points": len(t["data_points"]), "trend": "calculate from data"} for t in all_data.get("tracking_data", [])], indent=2)}

USER HEALTH PROFILE:
Age: {all_data.get('medical_profile', {}).get('age', 'Unknown')}
Chronic Conditions: {all_data.get('medical_profile', {}).get('chronic_conditions', [])}
Medications: {all_data.get('medical_profile', {}).get('current_medications', [])}
Allergies: {all_data.get('medical_profile', {}).get('allergies', [])}

WEARABLES DATA: {json.dumps(all_data.get('wearables', {}), indent=2) if request.include_wearables else 'Not included'}"""

        system_prompt = """Generate a comprehensive annual health report analyzing ALL health data sources. Provide deep insights, identify long-term patterns, and create actionable recommendations for the coming year.

IMPORTANT: Look for year-long trends, seasonal patterns, medication effectiveness over time, and correlations between different health aspects.

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive year in health narrative with key insights and achievements",
    "key_findings": ["major health discoveries and patterns from the year"],
    "health_journey": "detailed narrative of health evolution through the year",
    "achievements": ["health goals met", "improvements made"],
    "challenges_overcome": ["health issues resolved or managed"],
    "action_items": ["specific priorities for next year based on data"]
  },
  "yearly_metrics": {
    "total_health_interactions": 0,
    "engagement_score": "high/medium/low based on consistency",
    "most_active_months": ["top 3 months"],
    "health_complexity_score": "simple/moderate/complex"
  },
  "health_evolution": {
    "conditions_resolved": ["issues that went away"],
    "new_conditions": ["new health issues that appeared"],
    "chronic_conditions": ["ongoing issues throughout year"],
    "improvement_trajectory": {
      "overall_trend": "improving/stable/declining",
      "specific_improvements": ["what got better"],
      "specific_declines": ["what got worse"]
    }
  },
  "pattern_insights": {
    "seasonal_health": {
      "winter": ["winter-specific patterns"],
      "spring": ["spring-specific patterns"],
      "summer": ["summer-specific patterns"],
      "fall": ["fall-specific patterns"]
    },
    "monthly_patterns": {
      "best_months": ["healthiest months and why"],
      "challenging_months": ["difficult months and why"],
      "turning_points": ["key moments of change"]
    },
    "long_term_correlations": ["X seems to pop up when Y over months"]
  },
  "quarterly_analysis": {
    "Q1": {
      "health_status": "summary of Q1 health",
      "main_issues": ["primary health concerns"],
      "achievements": ["improvements made"],
      "trend": "improving/stable/declining"
    },
    "Q2": {
      "health_status": "summary of Q2 health",
      "main_issues": ["primary health concerns"],
      "achievements": ["improvements made"],
      "trend": "improving/stable/declining"
    },
    "Q3": {
      "health_status": "summary of Q3 health",
      "main_issues": ["primary health concerns"],
      "achievements": ["improvements made"],
      "trend": "improving/stable/declining"
    },
    "Q4": {
      "health_status": "summary of Q4 health",
      "main_issues": ["primary health concerns"],
      "achievements": ["improvements made"],
      "trend": "improving/stable/declining"
    },
    "quarter_over_quarter": "analysis of progression through quarters"
  },
  "body_system_review": {
    "neurological": {
      "year_summary": "comprehensive overview of neurological health",
      "total_incidents": 0,
      "frequency_trend": "increasing/stable/decreasing",
      "severity_trend": "better/same/worse",
      "main_symptoms": ["headaches", "dizziness", "etc"],
      "triggers_identified": ["stress", "sleep deprivation"],
      "treatment_effectiveness": "what worked/didn't work"
    },
    "cardiovascular": {
      "year_summary": "heart health overview",
      "total_incidents": 0,
      "frequency_trend": "trend analysis",
      "risk_factors": ["identified CV risks"],
      "protective_actions": ["exercise, diet changes"]
    },
    "respiratory": {
      "year_summary": "breathing and lung health",
      "seasonal_patterns": "worse in spring/fall",
      "environmental_triggers": ["pollution", "allergens"]
    },
    "gastrointestinal": {
      "year_summary": "digestive health overview",
      "food_triggers": ["identified problem foods"],
      "dietary_improvements": ["successful changes"]
    },
    "musculoskeletal": {
      "year_summary": "joint and muscle health",
      "activity_correlation": "pain vs exercise patterns",
      "mobility_changes": "improvements/declines"
    },
    "mental_health": {
      "year_summary": "emotional wellbeing overview",
      "stress_patterns": "work/life correlations",
      "coping_strategies": "what helped most",
      "mood_trajectory": "overall trend"
    },
    "dermatological": {
      "year_summary": "skin health if tracked",
      "photo_documented_changes": "visual progression",
      "treatment_responses": "what worked"
    }
  },
  "medication_analysis": {
    "medications_tried": ["list of all medications"],
    "effectiveness_ratings": {
      "medication_name": "highly effective/moderate/ineffective"
    },
    "adherence_analysis": {
      "average_adherence": "85%",
      "adherence_impact": "symptoms worse when missed",
      "barriers_identified": ["cost", "side effects", "forgetting"]
    },
    "optimization_opportunities": ["dose adjustments", "timing changes", "alternatives"]
  },
  "multi_modal_insights": {
    "photo_vs_symptom_correlation": "visual changes match reported symptoms",
    "assessment_consistency": "quick scans align with deep dives",
    "data_source_reliability": {
      "most_consistent": ["daily symptom tracking"],
      "most_insightful": ["deep dive sessions"],
      "most_objective": ["photo documentation"]
    }
  },
  "preventive_health_assessment": {
    "age_appropriate_screenings": ["colonoscopy at 50", "mammogram", "etc"],
    "risk_based_recommendations": ["based on family history and symptoms"],
    "vaccination_status": ["up to date/needed"],
    "lifestyle_risk_factors": ["smoking", "sedentary", "poor diet"],
    "protective_factors": ["exercise routine", "good sleep", "social support"],
    "prevention_score": "B+ (room for improvement in diet)"
  },
  "comparative_analysis": {
    "vs_previous_year": "if data available",
    "vs_population_norms": "compared to similar demographics",
    "personal_bests": ["longest symptom-free streak", "most active month"],
    "improvement_metrics": ["25% fewer headache days", "50% better sleep quality"]
  },
  "data_driven_recommendations": {
    "top_3_priorities": [
      "1. Address chronic headaches - 156 days affected",
      "2. Improve sleep consistency - affects all symptoms",
      "3. Establish exercise routine - clear correlation with wellbeing"
    ],
    "specialist_referrals": [
      {"specialty": "neurology", "reason": "chronic headaches need evaluation"},
      {"specialty": "sleep medicine", "reason": "persistent insomnia"}
    ],
    "lifestyle_modifications": [
      "Mediterranean diet - shown to reduce inflammation",
      "30 min daily walk - 40% symptom reduction on active days",
      "Meditation/mindfulness - stress is primary trigger"
    ],
    "monitoring_plan": [
      "Continue daily symptom tracking",
      "Add weekly photo documentation for skin",
      "Monthly deep dive assessments"
    ],
    "goal_setting": [
      "Reduce headache days by 50% (from 13/month to 6/month)",
      "Achieve 7+ hours sleep 5 nights/week",
      "Complete 150 minutes exercise weekly"
    ]
  },
  "year_ahead_outlook": {
    "predicted_challenges": [
      "Spring allergies likely to trigger symptoms",
      "Work stress in Q2 may impact health",
      "Winter months show historical decline"
    ],
    "opportunities": [
      "Building on Q4 improvements",
      "New medication showing promise",
      "Increased health awareness and tracking"
    ],
    "milestones": [
      "Q1: Establish exercise routine",
      "Q2: Complete specialist evaluations",
      "Q3: Reassess medication effectiveness",
      "Q4: Achieve symptom reduction goals"
    ],
    "success_metrics": "Define what success looks like for next year"
  },
  "data_quality_assessment": {
    "tracking_consistency": "87% - excellent",
    "data_completeness": {
      "symptom_tracking": "92% of days",
      "quick_scans": "weekly average",
      "deep_dives": "monthly",
      "photos": "sporadic - needs improvement"
    },
    "most_valuable_data": ["morning symptom logs", "deep dive insights"],
    "gaps_to_address": ["weekend tracking", "medication timing", "sleep quality details"],
    "tracking_recommendations": ["use app reminders", "simplify evening logs"]
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=5000  # Larger for comprehensive annual report
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Annual report generation failed. Please retry.",
                    "key_findings": [],
                    "health_journey": "Unable to generate",
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "report_type": "annual_comprehensive",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "executive_summary": report_data["executive_summary"]["one_page_summary"],
            "confidence_score": 92,
            "model_used": "tngtech/deepseek-r1t-chimera:free",
            "year": year,
            "time_range": config["time_range"]
        }
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "annual_comprehensive",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "year": year,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating annual report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/annual-summary")
async def generate_annual_summary(request: AnnualSummaryRequest):
    """Generate annual summary report"""
    try:
        analysis_response = supabase.table("report_analyses")\
            .select("*")\
            .eq("id", request.analysis_id)\
            .execute()
        
        if not analysis_response.data:
            return {"error": "Analysis not found", "status": "error"}
        
        analysis = analysis_response.data[0]
        
        # Override config for annual scope
        year = request.year or datetime.now().year
        annual_range = {
            "start": f"{year}-01-01T00:00:00Z",
            "end": f"{year}-12-31T23:59:59Z"
        }
        
        config = {
            "time_range": annual_range,
            "data_sources": {"quick_scans": [], "deep_dives": []}
        }
        
        # Get all data for the year
        scan_response = supabase.table("quick_scans")\
            .select("*")\
            .eq("user_id", str(request.user_id))\
            .gte("created_at", annual_range["start"])\
            .lte("created_at", annual_range["end"])\
            .execute()
        
        dive_response = supabase.table("deep_dive_sessions")\
            .select("*")\
            .eq("user_id", str(request.user_id))\
            .eq("status", "completed")\
            .gte("created_at", annual_range["start"])\
            .lte("created_at", annual_range["end"])\
            .execute()
        
        symptom_response = supabase.table("symptom_tracking")\
            .select("*")\
            .eq("user_id", str(request.user_id))\
            .gte("created_at", annual_range["start"])\
            .lte("created_at", annual_range["end"])\
            .execute()
        
        quick_scans = scan_response.data or []
        deep_dives = dive_response.data or []
        symptoms = symptom_response.data or []
        
        # Build annual context
        context = f"""Generate an annual health summary for {year}.

Annual Statistics:
- Total Quick Scans: {len(quick_scans)}
- Total Deep Dives: {len(deep_dives)}
- Symptom Entries: {len(symptoms)}

Conditions Assessed:
{json.dumps([s.get('analysis_result', {}).get('primaryCondition') for s in quick_scans if s.get('analysis_result', {}).get('primaryCondition')], indent=2)}

Symptom Frequency:
{json.dumps({}, indent=2)}

Seasonal Patterns: {len([s for s in symptoms if '01' in s.get('created_at', '')[:7] or '02' in s.get('created_at', '')[:7] or '12' in s.get('created_at', '')[:7]])} winter entries, {len([s for s in symptoms if '06' in s.get('created_at', '')[:7] or '07' in s.get('created_at', '')[:7] or '08' in s.get('created_at', '')[:7]])} summer entries"""

        system_prompt = """Generate an annual health summary. Return JSON:
{
  "executive_summary": {
    "one_page_summary": "Complete year overview",
    "key_findings": ["major health insights"],
    "action_items": ["recommendations for next year"]
  },
  "yearly_overview": {
    "total_assessments": 0,
    "most_common_concerns": ["top health issues"],
    "health_trends": {
      "improving_areas": ["areas of improvement"],
      "concerning_trends": ["areas needing attention"],
      "stable_conditions": ["stable health aspects"]
    },
    "seasonal_patterns": {
      "winter_issues": ["winter health patterns"],
      "summer_concerns": ["summer health patterns"],
      "year_round_stable": ["consistent health aspects"]
    }
  },
  "health_metrics": {
    "symptom_frequency": {},
    "severity_averages": {},
    "improvement_tracking": {
      "symptoms_resolved": ["resolved issues"],
      "new_symptoms": ["new health concerns"],
      "chronic_patterns": ["ongoing health patterns"]
    }
  },
  "preventive_recommendations": {
    "screening_due": ["recommended screenings"],
    "lifestyle_goals": ["health goals for next year"],
    "monitoring_priorities": ["key areas to monitor"],
    "specialist_referrals": ["specialist consultations needed"]
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
            max_tokens=2500
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": f"Annual health summary for {year} could not be generated.",
                    "key_findings": [],
                    "action_items": ["Schedule annual physical exam"]
                },
                "yearly_overview": {
                    "total_assessments": len(quick_scans) + len(deep_dives),
                    "most_common_concerns": [],
                    "health_trends": {},
                    "seasonal_patterns": {}
                },
                "health_metrics": {},
                "preventive_recommendations": {}
            }
        
        # Update total assessments
        if "yearly_overview" in report_data:
            report_data["yearly_overview"]["total_assessments"] = len(quick_scans) + len(deep_dives)
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "analysis_id": request.analysis_id,
            "report_type": "annual_summary",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "executive_summary": report_data["executive_summary"]["one_page_summary"],
            "confidence_score": 88,
            "model_used": "tngtech/deepseek-r1t-chimera:free",
            "year": year
        }
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "annual_summary",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "year": year,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating annual summary: {e}")
        return {"error": str(e), "status": "error"}