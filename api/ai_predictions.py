"""AI Predictions API endpoints for dashboard alerts and predictive insights"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
import json
import logging
import uuid
from services.ai_health_analyzer import HealthAnalyzer
from supabase_client import supabase
from utils.data_gathering import gather_prediction_data
from utils.json_parser import extract_json_from_text
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/ai", tags=["ai-predictions"])
logger = logging.getLogger(__name__)

# Create a wrapper class for AI analysis
class AIHealthAnalyzer(HealthAnalyzer):
    async def analyze_with_llm(self, prompt: str, model: str = None) -> str:
        """Wrapper method for LLM analysis"""
        if model:
            self.model = model
        result = await self._call_ai(prompt)
        return json.dumps(result) if isinstance(result, dict) else result

ai_analyzer = AIHealthAnalyzer()

# Request/Response Models
class UserPreferences(BaseModel):
    weekly_generation_enabled: bool = True
    preferred_day_of_week: int = 3  # Wednesday
    preferred_hour: int = 17  # 5 PM
    timezone: str = "UTC"

# Helper function to extract JSON from AI response
def safe_parse_json(response: Any, context: str = "") -> Any:
    """Safely parse JSON from AI response with logging"""
    try:
        # If it's already a dict or list, return it directly
        if isinstance(response, (dict, list)):
            logger.info(f"AI Response for {context}: Already parsed as {type(response).__name__}")
            return response
        
        # Log the raw response for debugging
        logger.info(f"AI Response for {context}: {str(response)[:500]}...")
        
        # If it's a string, try to parse it
        if isinstance(response, str):
            # Try to extract JSON using the utility
            extracted = extract_json_from_text(response)
            if extracted:
                return extracted
            
            # Try parsing as is
            return json.loads(response)
        
        # If it's neither dict/list nor string, log and return None
        logger.warning(f"Unexpected response type for {context}: {type(response)}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to parse JSON for {context}: {str(e)}")
        logger.error(f"Raw response: {response}")
        return None

# Gradient mapping for severity levels
def get_gradient_for_severity(severity: str) -> str:
    """Returns gradient CSS class for severity level"""
    gradients = {
        "info": "from-blue-600/10 to-cyan-600/10",
        "warning": "from-yellow-600/10 to-orange-600/10",
        "alert": "from-red-600/10 to-orange-600/10",
        "critical": "from-red-600/10 to-pink-600/10"
    }
    return gradients.get(severity, "from-gray-600/10 to-slate-600/10")


@router.get("/dashboard-alert/{user_id}")
async def get_dashboard_alert(user_id: str):
    """
    Get the single most important alert for the dashboard
    """
    try:
        logger.info(f"Generating dashboard alert for user {user_id}")
        
        # Gather recent data
        data = await gather_prediction_data(user_id, "dashboard")
        
        # Check if user has enough data
        if data.get("data_quality", 0) < 20:
            logger.info(f"Insufficient data for user {user_id}: quality score {data.get('data_quality', 0)}")
            return {"alert": None, "reason": "insufficient_data", "data_quality": data.get("data_quality", 0)}
        
        # Create summarized context for AI
        context = {
            "recent_symptoms": data["symptom_tracking"]["symptom_frequency"],
            "severity_trend": data["symptom_tracking"]["severity_trends"],
            "sleep_average": data["sleep_patterns"]["average_hours"],
            "stress_levels": data["mood_patterns"]["stress_levels"][-7:] if data["mood_patterns"]["stress_levels"] else [],
            "urgency_distribution": data["quick_scans"]["urgency_distribution"],
            "current_date": data["current_date"],
            "day_of_week": data["day_of_week"]
        }
        
        prompt = f"""
        Analyze this user's health data and generate ONE most important predictive alert.
        
        Context:
        {json.dumps(context, indent=2)}
        
        Generate ONE alert if there's a meaningful pattern. Be vague enough to not be easily disproven.
        Focus on increased risks or concerning patterns, not specific predictions.
        
        IMPORTANT: Return ONLY valid JSON, no other text or formatting.
        Return ONLY a JSON object:
        {{
            "severity": "info" or "warning" or "critical",
            "title": "Clear but general title (max 10 words)",
            "description": "2-3 sentences about the pattern and what to watch for",
            "timeframe": "General timeframe like 'next few days' or 'this week'",
            "confidence": 60-90,
            "preventionTip": "One immediate action they can take"
        }}
        
        If no significant patterns, return null.
        
        Example:
        {{
            "severity": "warning",
            "title": "Stress-Related Symptom Risk Increasing",
            "description": "Your stress levels combined with recent sleep patterns suggest increased vulnerability to symptoms. Watch for early warning signs.",
            "timeframe": "Over the next few days",
            "confidence": 75,
            "preventionTip": "Start stress reduction techniques now and prioritize sleep hygiene"
        }}
        """
        
        try:
            response = await ai_analyzer.analyze_with_llm(
                prompt=prompt,
                model="deepseek/deepseek-chat"
            )
            
            alert_data = safe_parse_json(response, "dashboard_alert")
            
            if alert_data and alert_data != "null" and isinstance(alert_data, dict):
                # Add metadata
                alert_data["id"] = str(uuid.uuid4())
                alert_data["actionUrl"] = f"/predictive-insights?focus={alert_data['id']}"
                alert_data["generated_at"] = datetime.now().isoformat()
                
                # Log for analytics and save to database
                await log_alert_generation(user_id, alert_data)
                
                # Ensure weekly predictions exist and save
                try:
                    prediction_id = await ensure_weekly_predictions_exist(user_id)
                    if prediction_id:
                        supabase.table('weekly_ai_predictions').update({
                            'dashboard_alert': alert_data,
                            'updated_at': datetime.now().isoformat()
                        }).eq('id', prediction_id).execute()
                except Exception as weekly_error:
                    logger.warning(f"Failed to update weekly predictions: {str(weekly_error)}")
                
                logger.info(f"Successfully generated alert for user {user_id}")
                return {"alert": alert_data, "status": "success"}
            else:
                logger.info(f"No significant patterns found for user {user_id}")
                return {"alert": None, "status": "no_patterns"}
        
        except Exception as ai_error:
            logger.error(f"AI analysis failed for user {user_id}: {str(ai_error)}")
            # Return a fallback alert based on available data
            if data["symptom_tracking"]["total_entries"] > 5:
                fallback_alert = {
                    "id": str(uuid.uuid4()),
                    "severity": "info",
                    "title": "Health Tracking Active",
                    "description": "Continue monitoring your symptoms for pattern detection. More data will enable personalized insights.",
                    "timeframe": "Ongoing",
                    "confidence": 60,
                    "preventionTip": "Keep tracking daily for best results",
                    "generated_at": datetime.now().isoformat(),
                    "is_fallback": True
                }
                return {"alert": fallback_alert, "status": "fallback"}
            
            return {"alert": None, "status": "error", "error": str(ai_error)}
        
    except Exception as e:
        logger.error(f"Error generating dashboard alert: {str(e)}", exc_info=True)
        return {"alert": None, "status": "error", "error": str(e)}


@router.get("/predictions/immediate/{user_id}")
async def get_immediate_predictions(user_id: str):
    """
    Generate predictions for the next 7 days
    """
    try:
        logger.info(f"Generating immediate predictions for user {user_id}")
        
        # Gather recent data
        data = await gather_prediction_data(user_id, "immediate")
        
        if data.get("data_quality", 0) < 30:
            logger.info(f"Insufficient data for predictions: quality score {data.get('data_quality', 0)}")
            return {
                "predictions": [],
                "message": "Need more health data for accurate predictions",
                "data_quality_score": data.get("data_quality", 0),
                "status": "insufficient_data"
            }
        
        # Prepare context
        context = {
            "symptom_frequency": data["symptom_tracking"]["symptom_frequency"],
            "top_symptoms": list(data["symptom_tracking"]["symptom_frequency"].keys())[:5],
            "severity_trend": data["symptom_tracking"]["severity_trends"],
            "body_parts": list(data["quick_scans"]["body_part_frequency"].keys())[:3],
            "sleep_average": data["sleep_patterns"]["average_hours"],
            "sleep_trend": data["sleep_patterns"]["quality_trend"],
            "stress_recent": data["mood_patterns"]["stress_levels"][-7:] if data["mood_patterns"]["stress_levels"] else [],
            "current_day": data["day_of_week"],
            "medication_compliance": data["medication_adherence"]["compliance_rate"]
        }
        
        prompt = f"""
        Analyze this health data and generate 2-4 predictions for the next 7 days.
        
        Data:
        {json.dumps(context, indent=2)}
        
        Generate predictions that are:
        - General enough to not be easily disproven (avoid specific days/times)
        - Based on actual patterns in the data
        - Focused on "increased risk" rather than certainties
        - Include actionable prevention steps
        
        IMPORTANT: Return ONLY a valid JSON array, no other text or formatting.
        Return a JSON array of predictions. Each should have:
        {{
            "title": "Risk/pattern title",
            "subtitle": "Brief description",
            "pattern": "The pattern you detected",
            "trigger_combo": "What combination of factors",
            "historical_accuracy": "Percentage as string like '75%'",
            "confidence": 60-90,
            "prevention_protocol": ["4 specific numbered action steps"]
        }}
        
        Example:
        [{{
            "title": "Migraine Risk Building",
            "subtitle": "Watch for migraine conditions in the next few days",
            "pattern": "Stress accumulation + sleep disruption pattern",
            "trigger_combo": "Your typical pre-migraine pattern detected",
            "historical_accuracy": "82%",
            "confidence": 82,
            "prevention_protocol": [
                "Increase water intake by 40% starting today",
                "Maintain consistent sleep schedule (±30 minutes)",
                "Consider preventive medication timing adjustment",
                "Avoid known dietary triggers"
            ]
        }}]
        """
        
        try:
            response = await ai_analyzer.analyze_with_llm(
                prompt=prompt,
                model="deepseek/deepseek-chat"
            )
            
            predictions_data = safe_parse_json(response, "immediate_predictions")
            
            if predictions_data and isinstance(predictions_data, list):
                # Enrich predictions
                enriched_predictions = []
                for pred in predictions_data:
                    if isinstance(pred, dict) and "title" in pred:
                        pred["id"] = str(uuid.uuid4())
                        pred["type"] = "immediate"
                        pred["gradient"] = get_gradient_for_severity("warning")
                        pred["generated_at"] = datetime.now().isoformat()
                        enriched_predictions.append(pred)
                        
                        # Save to history
                        try:
                            supabase.table('ai_predictions_history').insert({
                                'user_id': user_id,
                                'prediction_type': 'immediate',
                                'prediction_data': pred,
                                'confidence': pred.get('confidence', 70),
                                'generated_at': datetime.now().isoformat()
                            }).execute()
                        except Exception as db_error:
                            logger.warning(f"Failed to save prediction to history: {str(db_error)}")
                
                # Update weekly predictions if exists
                try:
                    current_weekly = supabase.table('weekly_ai_predictions').select('id, predictions').eq(
                        'user_id', user_id
                    ).eq('is_current', True).execute()
                    
                    if current_weekly.data:
                        supabase.table('weekly_ai_predictions').update({
                            'predictions': enriched_predictions,
                            'data_quality_score': data.get("data_quality", 0),
                            'updated_at': datetime.now().isoformat()
                        }).eq('id', current_weekly.data[0]['id']).execute()
                except Exception as weekly_error:
                    logger.warning(f"Failed to update weekly predictions: {str(weekly_error)}")
                
                logger.info(f"Successfully generated {len(enriched_predictions)} predictions for user {user_id}")
                return {
                    "predictions": enriched_predictions,
                    "generated_at": datetime.now().isoformat(),
                    "data_quality_score": data.get("data_quality", 0),
                    "status": "success"
                }
            else:
                logger.warning(f"Invalid predictions format for user {user_id}")
                # Generate fallback predictions based on available data
                if context["top_symptoms"]:
                    fallback_predictions = [{
                        "id": str(uuid.uuid4()),
                        "title": "Symptom Pattern Monitoring",
                        "subtitle": f"Watch for changes in your {context['top_symptoms'][0]} symptoms",
                        "pattern": "Based on recent tracking history",
                        "trigger_combo": "Historical symptom patterns",
                        "historical_accuracy": "Building baseline",
                        "confidence": 65,
                        "prevention_protocol": [
                            "Continue daily symptom tracking",
                            "Note any triggers or patterns",
                            "Maintain consistent self-care routine",
                            "Stay hydrated and well-rested"
                        ],
                        "type": "immediate",
                        "gradient": get_gradient_for_severity("info"),
                        "generated_at": datetime.now().isoformat(),
                        "is_fallback": True
                    }]
                    
                    return {
                        "predictions": fallback_predictions,
                        "generated_at": datetime.now().isoformat(),
                        "data_quality_score": data.get("data_quality", 0),
                        "status": "fallback"
                    }
                
                return {
                    "predictions": [],
                    "generated_at": datetime.now().isoformat(),
                    "data_quality_score": data.get("data_quality", 0),
                    "status": "parse_error"
                }
        
        except Exception as ai_error:
            logger.error(f"AI analysis failed for immediate predictions: {str(ai_error)}")
            return {
                "predictions": [],
                "generated_at": datetime.now().isoformat(),
                "data_quality_score": data.get("data_quality", 0),
                "status": "ai_error",
                "error": str(ai_error)
            }
        
    except Exception as e:
        logger.error(f"Error generating immediate predictions: {str(e)}", exc_info=True)
        return {"predictions": [], "status": "error", "error": str(e)}


@router.get("/predictions/seasonal/{user_id}")
async def get_seasonal_predictions(user_id: str):
    """
    Generate seasonal predictions for the next 3 months
    """
    try:
        # Gather seasonal data
        data = await gather_prediction_data(user_id, "seasonal")
        
        if data.get("data_quality", 0) < 20:
            return {
                "predictions": [],
                "current_season": data.get("season", "unknown"),
                "message": "Need more historical data for seasonal predictions"
            }
        
        context = {
            "current_season": data["season"],
            "upcoming_season": data.get("upcoming_season", {}),
            "seasonal_history": data.get("seasonal_history", {}),
            "weather_sensitivity": data.get("weather_sensitivity", {}),
            "common_symptoms": data["symptom_tracking"]["symptom_frequency"],
            "medical_profile": {
                "allergies": data["medical_profile"].get("allergies", []) if data["medical_profile"] else [],
                "conditions": data.get("chronic_conditions", [])
            }
        }
        
        prompt = f"""
        Generate 1-3 seasonal health predictions for the next 3 months.
        
        Current context:
        {json.dumps(context, indent=2)}
        
        Focus on:
        - Seasonal transitions and their typical effects
        - Weather-related patterns if user shows sensitivity
        - Vitamin D and daylight changes
        - Seasonal allergies if relevant
        - General seasonal wellness patterns
        
        IMPORTANT: Return ONLY a valid JSON array, no other text or formatting.
        Return JSON array where each prediction has:
        {{
            "title": "Seasonal pattern title",
            "subtitle": "Brief description",
            "pattern": "What seasonal pattern affects them",
            "timeframe": "General timeframe like 'February-March'",
            "confidence": 60-85,
            "prevention_protocol": ["4-5 specific prevention steps"],
            "historical_context": "General statement about this pattern"
        }}
        
        Example:
        [{{
            "title": "Late Winter Energy Dip",
            "subtitle": "Seasonal energy dip approaching",
            "pattern": "Reduced daylight exposure + vitamin D depletion",
            "timeframe": "Late February through March",
            "confidence": 75,
            "prevention_protocol": [
                "Start vitamin D supplementation (2000 IU daily)",
                "Morning light exposure 20-30 minutes",
                "Consider light therapy box for cloudy days",
                "Schedule energizing activities for mornings",
                "Maintain consistent sleep schedule despite darkness"
            ],
            "historical_context": "Common pattern in northern climates during winter months"
        }}]
        """
        
        response = await ai_analyzer.analyze_with_llm(
            prompt=prompt,
            model="qwen/qwen-2.5-coder-32b-instruct"  # Using Kimi K1.5 for better pattern analysis
        )
        
        predictions_data = safe_parse_json(response, "seasonal_predictions")
        
        if predictions_data and isinstance(predictions_data, list):
            # Enrich predictions
            for pred in predictions_data:
                pred["id"] = str(uuid.uuid4())
                pred["type"] = "seasonal"
                pred["gradient"] = "from-blue-600/10 to-indigo-600/10"
                pred["generated_at"] = datetime.now().isoformat()
            
            return {
                "predictions": predictions_data,
                "current_season": data["season"],
                "next_season_transition": data.get("upcoming_season", {}).get("transition_date")
            }
        
        return {
            "predictions": [],
            "current_season": data["season"],
            "parse_error": True
        }
        
    except Exception as e:
        logger.error(f"Error generating seasonal predictions: {str(e)}")
        return {"predictions": [], "error": str(e)}


@router.get("/predictions/longterm/{user_id}")
async def get_longterm_trajectory(user_id: str):
    """
    Generate long-term health trajectory assessments
    """
    try:
        # Gather comprehensive data
        data = await gather_prediction_data(user_id, "longterm")
        
        if data.get("data_quality", 0) < 40:
            return {
                "assessments": [],
                "message": "Need more comprehensive data for long-term assessments"
            }
        
        context = {
            "medical_profile": data["medical_profile"] or {},
            "chronic_conditions": data.get("chronic_conditions", []),
            "risk_factors": data.get("risk_factors", {}),
            "historical_patterns": data.get("historical_patterns", {}),
            "symptom_frequency": data["symptom_tracking"]["symptom_frequency"],
            "medication_compliance": data["medication_adherence"]["compliance_rate"],
            "lifestyle": {
                "sleep_average": data["sleep_patterns"]["average_hours"],
                "stress_frequency": len(data["mood_patterns"]["stress_levels"])
            }
        }
        
        prompt = f"""
        Generate 1-2 long-term health trajectory assessments based on this data.
        
        User context:
        {json.dumps(context, indent=2)}
        
        Focus on major health areas where you see patterns or risks.
        Be constructive and focus on improvement potential.
        
        IMPORTANT: Return ONLY a valid JSON array, no other text or formatting.
        Return JSON array where each assessment has:
        {{
            "condition": "Health area being assessed",
            "current_status": "Brief current state description",
            "risk_factors": ["List of 2-4 relevant risk factors"],
            "trajectory": {{
                "current_path": {{
                    "description": "Where they're headed now",
                    "risk_level": "low/moderate/high",
                    "projected_outcome": "Likely outcome if unchanged"
                }},
                "optimized_path": {{
                    "description": "Where they could be",
                    "risk_level": "low/moderate",
                    "requirements": ["What it takes to get there"]
                }}
            }},
            "prevention_strategy": ["4-5 specific long-term strategies"],
            "confidence": 70-85,
            "data_basis": "What this assessment is based on"
        }}
        
        Example:
        [{{
            "condition": "Cardiovascular Health",
            "current_status": "Managing stress-related blood pressure concerns",
            "risk_factors": [
                "Chronic work stress",
                "Irregular sleep patterns",
                "Family history considerations"
            ],
            "trajectory": {{
                "current_path": {{
                    "description": "Gradual increase in cardiovascular strain",
                    "risk_level": "moderate",
                    "projected_outcome": "May require medical intervention within 2-3 years"
                }},
                "optimized_path": {{
                    "description": "Significant risk reduction achievable",
                    "risk_level": "low",
                    "requirements": ["Lifestyle modifications", "Stress management", "Regular monitoring"]
                }}
            }},
            "prevention_strategy": [
                "Implement daily 30-minute walks (reduces BP by 5-10 points)",
                "Mediterranean diet adoption (30% risk reduction proven)",
                "Structured stress management program",
                "Sleep optimization to 7-8 hours consistently",
                "Quarterly health monitoring"
            ],
            "confidence": 78,
            "data_basis": "Based on 6 months of symptom patterns and lifestyle data"
        }}]
        """
        
        response = await ai_analyzer.analyze_with_llm(
            prompt=prompt,
            model="qwen/qwen-2.5-coder-32b-instruct"  # Using Kimi K1.5 for better pattern analysis
        )
        
        assessments_data = safe_parse_json(response, "longterm_assessments")
        
        if assessments_data and isinstance(assessments_data, list):
            # Enrich assessments
            for assessment in assessments_data:
                assessment["id"] = str(uuid.uuid4())
                assessment["generated_at"] = datetime.now().isoformat()
            
            # Determine overall trajectory
            risk_levels = [a["trajectory"]["current_path"]["risk_level"] for a in assessments_data]
            if "high" in risk_levels:
                overall = "needs_attention"
            elif "moderate" in risk_levels:
                overall = "stable_with_improvement_potential"
            else:
                overall = "positive"
            
            return {
                "assessments": assessments_data,
                "overall_health_trajectory": overall,
                "key_focus_areas": [a["condition"].lower().replace(" ", "_") for a in assessments_data]
            }
        
        return {
            "assessments": [],
            "parse_error": True
        }
        
    except Exception as e:
        logger.error(f"Error generating long-term trajectory: {str(e)}")
        return {"assessments": [], "error": str(e)}


@router.get("/patterns/{user_id}")
async def get_body_patterns(user_id: str):
    """
    Generate personalized body pattern insights
    """
    try:
        logger.info(f"Generating body patterns for user {user_id}")
        
        # Gather pattern data
        data = await gather_prediction_data(user_id, "patterns")
        
        if data.get("data_quality", 0) < 30:
            logger.info(f"Insufficient data for patterns: quality score {data.get('data_quality', 0)}")
            return {
                "tendencies": ["Track your symptoms for a week to discover patterns"],
                "positive_responses": ["Log what makes you feel better"],
                "pattern_metadata": {
                    "total_patterns_analyzed": 0,
                    "confidence_level": "low",
                    "data_span_days": 0
                },
                "status": "insufficient_data"
            }
        
        # Create comprehensive pattern context
        context = {
            "symptom_patterns": data["symptom_tracking"]["symptom_frequency"],
            "severity_trends": data["symptom_tracking"]["severity_trends"],
            "body_parts": data["quick_scans"]["body_part_frequency"],
            "sleep_data": {
                "average": data["sleep_patterns"]["average_hours"],
                "trend": data["sleep_patterns"]["quality_trend"]
            },
            "mood_patterns": {
                "average": data["mood_patterns"]["average_mood"],
                "stress_days": len(data["mood_patterns"]["stress_levels"])
            },
            "medication_compliance": data["medication_adherence"]["compliance_rate"],
            "day_patterns": analyze_day_patterns(data)
        }
        
        prompt = f"""
        Analyze these health patterns and create two lists of highly specific, personalized insights.
        
        User patterns:
        {json.dumps(context, indent=2)}
        
        Generate:
        1. "tendencies" - 6 VERY SPECIFIC patterns with exact timing and triggers:
           - Include specific timeframes (e.g., "48-72 hours after", "on Sunday evenings")
           - Add context in parentheses (e.g., "(work anticipation)", "(light sensitivity)")
           - Be specific about triggers, timing, and circumstances
           - Focus on surprising or non-obvious patterns
        
        2. "positiveResponses" - 6 SPECIFIC things that help, with details:
           - Include specific parameters (e.g., "±30 min", "not intense")
           - Be precise about what works and why
           - Include timing and dosage where relevant
        
        Write in second person. Be SPECIFIC and DETAILED.
        
        IMPORTANT: Return ONLY valid JSON, no other text or formatting.
        Return JSON:
        {{
            "tendencies": [
                "Get migraines 48-72 hours after high stress events",
                "Feel anxious on Sunday evenings (work anticipation)",
                "Sleep poorly during full moons (light sensitivity)",
                "Experience energy crashes when skipping breakfast",
                "Feel your best after morning walks",
                "Have sinus pressure before weather changes"
            ],
            "positiveResponses": [
                "Consistent sleep schedule (±30 min)",
                "Regular meal timing",
                "Moderate exercise (not intense)",
                "Stress reduction techniques",
                "Morning sunlight exposure",
                "Hydration consistency"
            ]
        }}
        """
        
        try:
            response = await ai_analyzer.analyze_with_llm(
                prompt=prompt,
                model="moonshotai/kimi-k2"  # Using Kimi K2 for better pattern analysis
            )
            
            patterns_data = safe_parse_json(response, "body_patterns")
            
            if patterns_data and isinstance(patterns_data, dict) and "tendencies" in patterns_data and "positiveResponses" in patterns_data:
                result_data = {
                    "tendencies": patterns_data["tendencies"],
                    "positive_responses": patterns_data["positiveResponses"],
                    "pattern_metadata": {
                        "total_patterns_analyzed": len(data["symptom_tracking"]["entries"]),
                        "confidence_level": "high" if data["data_quality"] > 70 else "medium",
                        "data_span_days": data["time_window"]["days"],
                        "generated_at": datetime.now().isoformat()
                    }
                }
                
                # Save to weekly predictions if exists
                try:
                    current_weekly = supabase.table('weekly_ai_predictions').select('id').eq(
                        'user_id', user_id
                    ).eq('is_current', True).execute()
                    
                    if current_weekly.data:
                        supabase.table('weekly_ai_predictions').update({
                            'body_patterns': {
                                'tendencies': patterns_data["tendencies"],
                                'positiveResponses': patterns_data["positiveResponses"]
                            },
                            'updated_at': datetime.now().isoformat()
                        }).eq('id', current_weekly.data[0]['id']).execute()
                except Exception as weekly_error:
                    logger.warning(f"Failed to update weekly predictions: {str(weekly_error)}")
                
                logger.info(f"Successfully generated body patterns for user {user_id}")
                return {**result_data, "status": "success"}
            else:
                logger.warning(f"Invalid patterns format for user {user_id}")
                # Generate fallback patterns based on available data
                if context["symptom_patterns"]:
                    top_symptoms = list(context["symptom_patterns"].keys())[:3]
                    fallback_data = {
                        "tendencies": [
                            f"You've tracked {top_symptoms[0]} most frequently",
                            "Your symptoms vary throughout the week",
                            "Pattern analysis is building with more data",
                            "Keep tracking to identify specific triggers",
                            "Your health data shows active monitoring"
                        ],
                        "positive_responses": [
                            "Regular tracking helps identify patterns",
                            "Your awareness of symptoms is improving",
                            "Consistent monitoring enables better insights",
                            "Each data point helps build your profile"
                        ],
                        "pattern_metadata": {
                            "total_patterns_analyzed": len(data["symptom_tracking"]["entries"]),
                            "confidence_level": "building",
                            "data_span_days": data["time_window"]["days"],
                            "generated_at": datetime.now().isoformat()
                        },
                        "status": "fallback"
                    }
                    
                    return fallback_data
                
                # Final fallback
                return {
                    "tendencies": [
                        "Patterns are still being analyzed",
                        "Continue tracking to reveal your unique patterns"
                    ],
                    "positive_responses": [
                        "Your data will reveal what works best for you"
                    ],
                    "pattern_metadata": {
                        "total_patterns_analyzed": 0,
                        "confidence_level": "low",
                        "data_span_days": 0
                    },
                    "status": "minimal_data"
                }
        
        except Exception as ai_error:
            logger.error(f"AI analysis failed for body patterns: {str(ai_error)}")
            # Return basic patterns from raw data
            if data["symptom_tracking"]["symptom_frequency"]:
                return {
                    "tendencies": [
                        "Your symptom patterns are being analyzed",
                        f"Most common symptom: {list(data['symptom_tracking']['symptom_frequency'].keys())[0]}",
                        "Continue tracking for personalized insights"
                    ],
                    "positive_responses": [
                        "Regular health tracking shows commitment",
                        "Building a comprehensive health profile"
                    ],
                    "pattern_metadata": {
                        "total_patterns_analyzed": len(data["symptom_tracking"]["entries"]),
                        "confidence_level": "low",
                        "data_span_days": data["time_window"]["days"]
                    },
                    "status": "ai_error"
                }
            
            return {
                "tendencies": [],
                "positive_responses": [],
                "pattern_metadata": {
                    "total_patterns_analyzed": 0,
                    "confidence_level": "error",
                    "data_span_days": 0
                },
                "status": "error",
                "error": str(ai_error)
            }
        
    except Exception as e:
        logger.error(f"Error generating body patterns: {str(e)}", exc_info=True)
        return {
            "tendencies": [],
            "positive_responses": [],
            "status": "error",
            "error": str(e)
        }


@router.get("/questions/{user_id}")
async def get_pattern_questions(user_id: str):
    """
    Generate personalized questions about health patterns
    """
    try:
        logger.info(f"Generating pattern questions for user {user_id}")
        
        # Gather data for questions
        data = await gather_prediction_data(user_id, "questions")
        
        if data.get("data_quality", 0) < 30:
            logger.info(f"Insufficient data for questions: quality score {data.get('data_quality', 0)}")
            return {
                "questions": [],
                "total_questions": 0,
                "message": "Need more data to generate personalized questions",
                "status": "insufficient_data"
            }
        
        # Find interesting patterns for questions
        patterns_context = {
            "top_symptoms": list(data["symptom_tracking"]["symptom_frequency"].keys())[:10],
            "symptom_timing": analyze_symptom_timing(data),
            "correlations": find_simple_correlations(data),
            "day_patterns": analyze_day_patterns(data),
            "unexplained_patterns": find_unexplained_patterns(data)
        }
        
        prompt = f"""
        Based on these health patterns, generate 4 SPECIFIC, INTRIGUING questions the user would actually wonder about.
        
        Patterns found:
        {json.dumps(patterns_context, indent=2)}
        
        Generate questions that are:
        - SHORT and PUNCHY (e.g., "Why do I get Sunday anxiety?")
        - About SPECIFIC days/times (e.g., "Why headaches on Thursdays?")
        - Personal and relatable (e.g., "What makes my best days?")
        - About mysterious patterns (e.g., "What breaks my sleep?")
        
        IMPORTANT: Return ONLY a valid JSON array, no other text or formatting.
        Return JSON array where each question has:
        {{
            "question": "Natural question they might ask",
            "category": "mood/sleep/energy/physical",
            "icon": "brain/moon/battery/heart",
            "brief_answer": "Your best days follow a specific pattern we've discovered.",
            "deep_dive": {{
                "detailed_insights": [
                    "Morning sunlight within 30 min of waking",
                    "Protein breakfast before 9am",
                    "Movement before noon",
                    "Meaningful work progress",
                    "Evening wind-down routine"
                ],
                "connected_patterns": [
                    "Better sleep that night",
                    "Positive momentum next day",
                    "Lower stress all week"
                ],
                "actionable_advice": [
                    "Set morning routine alarm",
                    "Prep breakfast night before",
                    "Schedule movement breaks"
                ]
            }},
            "relevance_score": 70-95,
            "based_on": ["symptom_logs", "sleep_data", etc]
        }}
        
        Example:
        [{{
            "question": "Why do I get Sunday anxiety?",
            "category": "mood",
            "icon": "brain",
            "brief_answer": "Your Sunday anxiety stems from work week anticipation.",
            "deep_dive": {{
                "detailed_insights": [
                    "It peaks around 6-8pm when you start thinking about Monday",
                    "Stronger when you have unfinished tasks from the week",
                    "Less intense after productive weekends",
                    "Your body starts releasing stress hormones in anticipation",
                    "This pattern has appeared in 75% of your Sunday logs"
                ],
                "connected_patterns": [
                    "Poor Sunday night sleep",
                    "Monday morning fatigue",
                    "Tuesday recovery pattern"
                ],
                "actionable_advice": [
                    "Create a Sunday evening wind-down routine",
                    "Complete a weekly review on Friday instead",
                    "Schedule something enjoyable for Monday morning"
                ]
            }},
            "relevance_score": 92,
            "based_on": ["mood_logs", "sleep_data", "symptom_patterns"]
        }}]
        """
        
        response = await ai_analyzer.analyze_with_llm(
            prompt=prompt,
            model="qwen/qwen-2.5-coder-32b-instruct"  # Using Kimi K1.5 for better pattern analysis
        )
        
        questions_data = safe_parse_json(response, "pattern_questions")
        
        if questions_data and isinstance(questions_data, list):
            # Enrich questions
            for q in questions_data:
                q["id"] = str(uuid.uuid4())
            
            categories = list(set(q["category"] for q in questions_data))
            
            return {
                "questions": questions_data,
                "total_questions": len(questions_data),
                "categories_covered": categories
            }
        
        return {
            "questions": [],
            "total_questions": 0,
            "parse_error": True
        }
        
    except Exception as e:
        logger.error(f"Error generating pattern questions: {str(e)}")
        return {"questions": [], "error": str(e)}


# Helper functions for pattern analysis
def analyze_day_patterns(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze patterns by day of week"""
    day_patterns = {
        "Monday": [],
        "Tuesday": [],
        "Wednesday": [],
        "Thursday": [],
        "Friday": [],
        "Saturday": [],
        "Sunday": []
    }
    
    # Analyze symptom entries by day
    for entry in data["symptom_tracking"]["entries"]:
        if "occurrence_date" in entry:
            date = datetime.fromisoformat(entry["occurrence_date"])
            day_name = date.strftime("%A")
            if day_name in day_patterns:
                day_patterns[day_name].append(entry.get("symptom_name", "unknown"))
    
    # Find days with most symptoms
    day_counts = {day: len(symptoms) for day, symptoms in day_patterns.items()}
    return day_counts


def analyze_symptom_timing(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze when symptoms typically occur"""
    timing_patterns = {
        "morning": 0,
        "afternoon": 0,
        "evening": 0,
        "night": 0
    }
    
    # This is simplified - in reality you'd parse timestamps
    for entry in data["symptom_tracking"]["entries"]:
        if "created_at" in entry:
            hour = datetime.fromisoformat(entry["created_at"]).hour
            if 5 <= hour < 12:
                timing_patterns["morning"] += 1
            elif 12 <= hour < 17:
                timing_patterns["afternoon"] += 1
            elif 17 <= hour < 22:
                timing_patterns["evening"] += 1
            else:
                timing_patterns["night"] += 1
    
    return timing_patterns


def find_simple_correlations(data: Dict[str, Any]) -> List[str]:
    """Find simple correlations in the data"""
    correlations = []
    
    # Check sleep-symptom correlation
    if data["sleep_patterns"]["quality_trend"] == "declining" and data["symptom_tracking"]["severity_trends"]["trend"] == "increasing":
        correlations.append("Poor sleep correlates with increased symptoms")
    
    # Check stress-symptom correlation
    if len(data["mood_patterns"]["stress_levels"]) > 5 and data["symptom_tracking"]["total_entries"] > 10:
        correlations.append("Stress levels linked to symptom frequency")
    
    return correlations


def find_unexplained_patterns(data: Dict[str, Any]) -> List[str]:
    """Find patterns that might need explanation"""
    patterns = []
    
    # Check for day-of-week patterns
    day_counts = analyze_day_patterns(data)
    max_day = max(day_counts, key=day_counts.get)
    if day_counts[max_day] > sum(day_counts.values()) * 0.2:
        patterns.append(f"Higher symptom frequency on {max_day}s")
    
    return patterns


# Utility functions
async def log_alert_generation(user_id: str, alert_data: Dict[str, Any]):
    """Log generated alerts for analytics"""
    try:
        supabase.table('ai_alerts_log').insert({
            'user_id': user_id,
            'alert_id': alert_data['id'],
            'severity': alert_data['severity'],
            'title': alert_data['title'],
            'confidence': alert_data['confidence'],
            'generated_at': alert_data['generated_at']
        }).execute()
    except Exception as e:
        logger.error(f"Error logging alert: {str(e)}")


# Weekly generation endpoint
@router.post("/generate-weekly/{user_id}")
async def generate_weekly_predictions(user_id: str, background_tasks: BackgroundTasks):
    """
    Generate all weekly predictions for a user
    """
    try:
        logger.info(f"Starting weekly prediction generation for user {user_id}")
        
        # Mark old predictions as not current
        supabase.table('weekly_ai_predictions').update({
            'is_current': False
        }).eq('user_id', user_id).eq('is_current', True).execute()
        
        # Create new prediction record
        prediction_record = {
            'user_id': user_id,
            'generation_status': 'pending',
            'generated_at': datetime.utcnow().isoformat(),
            'predictions': [],
            'pattern_questions': [],
            'body_patterns': {}
        }
        
        result = supabase.table('weekly_ai_predictions').insert(prediction_record).execute()
        prediction_id = result.data[0]['id']
        
        # Generate predictions in background
        background_tasks.add_task(
            generate_all_predictions,
            user_id,
            prediction_id
        )
        
        return {
            "status": "started",
            "prediction_id": prediction_id,
            "message": "Weekly predictions generation started"
        }
        
    except Exception as e:
        logger.error(f"Error starting weekly generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def generate_all_predictions(user_id: str, prediction_id: str):
    """Background task to generate all predictions"""
    try:
        # Generate each type of prediction
        dashboard_alert = await get_dashboard_alert(user_id)
        immediate = await get_immediate_predictions(user_id)
        patterns = await get_body_patterns(user_id)
        questions = await get_pattern_questions(user_id)
        
        # Update the record
        update_data = {
            'dashboard_alert': dashboard_alert.get('alert'),
            'predictions': immediate.get('predictions', []),
            'pattern_questions': questions.get('questions', []),
            'body_patterns': {
                'tendencies': patterns.get('tendencies', []),
                'positiveResponses': patterns.get('positive_responses', [])
            },
            'data_quality_score': immediate.get('data_quality_score', 0),
            'generation_status': 'completed',
            'updated_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('weekly_ai_predictions').update(update_data).eq('id', prediction_id).execute()
        
        logger.info(f"Successfully generated weekly predictions for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error generating predictions: {str(e)}")
        
        # Update with error
        supabase.table('weekly_ai_predictions').update({
            'generation_status': 'failed',
            'error_message': str(e),
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', prediction_id).execute()


# Helper function to ensure weekly predictions exist
async def ensure_weekly_predictions_exist(user_id: str) -> str:
    """
    Ensure a weekly predictions record exists for the user
    Returns the prediction ID
    """
    try:
        # Check for existing current predictions
        result = supabase.table('weekly_ai_predictions').select('id').eq(
            'user_id', user_id
        ).eq('is_current', True).execute()
        
        if result.data:
            return result.data[0]['id']
        
        # Create new prediction record
        new_prediction = {
            'user_id': user_id,
            'generation_status': 'pending',
            'generated_at': datetime.utcnow().isoformat(),
            'predictions': [],
            'pattern_questions': [],
            'body_patterns': {},
            'is_current': True
        }
        
        result = supabase.table('weekly_ai_predictions').insert(new_prediction).execute()
        return result.data[0]['id']
        
    except Exception as e:
        logger.error(f"Error ensuring weekly predictions exist: {str(e)}")
        return None

# Get current weekly predictions
@router.get("/weekly/{user_id}")
async def get_weekly_predictions(user_id: str):
    """
    Get the current weekly AI predictions for a user
    """
    try:
        result = supabase.table('weekly_ai_predictions').select('*').eq(
            'user_id', user_id
        ).eq('is_current', True).execute()
        
        if not result.data:
            # Try to create one
            prediction_id = await ensure_weekly_predictions_exist(user_id)
            if not prediction_id:
                return {
                    "status": "not_found",
                    "message": "No current predictions found",
                    "predictions": None
                }
            
            # Fetch the newly created record
            result = supabase.table('weekly_ai_predictions').select('*').eq(
                'id', prediction_id
            ).execute()
        
        if not result.data:
            return {
                "status": "not_found",
                "message": "No current predictions found",
                "predictions": None
            }
        
        prediction = result.data[0]
        
        # Mark as viewed if not already
        if not prediction.get('viewed_at'):
            supabase.table('weekly_ai_predictions').update({
                'viewed_at': datetime.now().isoformat()
            }).eq('id', prediction['id']).execute()
        
        return {
            "status": "success",
            "predictions": {
                "id": prediction['id'],
                "dashboard_alert": prediction.get('dashboard_alert'),
                "predictions": prediction.get('predictions', []),
                "pattern_questions": prediction.get('pattern_questions', []),
                "body_patterns": prediction.get('body_patterns', {}),
                "generated_at": prediction['generated_at'],
                "data_quality_score": prediction.get('data_quality_score', 0),
                "is_current": prediction['is_current'],
                "viewed_at": prediction.get('viewed_at') or datetime.now().isoformat(),
                "generation_status": prediction.get('generation_status', 'pending')
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching weekly predictions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# User preferences endpoints
@router.put("/preferences/{user_id}")
async def update_user_preferences(user_id: str, preferences: UserPreferences):
    """Update user's AI generation preferences"""
    try:
        existing = supabase.table('user_ai_preferences').select('user_id').eq('user_id', user_id).execute()
        
        update_data = {
            'weekly_generation_enabled': preferences.weekly_generation_enabled,
            'preferred_day_of_week': preferences.preferred_day_of_week,
            'preferred_hour': preferences.preferred_hour,
            'timezone': preferences.timezone,
            'updated_at': datetime.now().isoformat()
        }
        
        if existing.data:
            supabase.table('user_ai_preferences').update(update_data).eq('user_id', user_id).execute()
        else:
            update_data['user_id'] = user_id
            supabase.table('user_ai_preferences').insert(update_data).execute()
        
        return {
            "status": "success",
            "message": "Preferences updated successfully",
            "preferences": preferences.dict()
        }
        
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preferences/{user_id}")
async def get_user_preferences(user_id: str):
    """Get user's AI generation preferences"""
    try:
        result = supabase.table('user_ai_preferences').select('*').eq('user_id', user_id).execute()
        
        if not result.data:
            return {
                "preferences": {
                    "weekly_generation_enabled": True,
                    "preferred_day_of_week": 3,
                    "preferred_hour": 17,
                    "timezone": "UTC",
                    "initial_predictions_generated": False,
                    "last_generation_date": None
                }
            }
        
        prefs = result.data[0]
        return {
            "preferences": {
                "weekly_generation_enabled": prefs['weekly_generation_enabled'],
                "preferred_day_of_week": prefs['preferred_day_of_week'],
                "preferred_hour": prefs['preferred_hour'],
                "timezone": prefs['timezone'],
                "initial_predictions_generated": prefs.get('initial_predictions_generated', False),
                "last_generation_date": prefs.get('last_generation_date')
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))