"""AI Predictions API endpoints for dashboard alerts and predictive insights"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import logging
import uuid
from services.ai_health_analyzer import HealthAnalyzer
from supabase_client import supabase
from utils.data_gathering import (
    get_symptom_logs, get_sleep_data, get_mood_data, 
    get_medication_logs, get_quick_scan_history, get_deep_dive_sessions
)
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
class AIAlert(BaseModel):
    id: str
    severity: str  # 'info' | 'warning' | 'critical'
    title: str
    description: str
    timeframe: str
    confidence: int
    actionUrl: str
    preventionTip: Optional[str] = None
    generated_at: str

class AIPrediction(BaseModel):
    id: str
    type: str  # 'immediate' | 'seasonal' | 'longterm'
    severity: str  # 'info' | 'warning' | 'alert'
    title: str
    description: str
    pattern: str
    confidence: int
    preventionProtocols: List[str]
    category: str
    reasoning: Optional[str] = None
    dataPoints: Optional[List[str]] = None
    gradient: Optional[str] = None
    generated_at: str

class AIPatternQuestion(BaseModel):
    id: str
    question: str
    category: str  # 'sleep' | 'energy' | 'mood' | 'physical' | 'other'
    answer: str
    deepDive: List[str]
    connections: List[str]
    relevanceScore: int
    basedOn: List[str]

class BodyPatterns(BaseModel):
    tendencies: List[str]
    positiveResponses: List[str]

class WeeklyPredictions(BaseModel):
    id: str
    dashboard_alert: Optional[Dict[str, Any]]
    predictions: List[Dict[str, Any]]
    pattern_questions: List[Dict[str, Any]]
    body_patterns: Dict[str, Any]
    generated_at: str
    data_quality_score: Optional[int]
    is_current: bool
    viewed_at: Optional[str]

class UserPreferences(BaseModel):
    weekly_generation_enabled: bool = True
    preferred_day_of_week: int = 3  # Wednesday
    preferred_hour: int = 17  # 5 PM
    timezone: str = "UTC"


@router.get("/dashboard-alert/{user_id}")
async def generate_dashboard_alert(user_id: str):
    """
    Analyzes user's recent health data to generate the most important
    predictive alert for their dashboard.
    """
    try:
        # Gather comprehensive user data
        recent_data = await gather_user_health_data(user_id, days=14)
        historical_patterns = await get_user_patterns(user_id)
        
        # Check if user has enough data
        if not recent_data or len(recent_data.get('entries', [])) < 5:
            return {"alert": None, "reason": "insufficient_data"}
        
        # Extract patterns and insights
        symptoms = extract_symptoms(recent_data)
        sleep_patterns = analyze_sleep_trends(recent_data)
        stress_indicators = detect_stress_patterns(recent_data)
        medication_adherence = check_medication_compliance(recent_data)
        
        # Prepare context for AI
        context = {
            "recent_symptoms": symptoms,
            "sleep_patterns": sleep_patterns,
            "stress_indicators": stress_indicators,
            "medication_adherence": medication_adherence,
            "historical_triggers": historical_patterns.get('known_triggers', []),
            "current_date": datetime.now().isoformat(),
            "day_of_week": datetime.now().strftime("%A"),
        }
        
        # Generate alert using AI
        prompt = f"""
        Analyze this user's health data and generate ONE most important predictive alert.
        
        Context:
        {json.dumps(context, indent=2)}
        
        Rules:
        1. Only generate an alert if there's a meaningful pattern or risk detected
        2. Be specific about timeframes (e.g., "next 48 hours", "this weekend")
        3. Use supportive, non-alarming language
        4. Base predictions on actual patterns in their data
        5. Include confidence score based on pattern strength
        
        Generate a JSON object with:
        {{
            "severity": "info" or "warning" or "critical",
            "title": "Clear, specific title (max 10 words)",
            "description": "2-3 sentences explaining the pattern and prediction",
            "timeframe": "When this might occur",
            "confidence": 0-100,
            "preventionTip": "One immediate action they can take (optional)"
        }}
        
        If no significant patterns found, return null.
        """
        
        ai_response = await ai_analyzer.analyze_with_llm(
            prompt=prompt,
            model="deepseek/deepseek-chat"  # Using DeepSeek V3 as per CLAUDE.md
        )
        
        if ai_response and ai_response != "null":
            try:
                alert_data = json.loads(ai_response) if isinstance(ai_response, str) else ai_response
                
                if alert_data:
                    # Add metadata
                    alert_data["id"] = str(uuid.uuid4())
                    alert_data["actionUrl"] = f"/predictive-insights?focus={alert_data['id']}"
                    alert_data["generated_at"] = datetime.now().isoformat()
                    
                    # Log for analytics
                    await log_alert_generation(user_id, alert_data)
                    
                    return {"alert": alert_data}
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response: {ai_response}")
        
        return {"alert": None}
        
    except Exception as e:
        logger.error(f"Error generating dashboard alert: {str(e)}")
        return {"alert": None, "error": str(e)}


@router.get("/predictions/{user_id}")
async def generate_ai_predictions(user_id: str):
    """
    Generates personalized health predictions across multiple timeframes
    """
    try:
        # Gather comprehensive data
        user_data = await gather_full_user_data(user_id)
        
        if not has_sufficient_data(user_data):
            return {"predictions": generate_onboarding_predictions()}
        
        predictions = []
        
        # 1. Immediate predictions (next 7 days)
        immediate_context = prepare_immediate_context(user_data)
        immediate_prompt = f"""
        Analyze this user's recent health patterns and generate predictions for the next 7 days.
        
        Data:
        {json.dumps(immediate_context, indent=2)}
        
        Generate 2-4 specific predictions based on:
        - Recent symptom patterns
        - Sleep/stress/mood trends
        - Day of week patterns
        - Medication adherence
        
        For each prediction include:
        {{
            "type": "immediate",
            "severity": "info" or "warning" or "alert",
            "title": "Specific, actionable title",
            "description": "2-3 sentences explaining why",
            "pattern": "The specific pattern detected",
            "confidence": 60-100,
            "preventionProtocols": ["3-5 specific actions"],
            "category": "migraine/sleep/energy/mood/stress/other"
        }}
        
        Only include predictions with confidence > 60%.
        Output as JSON array.
        """
        
        immediate_predictions = await generate_predictions(immediate_prompt)
        predictions.extend(immediate_predictions)
        
        # 2. Seasonal predictions
        seasonal_context = prepare_seasonal_context(user_data)
        seasonal_prompt = f"""
        Based on historical patterns and upcoming season changes, generate predictions for next 3 months.
        
        Consider:
        - Past seasonal patterns
        - Allergy history
        - Weather sensitivity
        - Holiday stress patterns
        - Vitamin D patterns
        
        Context:
        {json.dumps(seasonal_context, indent=2)}
        
        Generate 1-3 seasonal predictions.
        Format same as above but type: "seasonal"
        """
        
        seasonal_predictions = await generate_predictions(seasonal_prompt)
        predictions.extend(seasonal_predictions)
        
        # 3. Long-term trajectory
        longterm_analysis = await analyze_longterm_risks(user_data)
        if longterm_analysis:
            predictions.extend(longterm_analysis)
        
        # Enrich predictions with gradients
        for pred in predictions:
            pred["gradient"] = get_gradient_for_severity(pred["severity"])
        
        return {
            "predictions": predictions,
            "generated_at": datetime.now().isoformat(),
            "data_quality_score": calculate_data_quality(user_data)
        }
        
    except Exception as e:
        logger.error(f"Error generating predictions: {str(e)}")
        return {"predictions": [], "error": str(e)}


@router.get("/pattern-questions/{user_id}")
async def generate_pattern_questions(user_id: str):
    """
    Generates personalized questions about the user's health patterns
    """
    try:
        # Get user's unique patterns
        patterns = await analyze_user_patterns(user_id)
        anomalies = await detect_anomalies(user_id)
        correlations = await find_correlations(user_id)
        
        context = {
            "top_patterns": patterns[:10],
            "unusual_findings": anomalies,
            "strong_correlations": correlations,
            "user_concerns": await get_user_focus_areas(user_id)
        }
        
        prompt = f"""
        Based on this user's unique health patterns, generate 4-6 insightful questions they might wonder about.
        
        Patterns found:
        {json.dumps(context, indent=2)}
        
        Generate questions that:
        1. Are specific to THIS user's data (not generic)
        2. Address patterns they might not have noticed
        3. Explain timing correlations they experience
        4. Connect seemingly unrelated symptoms
        
        For each question:
        {{
            "question": "Natural language question",
            "category": "sleep/energy/mood/physical/other",
            "answer": "Brief 1-2 sentence answer",
            "deepDive": ["4-5 detailed insights"],
            "connections": ["related patterns"],
            "relevanceScore": 0-100,
            "basedOn": ["data points that led to this question"]
        }}
        
        Output as JSON array.
        """
        
        questions_response = await ai_analyzer.analyze_with_llm(
            prompt=prompt,
            model="deepseek/deepseek-chat"
        )
        
        parsed_questions = json.loads(questions_response) if isinstance(questions_response, str) else questions_response
        
        # Add IDs
        for q in parsed_questions:
            q["id"] = str(uuid.uuid4())
        
        return {
            "questions": parsed_questions,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating pattern questions: {str(e)}")
        return {"questions": [], "error": str(e)}


@router.get("/body-patterns/{user_id}")
async def analyze_body_patterns(user_id: str):
    """
    Generates personalized insights about user's body patterns
    """
    try:
        # Comprehensive pattern analysis
        all_patterns = await get_all_user_patterns(user_id)
        
        prompt = f"""
        Analyze these health patterns and create two lists of insights.
        
        Patterns:
        {json.dumps(all_patterns, indent=2)}
        
        Generate:
        1. "tendencies" - 5-6 specific negative patterns or triggers
           Example: "Get migraines 48-72 hours after high stress events"
           
        2. "positiveResponses" - 5-6 things that consistently help
           Example: "Sleep quality improves with 30min morning walks"
        
        Make each insight:
        - Specific with numbers/timeframes when possible
        - Based on actual data patterns
        - Actionable (user can work with this knowledge)
        - Written in second person ("You tend to...")
        
        Output as JSON with two arrays:
        {{
            "tendencies": ["insight1", "insight2", ...],
            "positiveResponses": ["insight1", "insight2", ...]
        }}
        """
        
        response = await ai_analyzer.analyze_with_llm(
            prompt=prompt,
            model="deepseek/deepseek-chat"
        )
        
        patterns = json.loads(response) if isinstance(response, str) else response
        
        return {
            "patterns": patterns,
            "lastUpdated": datetime.now().isoformat(),
            "dataPoints": len(all_patterns)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing body patterns: {str(e)}")
        return {"patterns": {"tendencies": [], "positiveResponses": []}, "error": str(e)}


# Helper functions
async def gather_user_health_data(user_id: str, days: int) -> Dict[str, Any]:
    """Aggregates all health data sources"""
    try:
        data = {
            "entries": await get_symptom_logs(user_id, days),
            "sleep_logs": await get_sleep_data(user_id, days),
            "mood_logs": await get_mood_data(user_id, days),
            "medications": await get_medication_logs(user_id, days),
            "quick_scans": await get_quick_scan_history(user_id, days),
            "deep_dives": await get_deep_dive_sessions(user_id, days)
        }
        return data
    except Exception as e:
        logger.error(f"Error gathering user data: {str(e)}")
        return {}


async def gather_full_user_data(user_id: str) -> Dict[str, Any]:
    """Gathers complete user health data for comprehensive analysis"""
    return await gather_user_health_data(user_id, days=90)


def extract_symptoms(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts and categorizes recent symptoms"""
    symptoms = []
    for entry in data.get('entries', []):
        if entry.get('symptoms'):
            for s in entry['symptoms']:
                symptoms.append({
                    "name": s.get('name'),
                    "severity": s.get('severity'),
                    "date": entry.get('date'),
                    "body_part": s.get('body_part')
                })
    return symptoms


def analyze_sleep_trends(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Identifies sleep pattern changes"""
    sleep_logs = data.get('sleep_logs', [])
    if not sleep_logs:
        return None
    
    # Calculate averages and trends
    recent_logs = sleep_logs[-7:] if len(sleep_logs) >= 7 else sleep_logs
    previous_logs = sleep_logs[-14:-7] if len(sleep_logs) >= 14 else []
    
    recent_avg = calculate_average_sleep(recent_logs)
    previous_avg = calculate_average_sleep(previous_logs) if previous_logs else recent_avg
    
    return {
        "recent_average": recent_avg,
        "trend": "declining" if recent_avg < previous_avg - 0.5 else "stable",
        "disruptions": count_sleep_disruptions(recent_logs)
    }


def detect_stress_patterns(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detects stress indicators from various data sources"""
    indicators = []
    
    # Check mood logs
    mood_logs = data.get('mood_logs', [])
    for log in mood_logs:
        if log.get('stress_level', 0) > 7:
            indicators.append({
                "type": "high_stress",
                "date": log.get('date'),
                "level": log.get('stress_level')
            })
    
    return indicators


def check_medication_compliance(data: Dict[str, Any]) -> Dict[str, Any]:
    """Checks medication adherence patterns"""
    med_logs = data.get('medications', [])
    if not med_logs:
        return {"compliance_rate": 100, "missed_doses": 0}
    
    # Simple compliance calculation
    total_scheduled = len(med_logs)
    taken = sum(1 for log in med_logs if log.get('taken', False))
    
    return {
        "compliance_rate": (taken / total_scheduled * 100) if total_scheduled > 0 else 100,
        "missed_doses": total_scheduled - taken
    }


async def get_user_patterns(user_id: str) -> Dict[str, Any]:
    """Gets historical patterns for a user"""
    # supabase is already imported at module level
    
    try:
        # Get known triggers from health analysis
        result = supabase.table('health_analysis_results').select('*').eq('user_id', user_id).execute()
        
        if result.data:
            # Extract patterns from previous analyses
            patterns = {
                'known_triggers': [],
                'effective_treatments': []
            }
            
            for analysis in result.data:
                if analysis.get('triggers'):
                    patterns['known_triggers'].extend(analysis['triggers'])
                if analysis.get('treatments'):
                    patterns['effective_treatments'].extend(analysis['treatments'])
            
            return patterns
    except Exception as e:
        logger.error(f"Error getting user patterns: {str(e)}")
    
    return {'known_triggers': [], 'effective_treatments': []}


async def log_alert_generation(user_id: str, alert_data: Dict[str, Any]):
    """Logs generated alerts for analytics"""
    # supabase is already imported at module level
    
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


async def generate_predictions(prompt: str) -> List[Dict[str, Any]]:
    """Generate predictions using LLM"""
    response = await ai_analyzer.analyze_with_llm(
        prompt=prompt,
        model="deepseek/deepseek-chat"
    )
    
    try:
        predictions = json.loads(response) if isinstance(response, str) else response
        
        # Validate and clean predictions
        valid_predictions = []
        for pred in predictions:
            if validate_prediction(pred):
                pred["id"] = str(uuid.uuid4())
                pred["generated_at"] = datetime.now().isoformat()
                valid_predictions.append(pred)
        
        return valid_predictions
    except Exception as e:
        logger.error(f"Error parsing predictions: {str(e)}")
        return []


def validate_prediction(pred: Dict[str, Any]) -> bool:
    """Validates prediction has required fields"""
    required_fields = ['type', 'severity', 'title', 'description', 'confidence']
    return all(field in pred for field in required_fields)


def has_sufficient_data(user_data: Dict[str, Any]) -> bool:
    """Checks if user has enough data for predictions"""
    entries = user_data.get('entries', [])
    return len(entries) >= 10


def generate_onboarding_predictions() -> List[Dict[str, Any]]:
    """Generates default predictions for new users"""
    return [{
        "id": str(uuid.uuid4()),
        "type": "immediate",
        "severity": "info",
        "title": "Start Building Your Health Profile",
        "description": "Log your symptoms and health data for at least a week to unlock personalized predictions.",
        "pattern": "New user - insufficient data",
        "confidence": 100,
        "preventionProtocols": [
            "Log your symptoms daily",
            "Track your sleep patterns",
            "Note any triggers or patterns you notice"
        ],
        "category": "other",
        "gradient": "from-blue-600/10 to-cyan-600/10",
        "generated_at": datetime.now().isoformat()
    }]


def prepare_immediate_context(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares context for immediate predictions"""
    return {
        "recent_symptoms": extract_symptoms(user_data)[-20:],
        "sleep_average": calculate_average_sleep(user_data.get('sleep_logs', [])[-7:]),
        "stress_levels": [log.get('stress_level', 5) for log in user_data.get('mood_logs', [])[-7:]],
        "day_patterns": analyze_day_of_week_patterns(user_data),
        "current_date": datetime.now().isoformat()
    }


def prepare_seasonal_context(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares context for seasonal predictions"""
    return {
        "historical_seasons": get_seasonal_patterns(user_data),
        "allergy_history": extract_allergy_data(user_data),
        "weather_sensitivity": analyze_weather_correlations(user_data),
        "upcoming_season": get_upcoming_season()
    }


async def analyze_longterm_risks(user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyzes long-term health trajectory"""
    # Simplified for now
    return []


async def analyze_user_patterns(user_id: str) -> List[Dict[str, Any]]:
    """Analyzes and returns user's top patterns"""
    # Implementation would analyze all user data
    return []


async def detect_anomalies(user_id: str) -> List[Dict[str, Any]]:
    """Detects unusual patterns in user data"""
    return []


async def find_correlations(user_id: str) -> List[Dict[str, Any]]:
    """Finds correlations between different health factors"""
    return []


async def get_user_focus_areas(user_id: str) -> List[str]:
    """Gets areas user is most concerned about"""
    return []


async def get_all_user_patterns(user_id: str) -> List[Dict[str, Any]]:
    """Gets all patterns for comprehensive analysis"""
    return []


def get_gradient_for_severity(severity: str) -> str:
    """Returns gradient CSS class for severity level"""
    gradients = {
        "info": "from-blue-600/10 to-cyan-600/10",
        "warning": "from-yellow-600/10 to-orange-600/10",
        "alert": "from-red-600/10 to-orange-600/10",
        "critical": "from-red-600/10 to-pink-600/10"
    }
    return gradients.get(severity, "from-gray-600/10 to-slate-600/10")


def calculate_average_sleep(sleep_logs: List[Dict[str, Any]]) -> float:
    """Calculates average sleep hours"""
    if not sleep_logs:
        return 0
    
    total_hours = sum(log.get('hours', 0) for log in sleep_logs)
    return total_hours / len(sleep_logs)


def count_sleep_disruptions(sleep_logs: List[Dict[str, Any]]) -> int:
    """Counts sleep disruptions"""
    return sum(1 for log in sleep_logs if log.get('quality', 5) < 3)


def calculate_data_quality(user_data: Dict[str, Any]) -> int:
    """Calculates data quality score 0-100"""
    score = 0
    
    # Check data completeness
    if len(user_data.get('entries', [])) > 30:
        score += 25
    if len(user_data.get('sleep_logs', [])) > 20:
        score += 25
    if len(user_data.get('mood_logs', [])) > 20:
        score += 25
    if user_data.get('medications'):
        score += 25
    
    return min(score, 100)


def analyze_day_of_week_patterns(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyzes patterns by day of week"""
    # Simplified implementation
    return {}


def get_seasonal_patterns(user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Gets historical seasonal patterns"""
    return []


def extract_allergy_data(user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts allergy-related data"""
    return []


def analyze_weather_correlations(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyzes weather-related health correlations"""
    return {}


def get_upcoming_season() -> str:
    """Gets the upcoming season based on current date"""
    month = datetime.now().month
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "fall"


async def _generate_weekly_predictions_inline(user_id: str) -> Dict:
    """Generate weekly predictions inline to avoid circular imports"""
    try:
        # Mark old predictions as not current
        supabase.table('weekly_ai_predictions').update({
            'is_current': False
        }).eq('user_id', user_id).eq('is_current', True).execute()
        
        # Create new prediction record
        prediction_record = {
            'user_id': user_id,
            'generation_status': 'pending',
            'generated_at': datetime.utcnow().isoformat()
        }
        
        result = supabase.table('weekly_ai_predictions').insert(prediction_record).execute()
        prediction_id = result.data[0]['id']
        
        try:
            # Generate all predictions
            alert_data = await generate_dashboard_alert(user_id)
            dashboard_alert = alert_data.get('alert') if alert_data else None
            
            predictions_data = await generate_ai_predictions(user_id)
            predictions = predictions_data.get('predictions', []) if predictions_data else []
            data_quality_score = predictions_data.get('data_quality_score', 0) if predictions_data else 0
            
            questions_data = await generate_pattern_questions(user_id)
            pattern_questions = questions_data.get('questions', []) if questions_data else []
            
            patterns_data = await analyze_body_patterns(user_id)
            body_patterns = patterns_data.get('patterns', {}) if patterns_data else {}
            
            # Update the record
            update_data = {
                'dashboard_alert': dashboard_alert,
                'predictions': predictions,
                'pattern_questions': pattern_questions,
                'body_patterns': body_patterns,
                'data_quality_score': data_quality_score,
                'generation_status': 'completed',
                'updated_at': datetime.utcnow().isoformat()
            }
            
            supabase.table('weekly_ai_predictions').update(update_data).eq('id', prediction_id).execute()
            
            # Update user preferences
            supabase.table('user_ai_preferences').update({
                'last_generation_date': datetime.utcnow().isoformat(),
                'generation_failure_count': 0
            }).eq('user_id', user_id).execute()
            
            return {
                'user_id': user_id,
                'status': 'success',
                'prediction_id': prediction_id
            }
            
        except Exception as e:
            # Update record with error
            supabase.table('weekly_ai_predictions').update({
                'generation_status': 'failed',
                'error_message': str(e),
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', prediction_id).execute()
            
            # Increment failure count
            supabase.table('user_ai_preferences').update({
                'generation_failure_count': supabase.raw('generation_failure_count + 1')
            }).eq('user_id', user_id).execute()
            
            raise
            
    except Exception as e:
        logger.error(f"Failed to generate weekly predictions: {str(e)}")
        return {
            'user_id': user_id,
            'status': 'error',
            'error': str(e)
        }


# New endpoints for proactive weekly generation

@router.post("/generate-initial/{user_id}")
async def generate_initial_predictions(user_id: str):
    """
    Generate initial AI predictions when user first downloads the app
    This is called once during onboarding
    """
    try:
        logger.info(f"Generating initial AI predictions for new user {user_id}")
        
        # Check if already generated
        prefs_result = supabase.table('user_ai_preferences').select('initial_predictions_generated').eq('user_id', user_id).execute()
        
        if prefs_result.data and prefs_result.data[0].get('initial_predictions_generated'):
            return {
                "status": "already_generated",
                "message": "Initial predictions have already been generated for this user"
            }
        
        # Create user preferences if not exists
        if not prefs_result.data:
            supabase.table('user_ai_preferences').insert({
                'user_id': user_id,
                'weekly_generation_enabled': True,
                'preferred_day_of_week': 3,  # Wednesday
                'preferred_hour': 17,  # 5 PM
                'timezone': 'UTC'
            }).execute()
        
        # Generate and store predictions via direct function call
        result = await _generate_weekly_predictions_inline(user_id)
        
        if result['status'] == 'success':
            # Mark initial generation as complete
            supabase.table('user_ai_preferences').update({
                'initial_predictions_generated': True,
                'initial_generation_date': datetime.now().isoformat()
            }).eq('user_id', user_id).execute()
            
            return {
                "status": "success",
                "prediction_id": result['prediction_id'],
                "message": "Initial predictions generated successfully"
            }
        else:
            return {
                "status": "error",
                "message": "Failed to generate initial predictions",
                "error": result.get('error')
            }
            
    except Exception as e:
        logger.error(f"Error generating initial predictions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weekly/{user_id}")
async def get_weekly_predictions(user_id: str):
    """
    Get the current weekly AI predictions for a user
    Returns stored predictions instead of generating new ones
    """
    try:
        # Get current predictions
        result = supabase.table('weekly_ai_predictions').select('*').eq(
            'user_id', user_id
        ).eq('is_current', True).eq('generation_status', 'completed').execute()
        
        if not result.data:
            # Check if user needs initial generation
            needs_initial = supabase.rpc('user_needs_initial_predictions', {'p_user_id': user_id}).execute()
            
            if needs_initial.data:
                return {
                    "status": "needs_initial",
                    "message": "User needs initial prediction generation",
                    "predictions": None
                }
            else:
                return {
                    "status": "not_found",
                    "message": "No current predictions found. They will be generated on the next scheduled run.",
                    "predictions": None
                }
        
        prediction = result.data[0]
        
        # Mark as viewed if not already
        if not prediction.get('viewed_at'):
            supabase.table('weekly_ai_predictions').update({
                'viewed_at': datetime.now().isoformat()
            }).eq('id', prediction['id']).execute()
        
        # Format response
        return {
            "status": "success",
            "predictions": {
                "id": prediction['id'],
                "dashboard_alert": prediction['dashboard_alert'],
                "predictions": prediction['predictions'],
                "pattern_questions": prediction['pattern_questions'],
                "body_patterns": prediction['body_patterns'],
                "generated_at": prediction['generated_at'],
                "data_quality_score": prediction.get('data_quality_score', 0),
                "is_current": prediction['is_current'],
                "viewed_at": prediction.get('viewed_at') or datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching weekly predictions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weekly/{user_id}/alert")
async def get_weekly_dashboard_alert(user_id: str):
    """
    Get just the dashboard alert from weekly predictions
    Lightweight endpoint for dashboard use
    """
    try:
        result = supabase.table('weekly_ai_predictions').select(
            'id, dashboard_alert, generated_at'
        ).eq('user_id', user_id).eq('is_current', True).eq('generation_status', 'completed').execute()
        
        if not result.data or not result.data[0].get('dashboard_alert'):
            return {"alert": None}
        
        return {"alert": result.data[0]['dashboard_alert']}
        
    except Exception as e:
        logger.error(f"Error fetching weekly alert: {str(e)}")
        return {"alert": None}


@router.put("/preferences/{user_id}")
async def update_user_preferences(user_id: str, preferences: UserPreferences):
    """
    Update user's AI generation preferences
    """
    try:
        # Check if preferences exist
        existing = supabase.table('user_ai_preferences').select('user_id').eq('user_id', user_id).execute()
        
        update_data = {
            'weekly_generation_enabled': preferences.weekly_generation_enabled,
            'preferred_day_of_week': preferences.preferred_day_of_week,
            'preferred_hour': preferences.preferred_hour,
            'timezone': preferences.timezone,
            'updated_at': datetime.now().isoformat()
        }
        
        if existing.data:
            # Update existing
            supabase.table('user_ai_preferences').update(update_data).eq('user_id', user_id).execute()
        else:
            # Insert new
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
    """
    Get user's AI generation preferences
    """
    try:
        result = supabase.table('user_ai_preferences').select('*').eq('user_id', user_id).execute()
        
        if not result.data:
            # Return defaults
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
                "initial_predictions_generated": prefs['initial_predictions_generated'],
                "last_generation_date": prefs['last_generation_date']
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/regenerate/{user_id}")
async def regenerate_weekly_predictions(user_id: str):
    """
    Manually trigger regeneration of weekly predictions
    Useful for testing or if user wants fresh predictions
    """
    try:
        # Check rate limiting - allow once per day
        last_gen = supabase.table('user_ai_preferences').select('last_generation_date').eq('user_id', user_id).execute()
        
        if last_gen.data and last_gen.data[0].get('last_generation_date'):
            last_date = datetime.fromisoformat(last_gen.data[0]['last_generation_date'].replace('Z', '+00:00'))
            if (datetime.now() - last_date).total_seconds() < 86400:  # 24 hours
                remaining_hours = 24 - int((datetime.now() - last_date).total_seconds() / 3600)
                return {
                    "status": "rate_limited",
                    "message": f"Predictions can only be regenerated once per day. Try again in {remaining_hours} hours."
                }
        
        # Trigger regeneration
        result = await _generate_weekly_predictions_inline(user_id)
        
        if result['status'] == 'success':
            return {
                "status": "success",
                "prediction_id": result['prediction_id'],
                "message": "Predictions regenerated successfully"
            }
        else:
            return {
                "status": "error",
                "message": "Failed to regenerate predictions",
                "error": result.get('error')
            }
            
    except Exception as e:
        logger.error(f"Error regenerating predictions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))