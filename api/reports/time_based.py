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
    
    return {
        "quick_scans": scans.data or [],
        "deep_dives": dives.data or [],
        "symptom_tracking": tracking.data or [],
        "tracking_data": tracking_data,
        "llm_summaries": chats.data or [],
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
        
        context = f"""Generate a 30-day comprehensive health report.

TIME PERIOD: {start_date.strftime('%B %d')} to {end_date.strftime('%B %d, %Y')}

ACTIVITY SUMMARY:
- Total Quick Scans: {len(all_data.get('quick_scans', []))}
- Total Deep Dives: {len(all_data.get('deep_dives', []))}
- Symptom Tracking Entries: {len(all_data.get('symptom_tracking', []))}
- LLM Chat Sessions: {len(all_data.get('llm_summaries', []))}

WEEKLY BREAKDOWN:
{json.dumps(weekly_data, indent=2)}

TOP SYMPTOMS (by frequency):
{json.dumps(symptom_freq[:10], indent=2)}

PATTERN DATA:
{json.dumps(patterns[:20], indent=2)}

WEARABLES DATA: {json.dumps(all_data.get('wearables', {}), indent=2) if request.include_wearables else 'Not included'}"""

        system_prompt = """Generate a 30-day aggregate health report. This report should synthesize ALL health data from the past 30 days.

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive 30-day health overview",
    "key_findings": ["major insights from the period"],
    "patterns_identified": ["seems to pop up when patterns"],
    "action_items": ["recommendations based on patterns"]
  },
  "period_overview": {
    "total_health_interactions": 0,
    "most_active_week": "Week X",
    "primary_concerns": ["top 3-5 health issues"],
    "improvement_areas": ["symptoms that improved"],
    "worsening_areas": ["symptoms that worsened"],
    "stable_conditions": ["unchanged patterns"]
  },
  "pattern_analysis": {
    "temporal_patterns": {
      "time_of_day": ["morning symptoms", "evening symptoms"],
      "day_of_week": ["weekday vs weekend patterns"],
      "weekly_trends": ["week-over-week changes"]
    },
    "correlation_patterns": {
      "symptom_triggers": ["X seems to pop up when Y"],
      "environmental_factors": ["weather, stress, activity correlations"],
      "comorbidity_patterns": ["symptoms that occur together"]
    },
    "severity_analysis": {
      "average_severity": 0,
      "severity_trend": "improving/worsening/stable",
      "high_severity_events": ["dates and details of severe symptoms"]
    }
  },
  "detailed_findings": {
    "by_body_system": {
      "neurological": ["headaches, dizziness findings"],
      "cardiovascular": ["chest pain, palpitations findings"],
      "respiratory": ["breathing issues findings"],
      "gastrointestinal": ["digestive findings"],
      "musculoskeletal": ["pain, mobility findings"]
    },
    "by_symptom_type": {
      "pain": {"frequency": 0, "average_severity": 0, "locations": []},
      "fatigue": {"frequency": 0, "patterns": []},
      "other_symptoms": {}
    }
  },
  "predictive_insights": {
    "emerging_patterns": ["patterns that are developing"],
    "risk_indicators": ["concerning trends"],
    "preventive_opportunities": ["ways to prevent issues"]
  },
  "recommendations": {
    "immediate_actions": ["urgent items if any"],
    "lifestyle_modifications": ["based on patterns"],
    "monitoring_priorities": ["what to track closely"],
    "specialist_consultations": ["if patterns suggest need"],
    "follow_up_timeline": "suggested next steps"
  },
  "data_quality_metrics": {
    "data_completeness": "percentage of days with data",
    "consistency_score": "how consistent tracking has been",
    "areas_needing_data": ["what's missing"]
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
        
        context = f"""Generate a comprehensive annual health report for {year}.

YEARLY STATISTICS:
- Total Health Interactions: {total_interactions}
- Quick Scans: {len(all_data.get('quick_scans', []))}
- Deep Dives: {len(all_data.get('deep_dives', []))}
- Symptom Tracking Entries: {len(all_data.get('symptom_tracking', []))}
- Months with Data: {len(monthly_data)}

MONTHLY BREAKDOWN:
{json.dumps(monthly_data, indent=2)}

TOP CONDITIONS (by frequency):
{json.dumps(top_conditions, indent=2)}

SEASONAL PATTERNS:
{json.dumps(seasonal_patterns, indent=2)}

TRACKING DATA:
{json.dumps([{"metric": t["metric"], "points": len(t["data_points"])} for t in all_data.get("tracking_data", [])], indent=2)}

WEARABLES DATA: {json.dumps(all_data.get('wearables', {}), indent=2) if request.include_wearables else 'Not included'}"""

        system_prompt = """Generate a comprehensive annual health report. This report should provide deep insights into health patterns over the entire year.

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Complete year in health overview",
    "key_findings": ["major health insights from the year"],
    "health_journey": "narrative of health changes through the year",
    "action_items": ["priorities for next year"]
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
  "body_system_review": {
    "neurological": {
      "year_summary": "overview",
      "frequency_trend": "increasing/stable/decreasing",
      "severity_trend": "better/same/worse"
    },
    "cardiovascular": {},
    "respiratory": {},
    "gastrointestinal": {},
    "musculoskeletal": {},
    "mental_health": {}
  },
  "preventive_health_assessment": {
    "screening_recommendations": ["based on age and risk factors"],
    "vaccination_reminders": ["flu, covid, others"],
    "lifestyle_risk_factors": ["identified risks"],
    "protective_factors": ["positive health behaviors"]
  },
  "data_driven_recommendations": {
    "top_3_priorities": ["most important focus areas"],
    "specialist_referrals": ["based on year's data"],
    "lifestyle_modifications": ["evidence-based suggestions"],
    "monitoring_plan": ["what to track in coming year"],
    "goal_setting": ["SMART goals for health"]
  },
  "year_ahead_outlook": {
    "predicted_challenges": ["based on patterns"],
    "opportunities": ["for health improvement"],
    "milestones": ["health goals to achieve"]
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