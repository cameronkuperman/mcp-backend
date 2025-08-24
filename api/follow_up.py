"""Assessment Follow-Up API endpoints for temporal condition tracking"""
from fastapi import APIRouter, Request, HTTPException
from typing import Optional, Dict, Any, List
import json
import uuid
from datetime import datetime, timezone, timedelta
import logging

from models.requests import (
    FollowUpQuestionsRequest,
    FollowUpSubmitRequest,
    FollowUpChainRequest,
    MedicalVisitExplainRequest,
    FollowUpScheduleRequest,
    FollowUpAnalyticsRequest
)
from utils.json_parser import extract_json_from_text
from utils.data_gathering import get_user_medical_data
from business_logic import call_llm
from supabase_client import supabase

router = APIRouter(prefix="/api/follow-up", tags=["follow_up"])
logger = logging.getLogger(__name__)

# Base questions that are always asked
BASE_QUESTIONS = [
    {
        "id": "q1",
        "question": "Have there been any changes since last time?",
        "type": "multiple_choice",
        "options": ["Much better", "Somewhat better", "No change", "Somewhat worse", "Much worse"],
        "required": False
    },
    {
        "id": "q2",
        "question": "What specific changes have you noticed?",
        "type": "text",
        "depends_on": "q1",
        "show_if_not": "No change",
        "required": False
    },
    {
        "id": "q3",
        "question": "Have your symptoms worsened or gotten better in severity?",
        "type": "multiple_choice",
        "options": ["Much worse", "Somewhat worse", "About the same", "Somewhat better", "Much better"],
        "required": False
    },
    {
        "id": "q4",
        "question": "Have you identified any new triggers or patterns?",
        "type": "text_with_toggle",
        "options": ["Yes", "No", "Not sure"],
        "required": False
    },
    {
        "id": "q5",
        "question": "Have you seen a doctor since last time?",
        "type": "boolean",
        "triggers_modal": True,
        "required": False
    }
]

@router.get("/questions/{assessment_id}")
async def get_follow_up_questions(
    assessment_id: str,
    assessment_type: str,
    user_id: Optional[str] = None
):
    """Get follow-up questions (5 base + 3 AI-generated) for an assessment"""
    try:
        # Fetch the original assessment based on type
        original_assessment = await fetch_original_assessment(assessment_id, assessment_type)
        if not original_assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        # Fetch any previous follow-ups in the chain
        chain_id = await get_or_create_chain_id(assessment_id, assessment_type)
        previous_follow_ups = await fetch_follow_up_chain(chain_id)
        
        # Calculate temporal context
        created_at = original_assessment.get("created_at")
        if isinstance(created_at, str):
            if created_at.endswith('Z'):
                created_at = created_at[:-1] + '+00:00'
            original_date = datetime.fromisoformat(created_at)
        else:
            original_date = created_at
        
        days_since_original = (datetime.now(timezone.utc) - original_date).days
        
        # Determine days since last follow-up
        if previous_follow_ups:
            last_follow_up = previous_follow_ups[-1]
            last_date = datetime.fromisoformat(last_follow_up["created_at"])
            days_since_last = (datetime.now(timezone.utc) - last_date).days
        else:
            days_since_last = days_since_original
        
        # Check for active symptom tracking
        has_active_tracking = await check_active_symptom_tracking(user_id, original_assessment)
        
        # Generate AI questions
        ai_questions = await generate_ai_questions(
            original_assessment=original_assessment,
            assessment_type=assessment_type,
            previous_follow_ups=previous_follow_ups,
            days_since_original=days_since_original,
            days_since_last=days_since_last,
            user_id=user_id,
            has_active_tracking=has_active_tracking
        )
        
        # Track event
        await track_event(
            chain_id=chain_id,
            user_id=user_id,
            event_type="follow_up_scheduled",
            event_data={
                "assessment_id": assessment_id,
                "days_since_original": days_since_original,
                "follow_up_number": len(previous_follow_ups) + 1
            }
        )
        
        return {
            "base_questions": BASE_QUESTIONS,
            "ai_questions": ai_questions,
            "context": {
                "chain_id": chain_id,
                "days_since_original": days_since_original,
                "days_since_last": days_since_last,
                "follow_up_number": len(previous_follow_ups) + 1,
                "has_active_tracking": has_active_tracking,
                "original_assessment_date": original_date.isoformat(),
                "condition": original_assessment.get("primary_assessment", "Unknown condition")
            },
            "validation": {
                "min_questions_required": 1,
                "message": "Please answer at least one question to continue"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting follow-up questions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit")
async def submit_follow_up(request: Request):
    """Submit follow-up responses and generate analysis"""
    try:
        data = await request.json()
        assessment_id = data.get("assessment_id")
        assessment_type = data.get("assessment_type")
        chain_id = data.get("chain_id")
        responses = data.get("responses", {})
        medical_visit = data.get("medical_visit")
        user_id = data.get("user_id")
        
        # Validate and fix UUIDs
        try:
            if chain_id:
                # Validate chain_id is a valid UUID
                uuid.UUID(chain_id)
            else:
                # Generate new chain_id if missing
                chain_id = str(uuid.uuid4())
                logger.info(f"Generated new chain_id: {chain_id}")
        except ValueError:
            # If chain_id is invalid, generate a new one
            logger.warning(f"Invalid chain_id '{chain_id}', generating new one")
            chain_id = str(uuid.uuid4())
        
        # Validate assessment_id
        try:
            uuid.UUID(assessment_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid assessment_id: {assessment_id}")
            raise HTTPException(status_code=400, detail="Invalid assessment_id format")
        
        # Validate user_id if provided
        if user_id:
            try:
                uuid.UUID(user_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid user_id '{user_id}', setting to None")
                user_id = None
        
        # Validate assessment_type
        valid_types = ['quick_scan', 'deep_dive', 'general_assessment', 'general_deepdive']
        if assessment_type not in valid_types:
            logger.error(f"Invalid assessment_type: {assessment_type}")
            raise HTTPException(status_code=400, detail=f"Invalid assessment_type. Must be one of: {valid_types}")
        
        # Validate at least one question was answered
        if not responses or len(responses) == 0:
            raise HTTPException(status_code=400, detail="At least one question must be answered")
        
        # Track event (don't let this fail the request)
        try:
            await track_event(
                chain_id=chain_id,
                user_id=user_id,
                event_type="follow_up_started",
                event_data={"assessment_id": assessment_id}
            )
        except Exception as e:
            logger.warning(f"Failed to track event: {str(e)}")
        
        # Fetch original assessment and chain
        original_assessment = await fetch_original_assessment(assessment_id, assessment_type)
        if not original_assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        previous_follow_ups = await fetch_follow_up_chain(chain_id)
        
        # Calculate temporal data
        created_at = original_assessment.get("created_at")
        if isinstance(created_at, str):
            if created_at.endswith('Z'):
                created_at = created_at[:-1] + '+00:00'
            original_date = datetime.fromisoformat(created_at)
        else:
            original_date = created_at if created_at else datetime.now(timezone.utc)
        days_since_original = (datetime.now(timezone.utc) - original_date).days
        
        # If medical visit, translate jargon
        if medical_visit and medical_visit.get("assessment"):
            medical_visit["layman_explanation"] = await translate_medical_jargon(
                medical_visit["assessment"],
                original_assessment.get("primary_assessment", "")
            )
        
        # Generate comprehensive analysis
        analysis = await generate_follow_up_analysis(
            original_assessment=original_assessment,
            previous_follow_ups=previous_follow_ups,
            current_responses=responses,
            medical_visit=medical_visit,
            days_since_original=days_since_original,
            user_id=user_id
        )
        
        # Calculate confidence change
        original_confidence = float(original_assessment.get("confidence_score", 50))
        new_confidence = float(analysis.get("confidence", original_confidence))
        confidence_change = new_confidence - original_confidence
        
        # Check for pattern discoveries and milestone events
        patterns = await detect_patterns(chain_id, analysis)
        if patterns:
            await track_event(
                chain_id=chain_id,
                user_id=user_id,
                event_type="pattern_discovered",
                event_data={"patterns": patterns}
            )
        
        # Check for confidence milestone
        if new_confidence >= 90 and original_confidence < 90:
            await track_event(
                chain_id=chain_id,
                user_id=user_id,
                event_type="confidence_milestone",
                event_data={"milestone": "90% confidence reached"}
            )
        
        # Check if diagnosis changed
        if analysis.get("primary_assessment") != original_assessment.get("primary_assessment"):
            await track_event(
                chain_id=chain_id,
                user_id=user_id,
                event_type="diagnosis_changed",
                event_data={
                    "from": original_assessment.get("primary_assessment"),
                    "to": analysis.get("primary_assessment")
                }
            )
        
        # Store follow-up in database with error handling
        try:
            follow_up_id = await store_follow_up(
                chain_id=chain_id,
                source_type=assessment_type,
                source_id=assessment_id,
                responses=responses,
                medical_visit=medical_visit,
                analysis=analysis,
                days_since_original=days_since_original,
                follow_up_number=len(previous_follow_ups) + 1,
                user_id=user_id
            )
        except Exception as e:
            logger.error(f"Failed to store follow-up: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to store follow-up: {str(e)}")
        
        # Track completion event (don't let this fail the request)
        try:
            await track_event(
                chain_id=chain_id,
                user_id=user_id,
                event_type="follow_up_completed",
                event_data={
                    "follow_up_id": follow_up_id,
                    "confidence": new_confidence
                }
            )
        except Exception as e:
            logger.warning(f"Failed to track completion event: {str(e)}")
        
        # Build response with all the enhanced fields
        return {
            "follow_up_id": follow_up_id,
            "chain_id": chain_id,
            "assessment": analysis.get("assessment", {}),
            "assessment_evolution": analysis.get("assessment_evolution", {}),
            "progression_narrative": analysis.get("progression_narrative", {}),
            "pattern_insights": analysis.get("pattern_insights", {}),
            "treatment_efficacy": analysis.get("treatment_efficacy", {}),
            "recommendations": analysis.get("recommendations", {}),
            "confidence_indicator": {
                "level": "high" if new_confidence >= 85 else "medium" if new_confidence >= 70 else "low",
                "explanation": f"Confidence improved from {original_confidence:.0f}% to {new_confidence:.0f}%",
                "visual": "⚫" * min(5, int(new_confidence / 20))
            },
            "next_follow_up": analysis.get("next_follow_up", "1 week"),
            "medical_visit_explained": medical_visit.get("layman_explanation") if medical_visit else None,
            "symptom_tracking_integration": await get_tracking_summary(user_id, original_assessment) if user_id else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting follow-up: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/chain/{assessment_id}")
async def get_follow_up_chain(
    assessment_id: str,
    include_events: bool = False
):
    """Get the complete follow-up chain for visualization"""
    try:
        # Get chain_id for the assessment
        chain_result = supabase.table("assessment_follow_ups").select("chain_id").eq("source_id", assessment_id).limit(1).execute()
        
        if not chain_result.data:
            return {
                "chain_id": None,
                "follow_ups": [],
                "total_follow_ups": 0,
                "confidence_progression": [],
                "assessment_progression": [],
                "has_medical_visits": False
            }
        
        chain_id = chain_result.data[0]["chain_id"]
        
        # Fetch all follow-ups in the chain
        follow_ups = await fetch_follow_up_chain(chain_id)
        
        # Fetch events if requested
        events = []
        if include_events:
            events_result = supabase.table("follow_up_events").select("*").eq("chain_id", chain_id).order("event_timestamp").execute()
            events = events_result.data if events_result.data else []
        
        # Build progression arrays
        confidence_progression = [f["confidence_score"] for f in follow_ups]
        assessment_progression = [f["primary_assessment"] for f in follow_ups]
        
        # Check for medical visits
        has_medical_visits = any(f.get("medical_visit") is not None for f in follow_ups)
        
        return {
            "chain_id": chain_id,
            "follow_ups": follow_ups,
            "events": events,
            "total_follow_ups": len(follow_ups),
            "confidence_progression": confidence_progression,
            "assessment_progression": assessment_progression,
            "has_medical_visits": has_medical_visits,
            "peak_confidence": max(confidence_progression) if confidence_progression else 0,
            "latest_assessment": assessment_progression[-1] if assessment_progression else None,
            "total_days_tracked": follow_ups[-1]["days_since_original"] if follow_ups else 0
        }
        
    except Exception as e:
        logger.error(f"Error fetching follow-up chain: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/medical-visit/explain")
async def explain_medical_terms(request: Request):
    """Translate medical jargon to plain English"""
    try:
        data = await request.json()
        medical_terms = data.get("medical_terms")
        context = data.get("context", "")
        
        if not medical_terms:
            raise HTTPException(status_code=400, detail="medical_terms is required")
        
        explanation = await translate_medical_jargon(medical_terms, context)
        
        return {
            "original": medical_terms,
            "explanation": explanation,
            "key_takeaways": await extract_key_takeaways(explanation),
            "action_items": await extract_action_items(explanation)
        }
        
    except Exception as e:
        logger.error(f"Error explaining medical terms: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions

async def fetch_original_assessment(assessment_id: str, assessment_type: str) -> Dict[str, Any]:
    """Fetch the original assessment based on type"""
    table_map = {
        "quick_scan": "quick_scans",
        "deep_dive": "deep_dive_sessions",
        "general_assessment": "general_assessments",
        "general_deepdive": "general_deepdive_sessions"
    }
    
    table = table_map.get(assessment_type)
    if not table:
        raise ValueError(f"Invalid assessment type: {assessment_type}")
    
    logger.info(f"Fetching assessment from table '{table}' with id '{assessment_id}'")
    result = supabase.table(table).select("*").eq("id", assessment_id).execute()
    logger.info(f"Query result: {len(result.data) if result.data else 0} rows found")
    if result.data:
        logger.info(f"Assessment found: {result.data[0].get('id', 'no id')}")
    return result.data[0] if result.data else None

async def get_or_create_chain_id(assessment_id: str, assessment_type: str) -> str:
    """Get existing chain_id or create a new one"""
    # Check if a chain already exists for this assessment
    result = supabase.table("assessment_follow_ups").select("chain_id").eq("source_id", assessment_id).limit(1).execute()
    
    if result.data:
        return result.data[0]["chain_id"]
    else:
        return str(uuid.uuid4())

async def fetch_follow_up_chain(chain_id: str) -> List[Dict[str, Any]]:
    """Fetch all follow-ups in a chain"""
    result = supabase.table("assessment_follow_ups").select("*").eq("chain_id", chain_id).order("follow_up_number").execute()
    return result.data if result.data else []

async def check_active_symptom_tracking(user_id: str, assessment: Dict[str, Any]) -> bool:
    """Check if user has active symptom tracking for this condition"""
    if not user_id:
        return False
    
    # Extract condition/symptom keywords from assessment
    condition = assessment.get("primary_assessment", "")
    symptoms = assessment.get("symptoms", [])
    
    # Check tracking configurations
    result = supabase.table("tracking_configurations").select("*").eq("user_id", user_id).eq("status", "approved").execute()
    
    if result.data:
        for config in result.data:
            # Check if any tracking matches the condition
            if condition.lower() in config.get("metric_name", "").lower():
                return True
            for symptom in symptoms:
                if symptom.lower() in config.get("metric_name", "").lower():
                    return True
    
    return False

async def generate_ai_questions(
    original_assessment: Dict[str, Any],
    assessment_type: str,
    previous_follow_ups: List[Dict[str, Any]],
    days_since_original: int,
    days_since_last: int,
    user_id: Optional[str],
    has_active_tracking: bool
) -> List[Dict[str, str]]:
    """Generate 3 specific AI questions based on the case"""
    
    # Gather comprehensive context
    medical_data = {}
    if user_id:
        medical_data = await get_user_medical_data(user_id)
    
    # Build prompt for AI
    system_prompt = """You are generating follow-up questions for a medical condition.
    Generate EXACTLY 3 specific, actionable questions that:
    1. Reference specific details from the original assessment
    2. Track specific interventions or treatments tried
    3. Are answerable based on the patient's current experience
    4. Help refine the diagnosis or track progression
    
    Return JSON array with 3 questions:
    [
        {
            "id": "ai_q1",
            "question": "Specific question text",
            "type": "text",
            "category": "symptom_tracking|treatment_efficacy|pattern_discovery",
            "rationale": "Why this question matters"
        }
    ]"""
    
    # Extract key information from assessment
    condition = original_assessment.get("primary_assessment", "Unknown condition")
    symptoms = original_assessment.get("symptoms", [])
    severity = original_assessment.get("severity_level", "moderate")
    form_data = original_assessment.get("form_data", {})
    
    # Build context about progression if there are previous follow-ups
    progression_context = ""
    if previous_follow_ups:
        last_follow_up = previous_follow_ups[-1]
        progression_context = f"""
        Previous follow-up {days_since_last} days ago showed:
        - Assessment: {last_follow_up.get('primary_assessment')}
        - Confidence: {last_follow_up.get('confidence_score')}%
        - Key findings: {', '.join(last_follow_up.get('key_findings', [])[:3])}
        """
    
    user_prompt = f"""Generate 3 follow-up questions for this case:
    
    ORIGINAL CONDITION ({days_since_original} days ago):
    - Diagnosis: {condition}
    - Symptoms: {', '.join(symptoms[:5]) if symptoms else 'Not specified'}
    - Severity: {severity}
    - User reported: {form_data.get('symptoms', 'Not specified')}
    - Pain level: {form_data.get('painLevel', 'N/A')}/10
    
    {progression_context}
    
    TIME CONTEXT:
    - Days since original: {days_since_original}
    - Days since last check: {days_since_last}
    - Has active tracking: {has_active_tracking}
    
    MEDICAL CONTEXT:
    - Medications: {medical_data.get('medications', [])}
    - Conditions: {medical_data.get('personal_health_context', 'None')}
    
    Generate questions that are SPECIFIC to THIS person's case, not generic.
    Reference their specific symptoms, timeline, and what they've tried."""
    
    try:
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="deepseek/deepseek-chat",
            temperature=0.7
        )
        
        # Extract JSON from response
        content = llm_response.get("content", "")
        questions = extract_json_from_text(content)
        
        if questions and isinstance(questions, list) and len(questions) >= 3:
            return questions[:3]
        else:
            # Fallback questions if AI generation fails
            return [
                {
                    "id": "ai_q1",
                    "question": f"How has your {condition.lower()} progressed over the past {days_since_last} days?",
                    "type": "text",
                    "category": "symptom_tracking",
                    "rationale": "Track progression over time"
                },
                {
                    "id": "ai_q2",
                    "question": "What treatments or interventions have you tried, and how effective were they?",
                    "type": "text",
                    "category": "treatment_efficacy",
                    "rationale": "Assess treatment effectiveness"
                },
                {
                    "id": "ai_q3",
                    "question": "Have you noticed any patterns in when symptoms are better or worse?",
                    "type": "text",
                    "category": "pattern_discovery",
                    "rationale": "Identify triggers and patterns"
                }
            ]
    except Exception as e:
        logger.error(f"Error generating AI questions: {str(e)}")
        # Return fallback questions
        return [
            {
                "id": "ai_q1",
                "question": f"How has your condition changed in the {days_since_last} days since we last checked?",
                "type": "text",
                "category": "symptom_tracking",
                "rationale": "Track changes"
            },
            {
                "id": "ai_q2",
                "question": "What have you been doing to manage your symptoms?",
                "type": "text",
                "category": "treatment_efficacy",
                "rationale": "Track management"
            },
            {
                "id": "ai_q3",
                "question": "Is there anything new you've noticed about your condition?",
                "type": "text",
                "category": "pattern_discovery",
                "rationale": "Discover new information"
            }
        ]

async def translate_medical_jargon(medical_text: str, context: str) -> str:
    """Translate medical terminology to plain English"""
    system_prompt = """You are a medical translator helping patients understand their doctor's assessment.
    Translate medical jargon into clear, simple English that anyone can understand.
    Keep the same meaning but make it accessible.
    Include what it means for the patient's daily life.
    
    Return a clear explanation in 2-3 paragraphs."""
    
    user_prompt = f"""Translate this medical assessment to plain English:
    
    Doctor's assessment: {medical_text}
    
    Context about condition: {context}
    
    Explain:
    1. What the doctor is saying in simple terms
    2. What this means for the patient
    3. Any important action items or next steps"""
    
    try:
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="openai/gpt-5-mini",
            temperature=0.3
        )
        
        return llm_response.get("content", medical_text)
    except Exception as e:
        logger.error(f"Error translating medical jargon: {str(e)}")
        return medical_text

async def generate_follow_up_analysis(
    original_assessment: Dict[str, Any],
    previous_follow_ups: List[Dict[str, Any]],
    current_responses: Dict[str, Any],
    medical_visit: Optional[Dict[str, Any]],
    days_since_original: int,
    user_id: Optional[str]
) -> Dict[str, Any]:
    """Generate comprehensive follow-up analysis"""
    
    # Gather all context
    medical_data = {}
    if user_id:
        medical_data = await get_user_medical_data(user_id)
    
    # Build progression history
    confidence_history = [original_assessment.get("confidence_score", 50)]
    assessment_history = [original_assessment.get("primary_assessment", "Unknown")]
    
    for follow_up in previous_follow_ups:
        confidence_history.append(follow_up.get("confidence_score", 50))
        assessment_history.append(follow_up.get("primary_assessment", "Unknown"))
    
    system_prompt = """You are analyzing a follow-up assessment for a medical condition.
    Consider the progression over time and new information provided.
    
    Return comprehensive JSON analysis with:
    {
        "assessment": {
            "condition": "refined diagnosis with confidence",
            "confidence": 0-100,
            "severity": "low|moderate|high|urgent",
            "progression": "improving|stable|worsening"
        },
        "assessment_evolution": {
            "original_assessment": "what it was",
            "current_assessment": "what it is now",
            "confidence_change": "explanation",
            "diagnosis_refined": true/false,
            "key_discoveries": ["discovery1", "discovery2"]
        },
        "progression_narrative": {
            "summary": "narrative of progression",
            "details": "detailed explanation",
            "milestone": "next milestone to watch for"
        },
        "pattern_insights": {
            "discovered_patterns": ["pattern1", "pattern2"],
            "concerning_patterns": []
        },
        "treatment_efficacy": {
            "working": ["treatment1"],
            "not_working": ["treatment2"],
            "should_try": ["treatment3"]
        },
        "recommendations": {
            "immediate": ["action1"],
            "this_week": ["action2"],
            "consider": ["action3"],
            "next_follow_up": "timing recommendation"
        },
        "confidence": 0-100,
        "primary_assessment": "main diagnosis",
        "urgency": "low|medium|high|emergency"
    }"""
    
    # Format responses for analysis
    response_summary = f"""
    Changes since last time: {current_responses.get('q1', 'Not answered')}
    Specific changes: {current_responses.get('q2', 'Not answered')}
    Symptom severity: {current_responses.get('q3', 'Not answered')}
    New triggers/patterns: {current_responses.get('q4', 'Not answered')}
    Saw doctor: {current_responses.get('q5', 'No')}
    """
    
    # Add AI question responses
    for i in range(1, 4):
        key = f"ai_q{i}"
        if key in current_responses:
            response_summary += f"\nAI Question {i}: {current_responses[key]}"
    
    # Add medical visit info if present
    medical_visit_context = ""
    if medical_visit:
        medical_visit_context = f"""
        MEDICAL VISIT:
        Provider: {medical_visit.get('provider_type', 'Unknown')}
        Assessment: {medical_visit.get('assessment', 'Not provided')}
        Treatments: {medical_visit.get('treatments', 'None')}
        Follow-up: {medical_visit.get('follow_up_timing', 'As needed')}
        """
    
    user_prompt = f"""Analyze this follow-up assessment:
    
    ORIGINAL ASSESSMENT ({days_since_original} days ago):
    Condition: {original_assessment.get('primary_assessment')}
    Confidence: {original_assessment.get('confidence_score')}%
    Symptoms: {original_assessment.get('symptoms', [])}
    
    CONFIDENCE PROGRESSION: {confidence_history}
    ASSESSMENT PROGRESSION: {assessment_history}
    
    CURRENT FOLLOW-UP RESPONSES:
    {response_summary}
    
    {medical_visit_context}
    
    MEDICAL CONTEXT:
    {medical_data}
    
    Provide a comprehensive analysis that shows evolution and refinement of understanding."""
    
    try:
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="deepseek/deepseek-chat",
            temperature=0.5
        )
        
        content = llm_response.get("content", "")
        analysis = extract_json_from_text(content)
        
        if not analysis:
            # Fallback analysis
            analysis = {
                "assessment": {
                    "condition": original_assessment.get("primary_assessment", "Unknown"),
                    "confidence": min(100, original_assessment.get("confidence_score", 50) + 10),
                    "severity": "moderate",
                    "progression": "stable"
                },
                "confidence": min(100, original_assessment.get("confidence_score", 50) + 10),
                "primary_assessment": original_assessment.get("primary_assessment", "Unknown"),
                "urgency": "medium"
            }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error generating follow-up analysis: {str(e)}")
        # Return minimal analysis
        return {
            "assessment": {
                "condition": original_assessment.get("primary_assessment", "Unknown"),
                "confidence": original_assessment.get("confidence_score", 50),
                "severity": "moderate",
                "progression": "unknown"
            },
            "confidence": original_assessment.get("confidence_score", 50),
            "primary_assessment": original_assessment.get("primary_assessment", "Unknown"),
            "urgency": "medium",
            "recommendations": {
                "immediate": ["Continue monitoring symptoms"],
                "next_follow_up": "1 week"
            }
        }

async def detect_patterns(chain_id: str, analysis: Dict[str, Any]) -> List[str]:
    """Detect patterns in the follow-up chain"""
    patterns = []
    
    # Check for patterns in the analysis
    if "pattern_insights" in analysis:
        patterns.extend(analysis["pattern_insights"].get("discovered_patterns", []))
    
    # Add concerning patterns if any
    if "concerning_patterns" in analysis.get("pattern_insights", {}):
        patterns.extend(analysis["pattern_insights"]["concerning_patterns"])
    
    return patterns

async def store_follow_up(
    chain_id: str,
    source_type: str,
    source_id: str,
    responses: Dict[str, Any],
    medical_visit: Optional[Dict[str, Any]],
    analysis: Dict[str, Any],
    days_since_original: int,
    follow_up_number: int,
    user_id: Optional[str]
) -> str:
    """Store follow-up in database"""
    
    # Prepare base responses
    base_responses = {
        "changes_since_last": responses.get("q1"),
        "specific_changes": responses.get("q2"),
        "severity_change": responses.get("q3"),
        "new_triggers": {
            "found": responses.get("q4") == "Yes",
            "description": responses.get("q4_text", "")
        },
        "saw_doctor": responses.get("q5", False)
    }
    
    # Prepare AI questions
    ai_questions = []
    for i in range(1, 4):
        key = f"ai_q{i}"
        if key in responses:
            ai_questions.append({
                "question": f"Question {i}",  # This should come from the original questions
                "response": responses[key]
            })
    
    # Get previous follow-up if exists
    previous_result = supabase.table("assessment_follow_ups").select("id").eq("chain_id", chain_id).order("follow_up_number", desc=True).limit(1).execute()
    parent_id = previous_result.data[0]["id"] if previous_result.data else None
    
    # Calculate days since last follow-up
    days_since_last = None
    if previous_result.data:
        prev_follow_up = supabase.table("assessment_follow_ups").select("created_at").eq("id", parent_id).execute()
        if prev_follow_up.data:
            prev_date = datetime.fromisoformat(prev_follow_up.data[0]["created_at"])
            days_since_last = (datetime.now(timezone.utc) - prev_date).days
    
    # Get original assessment date
    original = await fetch_original_assessment(source_id, source_type)
    if not original:
        # If no original found, use current time as fallback
        original_date = datetime.now(timezone.utc)
        original_confidence = 50.0
    else:
        created_at = original.get("created_at")
        if isinstance(created_at, str):
            if created_at.endswith('Z'):
                created_at = created_at[:-1] + '+00:00'
            original_date = datetime.fromisoformat(created_at)
        else:
            original_date = created_at if created_at else datetime.now(timezone.utc)
        original_confidence = float(original.get("confidence_score", 50))
    
    # Ensure assessment_evolution has a value (it's NOT NULL in database)
    assessment_evolution = analysis.get("assessment_evolution", {})
    if not assessment_evolution:
        assessment_evolution = {
            "original_assessment": original.get("primary_assessment", "Unknown") if original else "Unknown",
            "current_assessment": analysis.get("primary_assessment", "Unknown"),
            "confidence_change": f"{original_confidence}% -> {float(analysis.get('confidence', 50))}%",
            "diagnosis_refined": False,
            "key_discoveries": []
        }
    
    # Insert follow-up
    follow_up_data = {
        "chain_id": chain_id,
        "user_id": user_id,
        "source_type": source_type,
        "source_id": source_id,
        "parent_follow_up_id": parent_id,
        "original_assessment_date": original_date.isoformat(),
        "days_since_original": days_since_original,
        "days_since_last_followup": days_since_last,
        "follow_up_number": follow_up_number,
        "base_responses": base_responses if base_responses else {},
        "ai_questions": ai_questions if ai_questions else [],
        "medical_visit": medical_visit,
        "analysis_result": analysis if analysis else {},
        "primary_assessment": analysis.get("primary_assessment", "Unknown"),
        "confidence_score": float(analysis.get("confidence", 50)),
        "confidence_change": float(analysis.get("confidence", 50)) - original_confidence,
        "diagnostic_certainty": assessment_evolution.get("diagnostic_certainty", "provisional"),
        "assessment_evolution": assessment_evolution,  # Now guaranteed to have a value
        "pattern_insights": analysis.get("pattern_insights", {}),
        "discovered_patterns": analysis.get("pattern_insights", {}).get("discovered_patterns", []),
        "concerning_patterns": analysis.get("pattern_insights", {}).get("concerning_patterns", []),
        "treatment_efficacy": analysis.get("treatment_efficacy", {}),
        "recommendations": analysis.get("recommendations", {}).get("immediate", []),
        "immediate_actions": analysis.get("recommendations", {}).get("immediate", []),
        "red_flags": analysis.get("pattern_insights", {}).get("concerning_patterns", []),
        "urgency_level": analysis.get("urgency", "medium"),
        "next_follow_up_suggested": analysis.get("recommendations", {}).get("next_follow_up", "1 week"),
        "model_used": "deepseek/deepseek-chat",
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        result = supabase.table("assessment_follow_ups").insert(follow_up_data).execute()
    except Exception as e:
        logger.error(f"Database insert failed: {str(e)}")
        logger.error(f"Follow-up data: {json.dumps(follow_up_data, default=str)}")
        raise Exception(f"Database insert failed: {str(e)}")
    
    # Store medical visit separately if present
    if medical_visit and result.data:
        follow_up_id = result.data[0]["id"]
        medical_visit_data = {
            "user_id": user_id,
            "follow_up_id": follow_up_id,
            "visit_date": datetime.now(timezone.utc).date().isoformat(),
            "provider_type": medical_visit.get("provider_type", "unknown"),
            "assessment": medical_visit.get("assessment", ""),
            "layman_explanation": medical_visit.get("layman_explanation", ""),
            "follow_up_timing": medical_visit.get("follow_up_timing", "")
        }
        supabase.table("medical_visits").insert(medical_visit_data).execute()
    
    return result.data[0]["id"] if result.data else str(uuid.uuid4())

async def track_event(
    chain_id: str,
    user_id: Optional[str],
    event_type: str,
    event_data: Dict[str, Any]
) -> None:
    """Track events for audit trail"""
    try:
        # Validate chain_id
        try:
            uuid.UUID(chain_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid chain_id for event tracking: {chain_id}")
            return
        
        # Validate user_id if provided
        if user_id:
            try:
                uuid.UUID(user_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid user_id for event tracking: {user_id}")
                user_id = None
        
        event = {
            "chain_id": chain_id,
            "user_id": user_id,
            "event_type": event_type,
            "event_data": event_data
        }
        supabase.table("follow_up_events").insert(event).execute()
    except Exception as e:
        logger.warning(f"Failed to track event: {str(e)}")

async def get_tracking_summary(user_id: str, assessment: Dict[str, Any]) -> Dict[str, Any]:
    """Get symptom tracking summary if available"""
    # This would integrate with your existing tracking system
    # For now, returning a placeholder
    return {
        "is_tracking": False,
        "summary": None
    }

async def extract_key_takeaways(explanation: str) -> List[str]:
    """Extract key takeaways from medical explanation"""
    # Simple extraction - could be enhanced with AI
    takeaways = []
    lines = explanation.split('\n')
    for line in lines:
        if any(keyword in line.lower() for keyword in ['important', 'key', 'main', 'critical', 'must']):
            takeaways.append(line.strip())
    return takeaways[:3] if takeaways else ["Follow doctor's recommendations", "Monitor symptoms", "Return if worsening"]

async def extract_action_items(explanation: str) -> List[str]:
    """Extract action items from medical explanation"""
    # Simple extraction - could be enhanced with AI
    actions = []
    lines = explanation.split('\n')
    for line in lines:
        if any(keyword in line.lower() for keyword in ['should', 'need to', 'must', 'take', 'schedule']):
            actions.append(line.strip())
    return actions[:3] if actions else ["Follow treatment plan", "Track symptoms", "Follow up as directed"]