"""General Assessment API endpoints for non-body-specific health concerns"""
from fastapi import APIRouter, Request, HTTPException
from typing import Optional, Dict, Any, List
import json
import uuid
import os
from datetime import datetime, timezone
import logging

from models.requests import (
    FlashAssessmentRequest,
    GeneralAssessmentRequest,
    GeneralAssessmentRefineRequest,
    GeneralDeepDiveStartRequest,
    GeneralDeepDiveContinueRequest,
    GeneralDeepDiveCompleteRequest
)
from utils.json_parser import extract_json_from_text
from utils.data_gathering import get_user_medical_data
from utils.assessment_formatter import (
    add_general_assessment_fields,
    add_minimal_fields,
    enhance_general_assessment_prompt
)
from utils.db_storage import (
    store_enhanced_fields_for_general_assessment,
    store_enhanced_fields_for_general_deepdive
)
from business_logic import call_llm
from supabase_client import supabase

router = APIRouter(prefix="/api", tags=["general_assessment"])
logger = logging.getLogger(__name__)

# Category-specific system prompts
CATEGORY_PROMPTS = {
    "energy": """You are analyzing energy and fatigue concerns. Consider:
- Circadian rhythm disruptions
- Sleep quality vs quantity  
- Nutritional deficiencies (B12, iron, vitamin D)
- Thyroid and hormonal issues
- Chronic fatigue syndrome patterns
- Post-viral fatigue
- Medication side effects from user's current meds: {medications}
- Physical activity levels and deconditioning""",
    
    "mental": """You are analyzing mental health concerns. Consider:
- Mood disorders (depression, bipolar)
- Anxiety disorders
- Stress-related conditions
- Trauma responses
- Medication interactions from: {medications}
- Sleep-mood connections
- Cognitive symptoms vs emotional symptoms
- Social and environmental factors
Note: Be supportive and non-judgmental in all responses.""",
    
    "sick": """You are analyzing acute illness symptoms. Consider:
- Infectious vs non-infectious causes
- Symptom progression timeline
- Contagion risk
- Dehydration signs
- When to seek immediate care
- User's chronic conditions that may complicate: {conditions}
- Recent exposures or travel
- Seasonal patterns""",
    
    "medication": """You are analyzing potential medication side effects. Consider:
- User's current medications: {medications}
- Drug interactions
- Timing of symptoms vs medication schedule
- Dose-dependent effects
- Alternative medications
- When to contact prescriber
- Distinguishing side effects from underlying conditions""",
    
    "multiple": """You are analyzing multiple concurrent health issues. Consider:
- Systemic conditions that cause multiple symptoms
- Medication cascades
- Stress/anxiety manifesting physically
- Autoimmune conditions
- Whether symptoms are related or separate
- Priority of addressing each issue
- Potential common underlying causes""",
    
    "unsure": """You are helping someone who isn't sure what's wrong. Consider:
- Vague or non-specific symptoms
- Somatization of stress/anxiety
- Early-stage conditions
- Need for basic health screening
- Importance of validation and support
- Gentle guidance toward appropriate care
- Pattern recognition from symptom clusters""",
    
    "physical": """You are analyzing physical pain and injuries. Consider:
- Musculoskeletal vs neurological causes
- Injury patterns and mechanisms
- Red flags requiring immediate care
- Movement patterns and compensations
- Referred pain possibilities
- Chronic vs acute presentation
- Impact on daily activities
- Previous injuries in the area""",
    
    "digestive": """You are analyzing digestive and gastrointestinal concerns. Consider:
- Upper vs lower GI issues
- Functional vs organic disease
- Food intolerances and triggers
- Inflammatory bowel conditions
- Red flags for GI malignancy
- User's medications affecting GI: {medications}
- Chronic conditions: {conditions}""",
    
    "breathing": """You are analyzing breathing and chest symptoms. Consider:
- Cardiac vs pulmonary causes
- Anxiety-related dyspnea
- Severity and functional impact
- Environmental triggers
- Red flags for emergency conditions
- User's medications: {medications}
- Chronic conditions: {conditions}""",
    
    "skin": """You are analyzing skin and hair concerns. Consider:
- Inflammatory vs infectious causes
- Distribution patterns
- Systemic disease manifestations
- Hair loss patterns
- Medication reactions from: {medications}
- Underlying conditions: {conditions}""",
    
    "hormonal": """You are analyzing hormonal and endocrine concerns. Consider:
- Sex-specific hormonal issues
- Thyroid and metabolic disorders
- Reproductive health
- Age-related changes
- Medication effects: {medications}
- Endocrine conditions: {conditions}
Note: Tailor assessment based on biological sex.""",
    
    "neurological": """You are analyzing neurological symptoms. Consider:
- Central vs peripheral nervous system
- Headache classification
- Red flags for serious pathology
- Stroke/TIA symptoms
- Movement and cognitive issues
- CNS-affecting medications: {medications}
- Neurological conditions: {conditions}"""
}

@router.post("/flash-assessment")
async def flash_assessment(request: Request):
    """Quick triage assessment from free text input"""
    try:
        data = await request.json()
        user_query = data.get("user_query")
        user_id = data.get("user_id")
        
        if not user_query:
            raise HTTPException(status_code=400, detail="user_query is required")
        
        # Fetch user medical data if user_id provided
        user_medical_data = {}
        if user_id:
            try:
                user_medical_data = await get_user_medical_data(user_id)
                logger.info(f"Fetched medical data for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to fetch medical data: {str(e)}")
                user_medical_data = {}
        
        # Build system prompt
        try:
            medical_context = format_medical_data(user_medical_data) if user_medical_data else "No medical history available"
        except Exception as e:
            logger.error(f"Error formatting medical data: {str(e)}")
            medical_context = "No medical history available"
        
        system_prompt = f"""You are a medical triage AI. Handle symptoms, concerns, and health questions professionally.
        
User Medical Context:
{medical_context}

For SYMPTOMS (e.g., "my chest hurts"):
"[Symptom] could indicate [2-3 conditions]. Key factors: [differentiators]. Urgency: [level]. Next: [action]."

For QUESTIONS (e.g., "is this normal after taking medication?"):
"[Direct answer]. [Medical context/explanation]. [If concerning, what to watch for]. [Action if needed]."

For CONCERNS (e.g., "worried about these symptoms together"):
"Your symptoms suggest [assessment]. [What makes this more/less concerning]. [Clear recommendation]."

Keep it professional but human - like a skilled triage nurse. Be direct, no fluff.

Respond in JSON format:
{{
    "response": "Your assessment (2-4 sentences max)",
    "main_concern": "core issue identified",
    "urgency": "low|medium|high|emergency",
    "confidence": 0-100,
    "next_action": "general-assessment|body-scan|see-doctor|monitor",
    "action_reason": "Why this action (be specific)"
}}"""

        # Call LLM
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            model="openai/gpt-5-mini",  # was: google/gemini-2.5-flash-lite
            temperature=0.7
        )
        
        logger.info(f"LLM Response: {str(llm_response)[:500]}...")  # Log first 500 chars
        
        # Extract content from response
        if isinstance(llm_response, dict):
            llm_content = llm_response.get('content', '')
        else:
            llm_content = str(llm_response)
        
        # Clean up markdown blocks if present
        if '```json' in llm_content:
            llm_content = llm_content.replace('```json', '').replace('```', '').strip()
        
        logger.info(f"Cleaned content: {llm_content[:500]}...")
        
        # Parse response
        try:
            parsed = extract_json_from_text(llm_content)
            logger.info(f"Parsed result: {parsed}")
            if not parsed:
                logger.warning("Failed to parse JSON from LLM response, using defaults")
                parsed = {
                    "response": llm_content if llm_content else "I understand your concern. Let me help you with that.",
                    "main_concern": "Unable to extract",
                    "urgency": "medium", 
                    "confidence": 70,
                    "next_action": "general-assessment",
                    "action_reason": "Further assessment needed"
                }
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            parsed = {
                "response": "I understand your concern. Let me help assess your situation.",
                "main_concern": user_query[:100],  # First 100 chars of query
                "urgency": "medium",
                "confidence": 50,
                "next_action": "general-assessment", 
                "action_reason": "Need more information"
            }
        
        # Save to database
        # Convert user_id to UUID if it's provided as string
        if user_id and isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except ValueError:
                pass  # Keep as string if not valid UUID
        
        # Save to database with error handling
        try:
            flash_result = supabase.table("flash_assessments").insert({
                "user_id": str(user_id) if user_id else None,
                "user_query": user_query,
                "ai_response": parsed.get("response", ""),
                "main_concern": parsed.get("main_concern", ""),
                "urgency": parsed.get("urgency", "medium"),
                "confidence_score": float(parsed.get("confidence", 70)),  # Ensure it's a float
                "suggested_next_action": parsed.get("next_action", "general-assessment"),
                "model_used": "google/gemini-2.5-flash-lite",
                "category": None  # Flash assessments don't have a specific category
            }).execute()
            
            flash_id = flash_result.data[0]["id"] if flash_result.data else str(uuid.uuid4())
        except Exception as e:
            logger.error(f"Database insert error: {str(e)}")
            # Return response even if DB save fails
            flash_id = str(uuid.uuid4())
        
        response_dict = {
            "flash_id": flash_id,
            "response": parsed.get("response", ""),
            "main_concern": parsed.get("main_concern", ""),
            "urgency": parsed.get("urgency", "medium"),
            "confidence": parsed.get("confidence", 70),
            "next_steps": {
                "recommended_action": parsed.get("next_action", "general-assessment"),
                "reason": parsed.get("action_reason", "")
            }
        }
        
        logger.info(f"Returning response: {json.dumps(response_dict, indent=2)}")
        return response_dict
        
    except Exception as e:
        logger.error(f"Flash assessment error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/general-assessment")
async def general_assessment(request: Request):
    """Structured category-based health assessment"""
    try:
        data = await request.json()
        category = data.get("category")
        form_data = data.get("form_data", {})
        user_id = data.get("user_id")
        
        if not category:
            raise HTTPException(status_code=400, detail="category is required")
        
        if category not in CATEGORY_PROMPTS:
            raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {list(CATEGORY_PROMPTS.keys())}")
        
        # Fetch user medical data
        user_medical_data = {}
        if user_id:
            user_medical_data = await get_user_medical_data(user_id)
        
        # Build category-specific system prompt
        system_prompt = build_category_prompt(category, user_medical_data)
        
        # Format form data for analysis
        symptoms_context = format_form_data(form_data, category)
        
        # Build analysis request
        analysis_prompt = f"""Patient presents with the following in the {category} category:
{symptoms_context}

Provide a comprehensive analysis in JSON format:
{{
    "primary_assessment": "main clinical impression",
    "confidence": 0-100,
    "key_findings": ["finding1", "finding2", ...],
    "possible_causes": [
        {{"condition": "name", "likelihood": 0-100, "explanation": "why this is possible"}}
    ],
    "recommendations": ["specific recommendation 1", "recommendation 2", ...],
    "urgency": "low|medium|high|emergency",
    "follow_up_questions": ["question to clarify diagnosis", ...],
    "severity_level": "low|moderate|high|urgent",
    "confidence_level": "low|medium|high",
    "what_this_means": "Plain English explanation of what symptoms indicate (2-3 sentences, no medical jargon)",
    "immediate_actions": ["3-5 specific actionable steps to take right now"],
    "red_flags": ["Specific warning signs requiring immediate medical attention"],
    "tracking_metrics": ["3-4 specific symptoms/measurements to monitor daily with how to measure"],
    "follow_up_timeline": {{
        "check_progress": "When to reassess (e.g., '3 days')",
        "see_doctor_if": "Specific conditions for seeking medical care"
    }}
}}

Example for what_this_means:
- Good: "Your fatigue and difficulty concentrating suggest your body is dealing with stress. This pattern is common and usually responds well to lifestyle adjustments."
- Avoid: "You have chronic fatigue syndrome with cognitive dysfunction."
"""

        # Call LLM
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": analysis_prompt}
            ],
            model="openai/gpt-5-mini",  # was: deepseek/deepseek-chat
            temperature=0.6
        )
        
        logger.info(f"General assessment LLM Response: {str(llm_response)[:500]}...")
        
        # Extract content from response
        if isinstance(llm_response, dict):
            llm_content = llm_response.get('content', '')
        else:
            llm_content = str(llm_response)
        
        # Clean up markdown blocks if present
        if '```json' in llm_content:
            llm_content = llm_content.replace('```json', '').replace('```', '').strip()
        
        # Parse response
        analysis = extract_json_from_text(llm_content)
        if not analysis:
            analysis = {
                "primary_assessment": "Unable to parse response",
                "confidence": 50,
                "key_findings": [],
                "possible_causes": [],
                "recommendations": ["Please consult with a healthcare provider"],
                "urgency": "medium",
                "follow_up_questions": []
            }
        
        # Add new required fields using formatter
        analysis = add_general_assessment_fields({
            "analysis": analysis
        }, llm_generated=analysis)
        
        # Extract analysis back out since we wrapped it
        if "analysis" in analysis:
            base_analysis = analysis["analysis"]
            del analysis["analysis"]
            # Merge base analysis fields back
            for key, value in base_analysis.items():
                if key not in analysis:
                    analysis[key] = value
        
        logger.info(f"Enhanced analysis with new fields: severity={analysis.get('severity_level')}, confidence={analysis.get('confidence_level')}")
        
        # Save to database
        try:
            assessment_result = supabase.table("general_assessments").insert({
                "user_id": str(user_id) if user_id else None,
                "category": category,
                "form_data": form_data,
                "analysis_result": analysis,
                "primary_assessment": analysis.get("primary_assessment", ""),
                "confidence_score": float(analysis.get("confidence", 50)),
                "urgency_level": analysis.get("urgency", "medium"),
                "recommendations": analysis.get("recommendations", []),
                "model_used": "deepseek/deepseek-chat"
            }).execute()
        except Exception as e:
            logger.error(f"Database insert error: {str(e)}")
            # Try to return success even if DB fails
            assessment_result = type('obj', (object,), {'data': [{'id': str(uuid.uuid4())}]})
        
        assessment_id = assessment_result.data[0]["id"] if assessment_result.data else str(uuid.uuid4())
        
        # Store the enhanced fields in the database
        try:
            store_enhanced_fields_for_general_assessment(assessment_id, analysis)
        except Exception as storage_error:
            logger.warning(f"Failed to store enhanced fields: {storage_error}")
        
        return {
            "assessment_id": assessment_id,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"General assessment error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/general-assessment/refine")
async def refine_general_assessment(request: Request):
    """Refine an existing general assessment by answering follow-up questions"""
    try:
        data = await request.json()
        assessment_id = data.get("assessment_id")
        answers = data.get("answers", [])
        user_id = data.get("user_id")
        
        if not assessment_id:
            raise HTTPException(status_code=400, detail="assessment_id is required")
        if not answers:
            raise HTTPException(status_code=400, detail="answers are required")
        
        # Fetch original assessment
        logger.info(f"Fetching original assessment: {assessment_id}")
        assessment_result = supabase.table("general_assessments").select("*").eq("id", assessment_id).single().execute()
        
        if not assessment_result.data:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        original_assessment = assessment_result.data
        
        # Extract original data
        category = original_assessment.get("category")
        form_data = original_assessment.get("form_data", {})
        original_analysis = original_assessment.get("analysis_result", {})
        original_confidence = float(original_analysis.get("confidence", 50))
        follow_up_questions = original_analysis.get("follow_up_questions", [])
        
        # Validate that we have follow-up questions
        if not follow_up_questions:
            raise HTTPException(status_code=400, detail="Original assessment has no follow-up questions")
        
        # Fetch user medical data if available
        user_medical_data = {}
        if user_id:
            user_medical_data = await get_user_medical_data(user_id)
        
        # Format Q&A pairs for context
        qa_pairs = []
        for answer_obj in answers:
            question = answer_obj.get("question", "")
            answer = answer_obj.get("answer", "")
            if question and answer:
                qa_pairs.append(f"Q: {question}\nA: {answer}")
        
        qa_context = "\n\n".join(qa_pairs)
        
        # Build refinement prompt
        system_prompt = build_category_prompt(category, user_medical_data)
        
        refinement_prompt = f"""You are refining a previous assessment with additional information from follow-up questions.

ORIGINAL ASSESSMENT:
Category: {category}
Initial Symptoms: {format_form_data(form_data, category)}

Initial Analysis:
- Primary Assessment: {original_analysis.get('primary_assessment', 'Unknown')}
- Confidence: {original_confidence}%
- Key Findings: {', '.join(original_analysis.get('key_findings', []))}
- Possible Causes: {[c.get('condition') for c in original_analysis.get('possible_causes', [])]}

FOLLOW-UP INFORMATION:
{qa_context}

Based on this additional information, provide a REFINED analysis with higher confidence.

Focus on:
1. Narrowing down the differential diagnosis
2. Increasing diagnostic certainty
3. Providing more specific recommendations
4. Identifying any new red flags or concerns

Respond in JSON format:
{{
    "refined_primary_assessment": "Updated assessment with higher certainty",
    "confidence": {max(original_confidence + 15, 85)}-95,
    "diagnostic_certainty": "provisional|probable|definitive",
    "differential_diagnoses": [
        {{"condition": "Most likely condition", "probability": 70-95, "supporting_evidence": ["evidence1", "evidence2"]}}
    ],
    "key_refinements": ["What the follow-up answers clarified", ...],
    "updated_recommendations": ["More specific recommendation 1", ...],
    "immediate_actions": ["Specific next steps based on refinement"],
    "red_flags": ["Any new concerns from follow-up answers"],
    "urgency": "low|medium|high|emergency",
    "next_steps": {{
        "immediate": "What to do right now",
        "short_term": "Next 24-48 hours",
        "follow_up": "When to reassess or see doctor"
    }},
    "severity_level": "low|moderate|high|urgent",
    "confidence_level": "medium|high",
    "what_this_means": "Clear explanation incorporating the new information (2-3 sentences)",
    "tracking_metrics": ["Specific metrics to track based on refined understanding"],
    "follow_up_timeline": {{
        "check_progress": "When to reassess",
        "see_doctor_if": "Specific conditions requiring medical care"
    }}
}}"""

        # Call LLM for refined analysis
        logger.info(f"Calling LLM for refinement of assessment {assessment_id}")
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": refinement_prompt}
            ],
            model="openai/gpt-5-mini",  # was: deepseek/deepseek-chat
            temperature=0.5  # Lower temperature for more consistent refinement
        )
        
        # Extract and parse response
        if isinstance(llm_response, dict):
            llm_content = llm_response.get('content', '')
        else:
            llm_content = str(llm_response)
        
        if '```json' in llm_content:
            llm_content = llm_content.replace('```json', '').replace('```', '').strip()
        
        refined_analysis = extract_json_from_text(llm_content)
        if not refined_analysis:
            logger.error("Failed to parse refined analysis")
            refined_analysis = {
                "refined_primary_assessment": "Unable to refine assessment",
                "confidence": original_confidence + 5,
                "diagnostic_certainty": "provisional",
                "key_refinements": ["Analysis refinement failed"],
                "updated_recommendations": original_analysis.get("recommendations", [])
            }
        
        # Calculate confidence improvement
        refined_confidence = float(refined_analysis.get("confidence", original_confidence + 10))
        confidence_improvement = refined_confidence - original_confidence
        
        logger.info(f"Refinement complete: confidence {original_confidence}% -> {refined_confidence}% (+{confidence_improvement}%)")
        
        # Store refinement in database
        try:
            refinement_result = supabase.table("general_assessment_refinements").insert({
                "assessment_id": assessment_id,
                "user_id": str(user_id) if user_id else None,
                "follow_up_questions": follow_up_questions,
                "answers": answers,
                "refined_analysis": refined_analysis,
                "refined_confidence": refined_confidence,
                "original_confidence": original_confidence,
                "severity_level": refined_analysis.get("severity_level", "moderate"),
                "confidence_level": refined_analysis.get("confidence_level", "medium"),
                "what_this_means": refined_analysis.get("what_this_means", ""),
                "immediate_actions": refined_analysis.get("immediate_actions", []),
                "red_flags": refined_analysis.get("red_flags", []),
                "tracking_metrics": refined_analysis.get("tracking_metrics", []),
                "follow_up_timeline": refined_analysis.get("follow_up_timeline", {}),
                "differential_diagnoses": refined_analysis.get("differential_diagnoses", []),
                "diagnostic_certainty": refined_analysis.get("diagnostic_certainty", "provisional"),
                "next_steps": refined_analysis.get("next_steps", {}),
                "model_used": "deepseek/deepseek-chat"
            }).execute()
            
            refinement_id = refinement_result.data[0]["id"] if refinement_result.data else str(uuid.uuid4())
        except Exception as e:
            logger.error(f"Database insert error for refinement: {str(e)}")
            refinement_id = str(uuid.uuid4())
        
        # Build response
        return {
            "refinement_id": refinement_id,
            "assessment_id": assessment_id,
            "refined_analysis": refined_analysis,
            "confidence_improvement": round(confidence_improvement, 1),
            "original_confidence": original_confidence,
            "refined_confidence": refined_confidence,
            "diagnostic_certainty": refined_analysis.get("diagnostic_certainty", "provisional"),
            "category": category,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Assessment refinement error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/general-deepdive/start")
async def start_general_deepdive(request: Request):
    """Start a multi-step diagnostic conversation"""
    try:
        data = await request.json()
        category = data.get("category")
        form_data = data.get("form_data", {})
        user_id = data.get("user_id")
        
        if not category:
            raise HTTPException(status_code=400, detail="category is required")
        
        # Initialize session
        session_id = str(uuid.uuid4())
        
        # Fetch user medical data
        user_medical_data = {}
        if user_id:
            user_medical_data = await get_user_medical_data(user_id)
        
        # Create initial context
        initial_complaint = form_data.get("symptoms", "unspecified symptoms")
        
        # Generate first diagnostic question
        first_question_prompt = f"""You are conducting a deep diagnostic interview for {category} health concerns.

Medical Context:
{format_medical_data(user_medical_data) if user_medical_data else "No medical history available"}

Initial Complaint:
{format_form_data(form_data, category)}

Generate the MOST IMPORTANT first diagnostic question to ask. This should be the question that will most help differentiate between possible conditions.

Focus on {category}-specific diagnostic criteria.

Respond in JSON format:
{{
    "question": "your diagnostic question",
    "question_type": "diagnostic|clarifying|severity|timeline",
    "why_asking": "brief explanation of why this question matters"
}}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": CATEGORY_PROMPTS[category]},
                {"role": "user", "content": first_question_prompt}
            ],
            model="openai/gpt-5-mini",  # was: deepseek/deepseek-chat
            temperature=0.5
        )
        
        # Extract content from response
        if isinstance(llm_response, dict):
            llm_content = llm_response.get('content', '')
        else:
            llm_content = str(llm_response)
        
        # Clean up markdown blocks if present
        if '```json' in llm_content:
            llm_content = llm_content.replace('```json', '').replace('```', '').strip()
        
        question_data = extract_json_from_text(llm_content)
        if not question_data:
            question_data = {
                "question": "Can you describe your symptoms in more detail?",
                "question_type": "diagnostic",
                "why_asking": "To better understand your condition"
            }
        
        # Save session
        session_result = supabase.table("general_deepdive_sessions").insert({
            "id": session_id,
            "user_id": user_id,
            "category": category,
            "initial_complaint": initial_complaint,
            "form_data": form_data,
            "questions": [question_data],
            "current_step": 1,
            "internal_state": {
                "user_medical_data": user_medical_data,
                "category": category
            },
            "status": "active",
            "model_used": "deepseek/deepseek-chat"
        }).execute()
        
        return {
            "session_id": session_id,
            "question": question_data.get("question", ""),
            "question_number": 1,
            "estimated_questions": "3-5",
            "question_type": question_data.get("question_type", "diagnostic"),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Start deep dive error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/general-deepdive/continue")
async def continue_general_deepdive(request: Request):
    """Continue the diagnostic conversation with next question"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        answer = data.get("answer")
        question_number = data.get("question_number", 1)
        
        if not session_id or not answer:
            raise HTTPException(status_code=400, detail="session_id and answer are required")
        
        # Fetch session
        session_result = supabase.table("general_deepdive_sessions").select("*").eq("id", session_id).single().execute()
        
        if not session_result.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_result.data
        
        # Store answer
        if "answers" not in session:
            session["answers"] = []
        session["answers"].append({
            "question_number": question_number,
            "answer": answer
        })
        
        # Check if we have enough information
        if question_number >= 5 or (question_number >= 3 and await has_sufficient_confidence(session)):
            # Update session status
            supabase.table("general_deepdive_sessions").update({
                "answers": session["answers"],
                "status": "analysis_ready",
                "current_step": question_number
            }).eq("id", session_id).execute()
            
            return {
                "ready_for_analysis": True,
                "questions_completed": question_number,
                "status": "success"
            }
        
        # Generate next question
        qa_history = format_qa_history(session.get("questions", []), session.get("answers", []))
        category = session.get("category", "general")
        
        next_question_prompt = f"""Based on this diagnostic conversation so far:

{qa_history}

Initial complaint: {session.get('initial_complaint', '')}

Generate the NEXT most important diagnostic question. Consider what information is still needed to make an accurate assessment.

Respond in JSON format:
{{
    "question": "your next diagnostic question",
    "question_type": "diagnostic|clarifying|severity|timeline",
    "why_asking": "brief explanation"
}}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": CATEGORY_PROMPTS[category]},
                {"role": "user", "content": next_question_prompt}
            ],
            model="openai/gpt-5-mini",  # was: deepseek/deepseek-chat
            temperature=0.5
        )
        
        # Extract content from response
        if isinstance(llm_response, dict):
            llm_content = llm_response.get('content', '')
        else:
            llm_content = str(llm_response)
        
        # Clean up markdown blocks if present
        if '```json' in llm_content:
            llm_content = llm_content.replace('```json', '').replace('```', '').strip()
        
        question_data = extract_json_from_text(llm_content)
        if not question_data:
            question_data = {
                "question": "Is there anything else you think might be relevant?",
                "question_type": "clarifying",
                "why_asking": "To ensure we haven't missed anything important"
            }
        
        # Update session
        questions = session.get("questions", [])
        questions.append(question_data)
        
        supabase.table("general_deepdive_sessions").update({
            "questions": questions,
            "answers": session["answers"],
            "current_step": question_number + 1
        }).eq("id", session_id).execute()
        
        return {
            "question": question_data.get("question", ""),
            "question_number": question_number + 1,
            "is_final_question": question_number >= 4,
            "question_type": question_data.get("question_type", "diagnostic"),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Continue deep dive error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/general-deepdive/complete")
async def complete_general_deepdive(request: Request):
    """Generate final comprehensive analysis"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        final_answer = data.get("final_answer")
        
        logger.info(f"Deep dive complete called for session: {session_id}")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        
        # Fetch complete session
        logger.info(f"Fetching session data for: {session_id}")
        session_result = supabase.table("general_deepdive_sessions").select("*").eq("id", session_id).single().execute()
        
        if not session_result.data:
            logger.error(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_result.data
        
        # Add final answer if provided
        if final_answer:
            if "answers" not in session:
                session["answers"] = []
            session["answers"].append({
                "question_number": len(session.get("questions", [])),
                "answer": final_answer
            })
        
        # Generate comprehensive analysis
        category = session.get("category", "general")
        qa_history = format_qa_history(session.get("questions", []), session.get("answers", []))
        medical_data = session.get("internal_state", {}).get("user_medical_data", {})
        
        final_analysis_prompt = f"""Based on this deep dive diagnostic session for {category} concerns:

Initial Presentation:
{format_form_data(session.get('form_data', {}), category)}

Diagnostic Conversation:
{qa_history}

Medical Context:
{format_medical_data(medical_data) if medical_data else "No medical history available"}

Provide a comprehensive final analysis in JSON format:
{{
    "analysis": {{
        "primary_diagnosis": "most likely condition with confidence %",
        "differential_diagnoses": [
            {{"condition": "name", "probability": 0-100, "reasoning": "why"}}
        ],
        "key_findings": ["important finding 1", "finding 2", ...],
        "recommendations": ["specific recommendation 1", ...],
        "red_flags": ["warning sign to watch for", ...],
        "follow_up": "suggested follow-up plan",
        "urgency": "low|medium|high|emergency"
    }},
    "confidence": 0-100,
    "reasoning_snippets": ["key reasoning point 1", "point 2", ...],
    "severity_level": "low|moderate|high|urgent",
    "confidence_level": "low|medium|high",
    "what_this_means": "Comprehensive plain English explanation based on full diagnostic conversation (2-3 sentences)",
    "immediate_actions": ["3-5 personalized action steps based on deep dive findings"],
    "red_flags": ["Specific warning signs based on diagnosis"],
    "tracking_metrics": ["Personalized metrics to monitor"],
    "follow_up_timeline": {{
        "check_progress": "When to reassess",
        "see_doctor_if": "Specific conditions for medical care"
    }}
}}"""

        logger.info(f"Calling LLM for final analysis of category: {category}")
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": CATEGORY_PROMPTS[category]},
                {"role": "user", "content": final_analysis_prompt}
            ],
            model="openai/gpt-5-mini",  # was: deepseek/deepseek-chat
            temperature=0.4
        )
        
        logger.info(f"Deep dive complete LLM Response: {str(llm_response)[:500]}...")
        
        # Extract content from response
        if isinstance(llm_response, dict):
            llm_content = llm_response.get('content', '')
        else:
            llm_content = str(llm_response)
        
        # Clean up markdown blocks if present
        if '```json' in llm_content:
            llm_content = llm_content.replace('```json', '').replace('```', '').strip()
        
        logger.info(f"Cleaned LLM content: {llm_content[:500]}...")
        
        analysis_data = extract_json_from_text(llm_content)
        logger.info(f"Parsed analysis data: {analysis_data}")
        if not analysis_data:
            analysis_data = {
                "analysis": {
                    "primary_diagnosis": "Unable to determine",
                    "differential_diagnoses": [],
                    "key_findings": ["Incomplete analysis"],
                    "recommendations": ["Please consult with a healthcare provider"],
                    "red_flags": [],
                    "follow_up": "Medical evaluation recommended",
                    "urgency": "medium"
                },
                "confidence": 50,
                "reasoning_snippets": []
            }
        
        # Add new required fields using formatter
        analysis_data = add_general_assessment_fields(
            analysis_data,
            llm_generated=analysis_data
        )
        
        logger.info(f"Enhanced deep dive with new fields: severity={analysis_data.get('severity_level')}, confidence_level={analysis_data.get('confidence_level')}")
        
        # Calculate session duration
        try:
            created_at_str = session.get("created_at", datetime.now().isoformat())
            # Handle timezone-aware datetime strings
            if created_at_str.endswith('Z'):
                created_at_str = created_at_str[:-1] + '+00:00'
            elif '+' not in created_at_str and not created_at_str.endswith('Z'):
                created_at_str += '+00:00'
            created_at = datetime.fromisoformat(created_at_str)
            # Make current time timezone-aware
            now = datetime.now(timezone.utc)
            session_duration_ms = int((now - created_at).total_seconds() * 1000)
        except Exception as e:
            logger.error(f"Error calculating session duration: {str(e)}")
            session_duration_ms = 0
        
        # Update session with final analysis
        try:
            logger.info(f"Updating deep dive session {session_id} with final analysis")
            update_result = supabase.table("general_deepdive_sessions").update({
                "final_analysis": analysis_data.get("analysis", {}),
                "final_confidence": float(analysis_data.get("confidence", 50)),
                "key_findings": analysis_data.get("analysis", {}).get("key_findings", []),
                "reasoning_snippets": analysis_data.get("reasoning_snippets", []),
                "status": "completed",
                "session_duration_ms": session_duration_ms,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", session_id).execute()
            logger.info(f"Deep dive session updated successfully")
        except Exception as e:
            logger.error(f"Database update error in deep dive complete: {str(e)}")
            # Continue anyway - we have the analysis
        
        # Build response with new fields
        response = {
            "deep_dive_id": session_id,
            "analysis": analysis_data.get("analysis", {}),
            "category": category,
            "confidence": analysis_data.get("confidence", 50),
            # Add new fields
            "severity_level": analysis_data.get("severity_level", "moderate"),
            "confidence_level": analysis_data.get("confidence_level", "medium"),
            "what_this_means": analysis_data.get("what_this_means", "Based on our conversation, further evaluation is recommended."),
            "immediate_actions": analysis_data.get("immediate_actions", []),
            "red_flags": analysis_data.get("red_flags", []),
            "tracking_metrics": analysis_data.get("tracking_metrics", []),
            "follow_up_timeline": analysis_data.get("follow_up_timeline", {}),
        }
        
        # Store the enhanced fields in the database
        try:
            store_enhanced_fields_for_general_deepdive(session_id, response)
        except Exception as storage_error:
            logger.warning(f"Failed to store enhanced fields for deep dive: {storage_error}")
        
        # Continue building response
        response.update({
            "questions_asked": len(session.get("questions", [])),
            "session_duration_ms": session_duration_ms,
            "reasoning_snippets": analysis_data.get("reasoning_snippets", []),
            "status": "success"
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Complete deep dive error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
def format_medical_data(medical_data: dict) -> str:
    """Format medical data for LLM context"""
    if not medical_data:
        return "No medical history available"
    
    height = medical_data.get('height', 0)
    weight = medical_data.get('weight', 0)
    bmi = calculate_bmi(height, weight) if height and weight else "Unknown"
    
    # Handle medications which is an array in the DB
    medications = medical_data.get('medications', [])
    if medications and isinstance(medications, list):
        medications_str = ', '.join(medications)
    else:
        medications_str = 'None'
    
    # Handle allergies and family_history which are JSONB
    allergies = medical_data.get('allergies', [])
    if allergies and isinstance(allergies, list):
        # Handle case where items might be dicts or strings
        allergies_list = []
        for item in allergies:
            if isinstance(item, dict):
                # Extract relevant field from dict (e.g., 'name' or 'allergy')
                allergies_list.append(str(item.get('name', item.get('allergy', str(item)))))
            else:
                allergies_list.append(str(item))
        allergies_str = ', '.join(allergies_list) if allergies_list else 'None'
    else:
        allergies_str = 'None'
        
    family_history = medical_data.get('family_history', [])
    if family_history and isinstance(family_history, list):
        # Handle case where items might be dicts or strings
        history_list = []
        for item in family_history:
            if isinstance(item, dict):
                # Extract relevant field from dict
                history_list.append(str(item.get('condition', item.get('name', str(item)))))
            else:
                history_list.append(str(item))
        family_history_str = ', '.join(history_list) if history_list else 'None'
    else:
        family_history_str = 'None'
    
    return f"""
Age: {medical_data.get('age', 'Unknown')}
Gender: {'Male' if medical_data.get('is_male') else 'Female' if medical_data.get('is_male') is False else 'Unknown'}
BMI: {bmi}
Health Context: {medical_data.get('personal_health_context', 'None provided')}
Current Medications: {medications_str}
Allergies: {allergies_str}
Family History: {family_history_str}
"""

def calculate_bmi(height_cm: float, weight_kg: float) -> str:
    """Calculate BMI from height and weight"""
    if not height_cm or not weight_kg:
        return "Unknown"
    try:
        # Convert to float if they're strings
        height_cm = float(height_cm)
        weight_kg = float(weight_kg)
        height_m = height_cm / 100
        bmi = weight_kg / (height_m ** 2)
        return f"{bmi:.1f}"
    except (ValueError, TypeError):
        return "Unknown"

def format_form_data(form_data: dict, category: str) -> str:
    """Format form data based on category"""
    base_info = f"""
Primary Symptoms: {form_data.get('symptoms', 'Not specified')}
Duration: {form_data.get('duration', 'Not specified')}
Impact Level: {form_data.get('impactLevel', 'Not specified')}/10
Aggravating Factors: {', '.join(form_data.get('aggravatingFactors', [])) or 'None specified'}
Tried Interventions: {', '.join(form_data.get('triedInterventions', [])) or 'None'}
"""
    
    # Add category-specific fields
    if category == 'energy':
        base_info += f"""
Energy Pattern: {form_data.get('energyPattern', 'Not specified')}
Sleep Hours: {form_data.get('sleepHours', 'Not specified')}
Wake Feeling: {form_data.get('wakingUpFeeling', 'Not specified')}
"""
    elif category == 'mental':
        base_info += f"""
Mood Pattern: {form_data.get('moodPattern', 'Not specified')}
Triggers: {form_data.get('triggerEvents', 'Not specified')}
Concentration: {form_data.get('concentrationLevel', 'Not specified')}/10
"""
    elif category == 'sick':
        base_info += f"""
Temperature: {form_data.get('temperatureFeeling', 'Not specified')}
Progression: {form_data.get('symptomProgression', 'Not specified')}
Contagious Exposure: {'Yes' if form_data.get('contagiousExposure') else 'No'}
"""
    elif category == 'medication':
        base_info += f"""
Symptom Timing: {form_data.get('symptomTiming', 'Not specified')}
Dose Changes: {'Yes' if form_data.get('doseChanges') else 'No'}
Time Since Started: {form_data.get('timeSinceStarted', 'Not specified')}
"""
    elif category == 'multiple':
        base_info += f"""
Primary Concern: {form_data.get('primaryConcern', 'Not specified')}
Symptom Connection: {form_data.get('symptomConnection', 'Not specified')}
Secondary Concerns: {', '.join(form_data.get('secondaryConcerns', [])) or 'None'}
"""
    elif category == 'unsure':
        base_info += f"""
Current Activity: {form_data.get('currentActivity', 'Not specified')}
Recent Changes: {form_data.get('recentChanges', 'Not specified')}
"""
    elif category == 'physical':
        base_info += f"""
Body Region: {form_data.get('bodyRegion', 'Not specified')}
Issue Type: {form_data.get('issueType', 'Not specified')}
Occurrence Pattern: {form_data.get('occurrencePattern', 'Not specified')}
Affected Side: {form_data.get('affectedSide', 'Not specified')}
Radiating Pain: {'Yes' if form_data.get('radiatingPain') else 'No'}
Specific Movements: {form_data.get('specificMovements', 'None')}
"""
    
    # Add optional body location if present
    if form_data.get('bodyLocation'):
        base_info += f"""
Location: {', '.join(form_data['bodyLocation'].get('regions', [])) or 'Not specified'}
Location Description: {form_data['bodyLocation'].get('description', 'None')}
"""
    
    return base_info

def build_category_prompt(category: str, medical_data: dict) -> str:
    """Build category-specific prompt with medical context"""
    
    # Try to load from file first
    prompts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'prompts', 'general_assessment')
    prompt_file = os.path.join(prompts_dir, f"{category}.txt")
    
    base_prompt = None
    try:
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r') as f:
                base_prompt = f.read()
                logger.info(f"Loaded {category} prompt from file")
    except Exception as e:
        logger.warning(f"Could not load prompt from file for {category}: {e}")
    
    # Fall back to inline prompt if file not found
    if not base_prompt:
        base_prompt = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["unsure"])
        logger.info(f"Using inline prompt for {category}")
    
    # Replace placeholders with actual medical data
    medications = medical_data.get('medications', [])
    if medications and isinstance(medications, list):
        medications_str = ', '.join(medications) or 'None'
    else:
        medications_str = 'None'
    
    # Use personal_health_context as conditions since there's no chronic_conditions field
    conditions = medical_data.get('personal_health_context', 'None')
    
    prompt = base_prompt.format(
        medications=medications_str,
        conditions=conditions
    )
    
    return prompt

def format_qa_history(questions: List[dict], answers: List[dict]) -> str:
    """Format Q&A history for context"""
    qa_pairs = []
    for i, q in enumerate(questions):
        question_text = q.get("question", "Unknown question")
        answer_text = "No answer provided"
        
        # Find matching answer
        for a in answers:
            if a.get("question_number", -1) == i + 1:
                answer_text = a.get("answer", "No answer")
                break
        
        qa_pairs.append(f"Q{i+1}: {question_text}\nA{i+1}: {answer_text}")
    
    return "\n\n".join(qa_pairs)

async def has_sufficient_confidence(session: dict) -> bool:
    """Determine if we have enough information to make assessment"""
    # Simple heuristic - can be enhanced
    answers = session.get("answers", [])
    if len(answers) >= 3:
        # Check if answers are substantive
        total_length = sum(len(a.get("answer", "")) for a in answers)
        return total_length > 100  # At least some detail provided
    return False