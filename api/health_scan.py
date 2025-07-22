"""Health Scan API endpoints - Quick Scan and Deep Dive"""
from fastapi import APIRouter
from datetime import datetime, timezone
import uuid
import json

from models.requests import (
    QuickScanRequest, 
    DeepDiveStartRequest, 
    DeepDiveContinueRequest, 
    DeepDiveCompleteRequest,
    DeepDiveThinkHarderRequest,
    DeepDiveAskMoreRequest,
    QuickScanThinkHarderRequest,
    QuickScanO4MiniRequest,
    QuickScanUltraThinkRequest,
    QuickScanAskMoreRequest
)
from supabase_client import supabase
from business_logic import call_llm, make_prompt, get_llm_context as get_llm_context_biz, get_user_data
from utils.json_parser import extract_json_from_response
from utils.data_gathering import get_user_medical_data

router = APIRouter(prefix="/api", tags=["health-scan"])

# Deep Dive Configuration
DEEP_DIVE_CONFIG = {
    "max_questions": 7,  # Limit to 7 questions max
    "target_confidence": 80,  # Target 80% confidence
    "min_confidence_for_completion": 80,  # Can complete at 80% if max questions reached
    "min_questions": 2,  # Minimum questions before completion
}

def is_duplicate_question(new_question: str, previous_questions: list) -> bool:
    """Prevent asking the same question twice"""
    import difflib
    
    if not previous_questions:
        return False
    
    # Normalize the new question
    new_q_normalized = new_question.lower().strip()
    
    for prev_q in previous_questions:
        # Check similarity (80% threshold)
        similarity = difflib.SequenceMatcher(
            None, 
            new_q_normalized, 
            prev_q.lower().strip()
        ).ratio()
        
        if similarity > 0.8:  # 80% similar = duplicate
            print(f"Duplicate question detected: {similarity:.2%} similar to previous question")
            return True
    
    return False

def should_complete_deep_dive(session_data: dict) -> bool:
    """Decide if deep dive should complete based on smart logic"""
    question_count = session_data.get('question_count', 0)
    confidence = session_data.get('final_confidence', 0)
    
    # Complete if any of these conditions:
    return (
        confidence >= DEEP_DIVE_CONFIG["target_confidence"] or  # Target confidence reached
        question_count >= DEEP_DIVE_CONFIG["max_questions"] or  # Max questions reached
        (question_count >= 5 and confidence >= DEEP_DIVE_CONFIG["min_confidence_for_completion"])  # Good enough fallback
    )

@router.post("/quick-scan")
async def quick_scan_endpoint(request: QuickScanRequest):
    """Quick Scan endpoint for rapid health assessment"""
    try:
        # Get user data if user_id provided (otherwise anonymous)
        user_data = {}
        medical_data = {}
        llm_context = ""
        
        if request.user_id:
            user_data = await get_user_data(request.user_id)
            medical_data = await get_user_medical_data(request.user_id)
            llm_context = await get_llm_context_biz(request.user_id)
        
        # Prepare data for prompt
        prompt_data = {
            "body_part": request.body_part,
            "form_data": request.form_data,
            "medical_data": medical_data if medical_data and "error" not in medical_data else None
        }
        
        # Generate the quick scan prompt
        query = request.form_data.get("symptoms", "Health scan requested")
        system_prompt = make_prompt(
            query=query,
            user_data=prompt_data,
            llm_context=llm_context,
            category="quick-scan",
            part_selected=request.body_part
        )
        
        # Call LLM with lower temperature for consistent JSON
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze my symptoms for {request.body_part}: {json.dumps(request.form_data)}"}
            ],
            model=request.model,
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=1024
        )
        
        # Parse the response as JSON
        try:
            if isinstance(llm_response["content"], dict):
                analysis_result = llm_response["content"]
            else:
                # Try to extract JSON from string response
                content = llm_response["raw_content"]
                # Find JSON in the response
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    analysis_result = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
        except Exception as json_error:
            # If JSON parsing fails, return error and ask for retry
            return {
                "error": "Failed to parse AI response",
                "message": "Please try again",
                "raw_response": llm_response.get("raw_content", ""),
                "parse_error": str(json_error),
                "status": "error"
            }
        
        # Generate unique scan ID
        scan_id = str(uuid.uuid4())
        
        # Save to database if user is authenticated
        if request.user_id:
            try:
                # Save to quick_scans table
                scan_data = {
                    "id": scan_id,
                    "user_id": request.user_id,
                    "body_part": request.body_part,
                    "form_data": request.form_data,
                    "analysis_result": analysis_result,
                    "urgency_level": analysis_result.get("urgency", "low"),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                print(f"\n=== SAVING QUICK SCAN ===")
                print(f"Scan ID: {scan_id}")
                print(f"User ID: '{request.user_id}' (type: {type(request.user_id)})")
                print(f"User ID repr: {repr(request.user_id)}")
                print(f"Body part: {request.body_part}")
                
                supabase.table("quick_scans").insert(scan_data).execute()
                print("Quick scan saved successfully!")
                print("=== END SAVE ===\n")
                
                # Save symptoms to tracking table
                if "symptoms" in request.form_data:
                    severity = request.form_data.get("painLevel", 5)
                    tracking_data = {
                        "user_id": request.user_id,
                        "quick_scan_id": scan_id,
                        "symptom_name": request.form_data["symptoms"],
                        "body_part": request.body_part,
                        "severity": severity
                    }
                    supabase.table("symptom_tracking").insert(tracking_data).execute()
                    
            except Exception as db_error:
                print(f"Database error (non-critical): {db_error}")
                # Continue even if DB save fails
        
        return {
            "scan_id": scan_id,
            "analysis": analysis_result,
            "body_part": request.body_part,
            "confidence": analysis_result.get("confidence", 0),
            "user_id": request.user_id,
            "usage": llm_response.get("usage", {}),
            "model": llm_response.get("model", ""),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error in quick scan: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/deep-dive/start")
async def start_deep_dive(request: DeepDiveStartRequest):
    """Start a Deep Dive analysis session"""
    try:
        # Get user data if provided
        user_data = {}
        medical_data = {}
        llm_context = ""
        
        if request.user_id:
            user_data = await get_user_data(request.user_id)
            medical_data = await get_user_medical_data(request.user_id)
            llm_context = await get_llm_context_biz(request.user_id)
        
        # Prepare data for prompt
        prompt_data = {
            "body_part": request.body_part,
            "form_data": request.form_data,
            "medical_data": medical_data if medical_data and "error" not in medical_data else None
        }
        
        # Use DeepSeek R1 for asking questions (better at generating diagnostic questions)
        model = request.model or "tngtech/deepseek-r1t-chimera:free"
        
        # Add model validation and fallback
        WORKING_MODELS = [
            "tngtech/deepseek-r1t-chimera:free",  # Primary model for deep dive questions
            "google/gemini-2.5-pro",  # Fallback option
            "deepseek/deepseek-chat",
            "meta-llama/llama-3.2-3b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "microsoft/phi-3-mini-128k-instruct:free"
        ]
        
        # If specified model not in list, use DeepSeek R1
        if model not in WORKING_MODELS:
            print(f"Model {model} not in working list, using DeepSeek R1")
            model = "tngtech/deepseek-r1t-chimera:free"
        
        # Generate initial question
        query = request.form_data.get("symptoms", "Health analysis requested")
        system_prompt = make_prompt(
            query=query,
            user_data=prompt_data,
            llm_context=llm_context,
            category="deep-dive-initial",
            part_selected=request.body_part
        )
        
        # Call LLM
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze symptoms and generate first diagnostic question"}
            ],
            model=model,
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=1024
        )
        
        # Parse response with robust fallback
        try:
            # First try our robust parser
            question_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            # Validate the question data
            if not question_data or not isinstance(question_data.get("question"), str) or len(question_data.get("question", "")) < 10:
                # Invalid or missing question
                print(f"Invalid question data received: {question_data}")
                question_data = {
                    "question": f"Can you describe the {request.body_part} pain in more detail? Is it sharp, dull, burning, or aching?",
                    "question_type": "symptom_characterization",
                    "internal_analysis": {"fallback": True, "original": question_data}
                }
            
            # Additional validation - ensure question doesn't contain formatting instructions
            question_text = question_data.get("question", "")
            if any(word in question_text.lower() for word in ["json", "format", "response", "ensure", "```"]):
                print(f"Question contains formatting instructions: {question_text}")
                question_data = {
                    "question": f"Can you describe the {request.body_part} symptoms in more detail? When did they start and what makes them better or worse?",
                    "question_type": "symptom_characterization",
                    "internal_analysis": {"fallback": True, "formatting_detected": True}
                }
                
        except Exception as e:
            print(f"Parse error in deep dive start: {e}")
            # Use fallback question
            question_data = {
                "question": f"Can you describe the {request.body_part} pain in more detail? Is it sharp, dull, burning, or aching?",
                "question_type": "symptom_characterization",
                "internal_analysis": {"error": str(e)}
            }
        
        # Create session
        session_id = str(uuid.uuid4())
        
        # Save session to database
        session_data = {
            "id": session_id,
            "user_id": request.user_id,
            "body_part": request.body_part,
            "form_data": request.form_data,
            "model_used": model,
            "questions": [],  # PostgreSQL array, not dict
            "current_step": 1,
            "internal_state": question_data.get("internal_analysis", {}),
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_question": question_data.get("question", "")
        }
        
        # Always save session to database (for both authenticated and anonymous users)
        try:
            insert_response = supabase.table("deep_dive_sessions").insert(session_data).execute()
            print(f"Deep dive session saved: {session_id}")
            print(f"Insert response: {insert_response.data if insert_response.data else 'No data returned'}")
        except Exception as db_error:
            print(f"ERROR saving deep dive session: {db_error}")
            print(f"Session data attempted: {session_data}")
            # Return error instead of continuing
            return {
                "error": f"Failed to save session: {str(db_error)}",
                "status": "error"
            }
        
        return {
            "session_id": session_id,
            "question": question_data.get("question", ""),
            "question_number": 1,
            "estimated_questions": "2-3",
            "question_type": question_data.get("question_type", "differential"),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error in deep dive start: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/deep-dive/continue")
async def continue_deep_dive(request: DeepDiveContinueRequest):
    """Continue Deep Dive with answer processing"""
    try:
        print(f"\n=== DEEP DIVE CONTINUE ===")
        print(f"Looking for session: {request.session_id}")
        
        # Get session from database
        session_response = supabase.table("deep_dive_sessions").select("*").eq("id", request.session_id).execute()
        print(f"Session query response: {len(session_response.data) if session_response.data else 0} records found")
        
        if not session_response.data:
            print(f"ERROR: No session found with ID {request.session_id}")
            # Try to list recent sessions for debugging
            recent = supabase.table("deep_dive_sessions").select("id, created_at").order("created_at", desc=True).limit(5).execute()
            print(f"Recent sessions: {recent.data if recent.data else 'None'}")
            return {"error": "Session not found", "status": "error"}
        
        session = session_response.data[0]
        
        if session["status"] != "active":
            return {"error": "Session already completed", "status": "error"}
        
        # Add Q&A to history
        qa_entry = {
            "question_number": request.question_number,
            "question": session.get("last_question", ""),
            "answer": request.answer,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        questions = session.get("questions", [])
        questions.append(qa_entry)
        
        # Track questions through the questions array
        previous_questions = [q.get("question", "") for q in questions if q.get("question")]
        if session.get("last_question") and session.get("last_question") not in previous_questions:
            previous_questions.append(session.get("last_question"))
        
        # Prepare session data for prompt
        session_data = {
            "questions": questions,
            "internal_state": session.get("internal_state", {}),
            "form_data": session.get("form_data", {})
        }
        
        # Fetch medical data if user_id exists
        medical_data = {}
        if session.get("user_id"):
            medical_data = await get_user_medical_data(session["user_id"])
        
        # Get user context
        llm_context = ""
        if session.get("user_id"):
            llm_context = await get_llm_context_biz(session["user_id"])
        
        # Generate continue prompt with medical data
        prompt_data = {
            "session_data": session_data,
            "medical_data": medical_data if medical_data and "error" not in medical_data else None
        }
        
        system_prompt = make_prompt(
            query=request.answer,
            user_data=prompt_data,
            llm_context=llm_context,
            category="deep-dive-continue"
        )
        
        # Call LLM
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Process answer and decide next step"}
            ],
            model=session.get("model_used", "google/gemini-2.5-pro"),  # Default to Gemini 2.5 Pro
            user_id=session.get("user_id"),
            temperature=0.3,
            max_tokens=1024
        )
        
        # Parse response with fallback
        try:
            decision_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            # Validate decision data
            if not decision_data:
                # Create fallback decision
                decision_data = {
                    "need_another_question": request.question_number < 2,
                    "current_confidence": 50 + (request.question_number * 15),  # Incremental confidence
                    "question": "Have you experienced any other symptoms along with this?",
                    "confidence_projection": "Gathering more information",
                    "updated_analysis": session.get("internal_state", {})
                }
            
            # If there's a question, validate it
            if decision_data.get("question"):
                question_text = str(decision_data.get("question", ""))
                # Check for formatting instructions
                if any(word in question_text.lower() for word in ["json", "format", "response", "ensure", "```"]) or len(question_text) < 10:
                    print(f"Invalid question detected in continue: {question_text}")
                    # Generate contextual fallback question based on question number
                    fallback_questions = [
                        "Have you noticed if the symptoms change throughout the day or with certain activities?",
                        "Are there any other symptoms you've experienced, even if they seem unrelated?",
                        "Have you tried any treatments or medications, and did they help?",
                        "Is there a family history of similar conditions?",
                        "How is this affecting your daily activities and quality of life?"
                    ]
                    decision_data["question"] = fallback_questions[min(request.question_number - 1, len(fallback_questions) - 1)]
                    
        except Exception as e:
            print(f"Parse error in deep dive continue: {e}")
            decision_data = {
                "ready_for_analysis": True,
                "questions_completed": request.question_number
            }
        
        # Update session
        update_data = {
            "questions": questions,
            "current_step": request.question_number + 1,
            "internal_state": decision_data.get("updated_analysis", session.get("internal_state", {}))
        }
        
        # Update session in database
        try:
            supabase.table("deep_dive_sessions").update(update_data).eq("id", request.session_id).execute()
        except Exception as e:
            print(f"Error updating session: {e}")
        
        # Get current confidence level
        current_confidence = decision_data.get("current_confidence", 0)
        question_count = len(previous_questions)
        
        print(f"Deep Dive Progress: Question {question_count}, Confidence: {current_confidence}%, Target: {DEEP_DIVE_CONFIG['target_confidence']}%")
        
        # Update session with current confidence and question count
        session_data_for_completion = {
            "final_confidence": current_confidence,
            "question_count": question_count
        }
        
        # Check if we should complete using smart logic
        should_complete = should_complete_deep_dive(session_data_for_completion)
        
        # Check if LLM also thinks we need another question
        llm_wants_more = decision_data.get("need_another_question", False)
        
        # Force completion if we've reached max questions
        if question_count >= DEEP_DIVE_CONFIG["max_questions"]:
            should_complete = True
            print(f"Max questions ({DEEP_DIVE_CONFIG['max_questions']}) reached - forcing completion")
        
        # Need at least minimum questions
        if question_count < DEEP_DIVE_CONFIG["min_questions"]:
            should_complete = False
        
        # Continue asking questions if we haven't hit completion criteria AND either:
        # - LLM wants more questions, OR
        # - We're below target confidence
        # This allows completion at 80% but doesn't require it
        if not should_complete and llm_wants_more:
            new_question = decision_data.get("question", "")
            
            # Check for duplicate question
            if is_duplicate_question(new_question, previous_questions):
                print(f"Duplicate question detected - forcing completion")
                # If we've asked enough questions and got a duplicate, complete
                if question_count >= 3:
                    return {
                        "ready_for_analysis": True,
                        "questions_completed": question_count,
                        "status": "success",
                        "reason": "duplicate_question_detected"
                    }
                else:
                    # Try to generate alternative question
                    new_question = f"Besides what we've discussed, are there any other symptoms or concerns about your {session.get('body_part', 'condition')}?"
            
            
            # Store the question for next iteration
            try:
                supabase.table("deep_dive_sessions").update({
                    "last_question": new_question,
                    "final_confidence": current_confidence
                }).eq("id", request.session_id).execute()
            except Exception as e:
                print(f"Error storing last question: {e}")
            
            # Check if we're approaching max questions
            is_final_question = len(previous_questions) >= (DEEP_DIVE_CONFIG["max_questions"] - 1)
            
            return {
                "question": new_question,
                "question_number": len(previous_questions),
                "is_final_question": is_final_question,
                "confidence_projection": decision_data.get("confidence_projection", ""),
                "current_confidence": current_confidence,
                "confidence_threshold": DEEP_DIVE_CONFIG["target_confidence"],
                "questions_remaining": max(0, DEEP_DIVE_CONFIG["max_questions"] - len(previous_questions)),
                "status": "success"
            }
        else:
            # Ready for final analysis
            return {
                "ready_for_analysis": True,
                "questions_completed": request.question_number,
                "status": "success"
            }
            
    except Exception as e:
        print(f"Error in deep dive continue: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/deep-dive/complete")
async def complete_deep_dive(request: DeepDiveCompleteRequest):
    """Generate final Deep Dive analysis"""
    try:
        # Get session
        session_response = supabase.table("deep_dive_sessions").select("*").eq("id", request.session_id).execute()
        
        if not session_response.data:
            return {"error": "Session not found", "status": "error"}
        
        session = session_response.data[0]
        
        # Add final answer if provided
        if request.final_answer:
            qa_entry = {
                "question_number": len(session.get("questions", [])) + 1,
                "question": session.get("last_question", ""),
                "answer": request.final_answer,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            questions = session.get("questions", [])
            questions.append(qa_entry)
        else:
            questions = session.get("questions", [])
        
        # Get user context
        llm_context = ""
        if session.get("user_id"):
            llm_context = await get_llm_context_biz(session["user_id"])
        
        # Fetch medical data if user_id exists
        medical_data = {}
        if session.get("user_id"):
            medical_data = await get_user_medical_data(session["user_id"])
        
        # Generate final analysis
        session_data = {
            "questions": questions,
            "form_data": session.get("form_data", {}),
            "internal_state": session.get("internal_state", {}),
            "medical_data": medical_data if medical_data and "error" not in medical_data else None
        }
        
        system_prompt = make_prompt(
            query="Generate final analysis",
            user_data={"session_data": session_data},
            llm_context=llm_context,
            category="deep-dive-final"
        )
        
        # Call LLM for final analysis
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate comprehensive final analysis based on all Q&A"}
            ],
            model="google/gemini-2.5-pro",  # Always use Gemini 2.5 Pro for final analysis
            user_id=session.get("user_id"),
            temperature=0.3,
            max_tokens=2048
        )
        
        # Parse final analysis with comprehensive fallback
        try:
            # DEBUG: Log the raw response
            raw_response = llm_response.get("content", llm_response.get("raw_content", ""))
            print(f"[DEBUG] Deep Dive Complete - Raw LLM Response Type: {type(raw_response)}")
            print(f"[DEBUG] Deep Dive Complete - Raw LLM Response: {str(raw_response)[:500]}...")
            
            analysis_result = extract_json_from_response(raw_response)
            
            # DEBUG: Log parsing result
            print(f"[DEBUG] Deep Dive Complete - Parsed Result: {analysis_result is not None}")
            if analysis_result:
                print(f"[DEBUG] Deep Dive Complete - Parsed Keys: {list(analysis_result.keys()) if isinstance(analysis_result, dict) else 'Not a dict'}")
            
            if not analysis_result:
                # Create structured fallback analysis
                print("[DEBUG] Deep Dive Complete - Using fallback analysis due to parsing failure")
                analysis_result = {
                    "confidence": 70,
                    "primaryCondition": f"Analysis of {session.get('body_part', 'symptom')} pain",
                    "likelihood": "Likely",
                    "symptoms": [s for q in questions for s in [q.get("answer", "")] if s],
                    "recommendations": [
                        "Monitor symptoms closely",
                        "Seek medical evaluation if symptoms worsen",
                        "Keep a symptom diary"
                    ],
                    "urgency": "medium",
                    "differentials": [],
                    "redFlags": ["Seek immediate care if symptoms suddenly worsen"],
                    "selfCare": ["Rest and avoid activities that worsen symptoms"],
                    "timeline": "Monitor for 2-3 days",
                    "followUp": "If symptoms persist or worsen after 3 days",
                    "relatedSymptoms": ["Watch for fever, spreading symptoms, or increased pain"],
                    "reasoning_snippets": ["Based on reported symptoms"]
                }
        except Exception as e:
            print(f"Parse error in deep dive complete: {e}")
            # Use fallback analysis
            analysis_result = {
                "confidence": 60,
                "primaryCondition": "Requires further medical evaluation",
                "likelihood": "Possible",
                "symptoms": ["As reported"],
                "recommendations": ["Consult with a healthcare provider"],
                "urgency": "medium",
                "differentials": [],
                "redFlags": [],
                "selfCare": [],
                "timeline": "Seek evaluation within 24-48 hours",
                "followUp": "Schedule appointment with healthcare provider",
                "relatedSymptoms": ["Monitor all symptoms"],
                "reasoning_snippets": ["Unable to complete full analysis"]
            }
        
        # Update session with results
        update_data = {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "final_analysis": analysis_result,
            "final_confidence": analysis_result.get("confidence", 0),
            "reasoning_chain": analysis_result.get("reasoning_snippets", []),
            "questions": questions,
            "tokens_used": llm_response.get("usage", {})
        }
        
        # Update session in database
        try:
            supabase.table("deep_dive_sessions").update(update_data).eq("id", request.session_id).execute()
        except Exception as e:
            print(f"Error updating session: {e}")
            
            # Auto-generate summary (fire and forget)
            try:
                # Create summary for llm_context table
                summary_text = f"""Deep Dive Analysis - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
Body Part: {session.get('body_part')}
Primary Condition: {analysis_result.get('primaryCondition')}
Confidence: {analysis_result.get('confidence')}%
Questions Asked: {len(questions)}
Key Findings: {', '.join(analysis_result.get('reasoning_snippets', [])[:3])}"""
                
                summary_data = {
                    "user_id": session["user_id"],
                    "conversation_id": None,  # Deep dives don't have conversation_id
                    "llm_summary": summary_text,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                supabase.table("llm_context").insert(summary_data).execute()
            except Exception as summary_error:
                print(f"Summary generation error (non-critical): {summary_error}")
        
        return {
            "deep_dive_id": request.session_id,
            "analysis": analysis_result,
            "body_part": session.get("body_part"),
            "confidence": analysis_result.get("confidence", 0),
            "questions_asked": len(questions),
            "reasoning_snippets": analysis_result.get("reasoning_snippets", []),
            "usage": llm_response.get("usage", {}),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error in deep dive complete: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/deep-dive/think-harder")
async def deep_dive_think_harder(request: DeepDiveThinkHarderRequest):
    """Re-analyze completed deep dive session with premium model for enhanced insights"""
    try:
        # Get session from database
        session_response = supabase.table("deep_dive_sessions").select("*").eq("id", request.session_id).execute()
        
        if not session_response.data:
            return {"error": "Session not found", "status": "error"}
        
        session = session_response.data[0]
        
        if session["status"] != "completed":
            return {"error": "Session must be completed before using Think Harder", "status": "error"}
        
        # Get all session data except the final results
        original_questions = session.get("questions", [])
        form_data = session.get("form_data", {})
        body_part = session.get("body_part", "")
        internal_state = session.get("internal_state", {})
        
        # Get medical data if user_id exists
        medical_data = {}
        llm_context = ""
        if request.user_id or session.get("user_id"):
            user_id = request.user_id or session.get("user_id")
            medical_data = await get_user_medical_data(user_id)
            llm_context = await get_llm_context_biz(user_id)
        
        # Create enhanced prompt for full o3 model
        enhanced_prompt = f"""You are an expert diagnostician with access to advanced reasoning capabilities. 
        
A patient has completed a deep dive diagnostic session. You need to re-analyze the entire case with enhanced reasoning.

PATIENT CASE DATA:
- Body Part: {body_part}
- Initial Symptoms: {json.dumps(form_data)}
- Medical History: {json.dumps(medical_data) if medical_data else "Not available"}

DIAGNOSTIC Q&A SESSION:
{chr(10).join([f"Q{q['question_number']}: {q.get('question', 'N/A')}{chr(10)}A{q['question_number']}: {q.get('answer', 'N/A')}" for q in original_questions])}

Previous Analysis State: {json.dumps(internal_state)}

INSTRUCTIONS FOR ENHANCED ANALYSIS:
1. Apply advanced medical reasoning patterns:
   - Differential diagnosis with Bayesian probability updates
   - Pattern recognition for rare conditions
   - Consider diagnostic test recommendations
   - Analyze symptom clustering and temporal patterns
   
2. Look for subtle patterns that may have been missed:
   - Rare condition markers
   - Systemic connections between symptoms
   - Medication side effects or interactions
   
3. Provide chain-of-thought reasoning showing your diagnostic process

4. Aim for 90%+ diagnostic confidence through systematic analysis

Return a JSON response with this exact structure:
{{
    "primaryCondition": "Most likely diagnosis based on enhanced analysis",
    "confidence": 85,  // Your confidence percentage (0-100)
    "likelihood": "Very Likely|Likely|Possible|Unlikely",
    "differentials": [
        {{
            "condition": "Alternative condition name",
            "probability": 20,  // percentage as number (0-100)
            "reasoning": "Why this is considered"
        }}
    ],
    "recommendations": [
        "Specific next steps or tests recommended"
    ],
    "redFlags": [
        "Any concerning symptoms that need immediate attention"
    ],
    "keyInsights": "Most significant finding from enhanced analysis that changes or confirms the diagnosis",
    "reasoningChain": [
        "Step 1: Initial symptom analysis shows...",
        "Step 2: Temporal pattern suggests...",
        "Step 3: Differential diagnosis reveals..."
    ],
    "enhancedFindings": "New insights discovered through advanced reasoning that weren't apparent in initial analysis"
}}"""

        # Call o4-mini-high for cost-efficient enhanced reasoning
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": enhanced_prompt},
                {"role": "user", "content": "Perform enhanced diagnostic analysis with advanced reasoning"}
            ],
            model=request.model,  # openai/o4-mini-high by default
            user_id=request.user_id or session.get("user_id"),
            temperature=0.2,  # Lower temperature for more consistent reasoning
            max_tokens=2000
        )
        
        # Parse enhanced analysis
        try:
            enhanced_analysis = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not enhanced_analysis:
                # Fallback structure
                enhanced_analysis = {
                    "error": "Failed to parse enhanced analysis",
                    "raw_response": llm_response.get("raw_content", "")
                }
        except Exception as e:
            print(f"Parse error in think harder: {e}")
            enhanced_analysis = {
                "error": str(e),
                "raw_response": llm_response.get("raw_content", "")
            }
        
        # Calculate confidence improvement
        original_confidence = session.get("final_confidence", 0)
        enhanced_confidence = enhanced_analysis.get("confidence", original_confidence)
        confidence_improvement = enhanced_confidence - original_confidence
        
        # Update session with enhanced analysis
        update_data = {
            "enhanced_analysis": enhanced_analysis,
            "enhanced_confidence": enhanced_confidence,
            "enhanced_model": request.model,
            "enhanced_at": datetime.now(timezone.utc).isoformat(),
            "confidence_improvement": confidence_improvement
        }
        
        try:
            supabase.table("deep_dive_sessions").update(update_data).eq("id", request.session_id).execute()
        except Exception as db_error:
            print(f"Error updating session with enhanced analysis: {db_error}")
        
        return {
            "status": "success",
            "enhanced_analysis": enhanced_analysis,
            "original_confidence": original_confidence,
            "enhanced_confidence": enhanced_confidence,
            "confidence_improvement": confidence_improvement,
            "key_insights": enhanced_analysis.get("keyInsights", ""),
            "reasoning_chain": enhanced_analysis.get("reasoningChain", []),
            "model_used": request.model,
            "processing_time_ms": llm_response.get("usage", {}).get("total_time", 0),
            "usage": llm_response.get("usage", {})
        }
        
    except Exception as e:
        print(f"Error in deep dive think harder: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/deep-dive/ask-more") 
async def deep_dive_ask_more(request: DeepDiveAskMoreRequest):
    """Generate additional questions to reach target confidence level"""
    try:
        # Get session from database
        session_response = supabase.table("deep_dive_sessions").select("*").eq("id", request.session_id).execute()
        
        if not session_response.data:
            return {"error": "Session not found", "status": "error"}
        
        session = session_response.data[0]
        
        if session["status"] != "completed":
            return {"error": "Session must be completed before asking more questions", "status": "error"}
        
        # Get current confidence
        current_confidence = session.get("final_confidence", 0)
        if current_confidence >= request.target_confidence:
            return {
                "status": "success",
                "message": f"Target confidence of {request.target_confidence}% already achieved",
                "current_confidence": current_confidence,
                "questions_needed": 0
            }
        
        # Get session data
        questions_asked = session.get("questions", [])
        form_data = session.get("form_data", {})
        body_part = session.get("body_part", "")
        final_analysis = session.get("final_analysis", {})
        
        # Get medical data if available
        medical_data = {}
        if request.user_id or session.get("user_id"):
            user_id = request.user_id or session.get("user_id")
            medical_data = await get_user_medical_data(user_id)
        
        # Get all previous questions from the questions array
        all_previous_questions = [q.get("question", "") for q in questions_asked if q.get("question")]
        
        # Check total questions against global max
        total_questions = len(all_previous_questions)
        if total_questions >= DEEP_DIVE_CONFIG["max_questions"]:
            return {
                "status": "success", 
                "message": f"Maximum of {DEEP_DIVE_CONFIG['max_questions']} total questions reached",
                "current_confidence": current_confidence,
                "total_questions_asked": total_questions
            }
        
        # Check how many additional questions have already been asked
        additional_questions = session.get("additional_questions", [])
        questions_remaining = min(
            request.max_questions - len(additional_questions),
            DEEP_DIVE_CONFIG["max_questions"] - total_questions
        )
        
        if questions_remaining <= 0:
            return {
                "status": "success", 
                "message": f"Maximum questions limit reached",
                "current_confidence": current_confidence,
                "questions_asked": len(additional_questions),
                "total_questions": total_questions
            }
        
        # Create prompt for generating highly leveraged question
        question_prompt = f"""You are an expert physician conducting a diagnostic interview. A patient has completed an initial assessment but diagnostic confidence is below target.

CURRENT SITUATION:
- Primary Diagnosis: {final_analysis.get('primaryCondition', 'Unknown')}
- Current Confidence: {current_confidence}%
- Target Confidence: {request.target_confidence}%
- Confidence Gap: {request.target_confidence - current_confidence}%
- Questions Remaining: {questions_remaining} (of {request.max_questions} max)

PATIENT DATA:
- Body Part: {body_part}
- Initial Symptoms: {json.dumps(form_data)}
- Medical History: {json.dumps(medical_data) if medical_data else "Not available"}

QUESTIONS ALREADY ASKED:
{chr(10).join([f"Q{i+1}: {q.get('question', 'N/A')}{chr(10)}A: {q.get('answer', 'N/A')}" for i, q in enumerate(questions_asked)])}

ADDITIONAL QUESTIONS ASKED:
{chr(10).join([f"Q{i+1}: {q.get('question', 'N/A')}{chr(10)}A: {q.get('answer', 'N/A')}" for i, q in enumerate(additional_questions)])}

CURRENT DIFFERENTIAL DIAGNOSES:
{json.dumps(final_analysis.get('differentials', []))}

Your task is to generate ONE highly leveraged question that will most effectively increase diagnostic confidence. Focus on:

1. Questions that distinguish between the top differential diagnoses
2. Red flag symptoms that haven't been explored
3. Temporal patterns or triggers not yet clarified
4. Associated symptoms that could confirm/exclude conditions
5. Response to treatments or specific maneuvers

The question should be:
- Specific and actionable (not vague)
- Non-repetitive (check all previous questions)
- Focused on the biggest diagnostic uncertainty
- Likely to provide high diagnostic value

Return JSON with this structure:
{{
    "question": "Your specific diagnostic question here",
    "question_category": "differential_diagnosis|red_flags|temporal_factors|associated_symptoms|treatment_response",
    "reasoning": "Why this question will help increase confidence",
    "expected_confidence_gain": 15,  // Realistic estimate of confidence increase (5-20)
    "targets_condition": "Which specific condition this helps confirm/exclude"
}}"""

        # Call LLM to generate question
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": question_prompt},
                {"role": "user", "content": "Generate the most diagnostically valuable question"}
            ],
            model="deepseek/deepseek-chat",  # Use standard model for question generation
            user_id=request.user_id or session.get("user_id"),
            temperature=0.7,
            max_tokens=500
        )
        
        # Parse question response
        try:
            question_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not question_data or not question_data.get("question"):
                # Fallback question
                question_data = {
                    "question": f"Have you noticed if your {body_part} symptoms change with specific activities, positions, or times of day?",
                    "question_category": "temporal_factors",
                    "reasoning": "Understanding patterns can help narrow the diagnosis",
                    "expected_confidence_gain": 10
                }
        except Exception as e:
            print(f"Parse error in ask more: {e}")
            question_data = {
                "question": "Can you describe any other symptoms you've noticed, even if they seem unrelated?",
                "question_category": "associated_symptoms",
                "reasoning": "Additional symptoms may reveal systemic conditions",
                "expected_confidence_gain": 10
            }
        
        # Calculate estimated questions to reach target
        avg_confidence_gain = 12  # Average expected gain per question
        confidence_gap = request.target_confidence - current_confidence
        estimated_questions = min(
            max(1, int(confidence_gap / avg_confidence_gain)), 
            questions_remaining
        )
        
        # Check for duplicate question
        if is_duplicate_question(question_data.get("question", ""), all_previous_questions):
            print(f"Duplicate question detected in ask-more - trying alternate")
            # Generate a more specific alternate question
            question_data = {
                "question": f"What specific aspect of your {body_part} condition concerns you most that we haven't discussed?",
                "question_category": "patient_concerns",
                "reasoning": "Patient perspective can reveal overlooked symptoms",
                "expected_confidence_gain": 8
            }
        
        # Prepare response
        response = {
            "status": "success",
            "question": question_data.get("question"),
            "question_number": len(questions_asked) + len(additional_questions) + 1,
            "question_category": question_data.get("question_category"),
            "current_confidence": current_confidence,
            "target_confidence": request.target_confidence,
            "confidence_gap": confidence_gap,
            "estimated_questions_remaining": estimated_questions,
            "max_questions_remaining": questions_remaining,
            "reasoning": question_data.get("reasoning"),
            "expected_confidence_gain": question_data.get("expected_confidence_gain", 10)
        }
        
        # Store the generated question in session for tracking
        try:
            additional_questions.append({
                "question": question_data.get("question"),
                "category": question_data.get("question_category"),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending"
            })
            
            supabase.table("deep_dive_sessions").update({
                "additional_questions": additional_questions,
                "ask_more_active": True
            }).eq("id", request.session_id).execute()
        except Exception as db_error:
            print(f"Error updating session with new question: {db_error}")
        
        return response
        
    except Exception as e:
        print(f"Error in deep dive ask more: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/quick-scan/think-harder")
async def quick_scan_think_harder(request: QuickScanThinkHarderRequest):
    """Enhanced analysis for Quick Scan results using premium model"""
    try:
        # Get quick scan data
        scan_id = request.scan_id
        if not scan_id:
            return {"error": "scan_id is required", "status": "error"}
        
        # Fetch quick scan from database
        scan_response = supabase.table("quick_scans").select("*").eq("id", scan_id).execute()
        
        if not scan_response.data:
            return {"error": "Quick scan not found", "status": "error"}
        
        scan = scan_response.data[0]
        
        # Get user medical data if available
        medical_data = {}
        llm_context = ""
        if scan.get("user_id"):
            medical_data = await get_user_medical_data(scan["user_id"])
            llm_context = await get_llm_context_biz(scan["user_id"])
        
        # Create enhanced analysis prompt
        enhanced_prompt = f"""You are an expert physician providing a deeper, more thorough analysis of a patient's symptoms.

Initial Quick Scan Analysis:
{json.dumps(scan.get("analysis", {}), indent=2)}

Body Part: {scan.get("body_part", "")}
Symptoms: {json.dumps(scan.get("form_data", {}), indent=2)}

Medical History:
{json.dumps(medical_data, indent=2) if medical_data and "error" not in medical_data else "No medical history available"}

Provide an enhanced analysis with:
1. More detailed differential diagnosis
2. Specific red flags to watch for
3. Recommended diagnostic tests
4. Treatment options to discuss with healthcare provider
5. Timeline expectations
6. When to seek immediate care

Format as JSON with these fields:
{{
    "primary_diagnosis": {{
        "condition": "Most likely condition",
        "confidence": 85,  // percentage
        "supporting_evidence": ["evidence1", "evidence2"],
        "contradicting_factors": ["factor1", "factor2"] 
    }},
    "differential_diagnoses": [
        {{
            "condition": "Alternative condition",
            "probability": 20,  // percentage as number (0-100)
            "key_differentiators": ["what would make this more likely"]
        }}
    ],
    "red_flags": [
        {{
            "symptom": "Specific symptom to watch for",
            "urgency": "immediate|24hrs|routine",
            "action": "What to do if this occurs"
        }}
    ],
    "diagnostic_recommendations": [
        {{
            "test": "Test name",
            "purpose": "What it will reveal",
            "priority": "high|medium|low"
        }}
    ],
    "treatment_considerations": [
        {{
            "approach": "Treatment option",
            "benefits": ["benefit1", "benefit2"],
            "considerations": ["consider1", "consider2"]
        }}
    ],
    "timeline": {{
        "expected_improvement": "Timeline if treatment works",
        "reassessment_needed": "When to follow up if no improvement",
        "natural_course": "What happens without treatment"
    }},
    "immediate_care_criteria": ["Go to ER if...", "Call doctor immediately if..."],
    "confidence": 90,  // Overall confidence in this enhanced analysis
    "clinical_pearls": ["Key insights that might be missed"]
}}"""

        # Use premium model for enhanced analysis
        model = request.model  # Default to GPT-4 from request model
        
        # Call LLM
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": enhanced_prompt},
                {"role": "user", "content": "Provide enhanced analysis based on the symptoms and initial assessment"}
            ],
            model=model,
            user_id=scan.get("user_id"),
            temperature=0.2,  # Lower temperature for consistency
            max_tokens=2000
        )
        
        # Parse response
        try:
            enhanced_analysis = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not enhanced_analysis:
                enhanced_analysis = {
                    "error": "Failed to parse enhanced analysis",
                    "raw_response": llm_response.get("raw_content", "")
                }
        except Exception as e:
            print(f"Parse error in quick scan think harder: {e}")
            enhanced_analysis = {
                "error": str(e),
                "raw_response": llm_response.get("raw_content", "")
            }
        
        # Calculate confidence improvement
        original_confidence = scan.get("confidence", 0)
        enhanced_confidence = enhanced_analysis.get("confidence", original_confidence)
        confidence_improvement = enhanced_confidence - original_confidence
        
        # Update quick scan with enhanced analysis
        try:
            supabase.table("quick_scans").update({
                "enhanced_analysis": enhanced_analysis,
                "enhanced_confidence": enhanced_confidence,
                "enhanced_model": model,
                "enhanced_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", scan_id).execute()
        except Exception as db_error:
            print(f"Error updating quick scan: {db_error}")
        
        return {
            "status": "success",
            "enhanced_analysis": enhanced_analysis,
            "original_confidence": original_confidence,
            "enhanced_confidence": enhanced_confidence,
            "confidence_improvement": confidence_improvement,
            "model_used": model,
            "scan_id": scan_id,
            "usage": llm_response.get("usage", {})
        }
        
    except Exception as e:
        print(f"Error in quick scan think harder: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/quick-scan/think-harder-o4")
async def quick_scan_think_harder_o4(request: QuickScanO4MiniRequest):
    """Enhanced analysis using o4-mini for balanced reasoning and cost"""
    try:
        # Get quick scan data
        scan_id = request.scan_id
        if not scan_id:
            return {"error": "scan_id is required", "status": "error"}
        
        # Fetch quick scan from database
        scan_response = supabase.table("quick_scans").select("*").eq("id", scan_id).execute()
        
        if not scan_response.data:
            return {"error": "Quick scan not found", "status": "error"}
        
        scan = scan_response.data[0]
        
        # Check if we already have o4-mini analysis
        if scan.get("o4_mini_analysis"):
            return {
                "status": "success",
                "message": "o4-mini analysis already exists",
                "o4_mini_analysis": scan["o4_mini_analysis"],
                "original_confidence": scan.get("confidence", 0),
                "o4_mini_confidence": scan.get("o4_mini_confidence", 0),
                "model_used": scan.get("o4_mini_model", "openai/o4-mini")
            }
        
        # Get user medical data if available
        medical_data = {}
        llm_context = ""
        if scan.get("user_id"):
            medical_data = await get_user_medical_data(scan["user_id"])
            llm_context = await get_llm_context_biz(scan["user_id"])
        
        # Create o4-mini specific prompt
        o4_mini_prompt = f"""You are o4-mini, providing enhanced medical analysis with efficient reasoning.

INITIAL ANALYSIS:
{json.dumps(scan.get("analysis_result", {}), indent=2)}

PATIENT DATA:
- Body Part: {scan.get("body_part", "")}
- Symptoms: {json.dumps(scan.get("form_data", {}), indent=2)}
- Medical History: {json.dumps(medical_data, indent=2) if medical_data and "error" not in medical_data else "No history available"}

YOUR TASK:
Provide deeper analysis by:
1. Identifying overlooked patterns in the symptoms
2. Considering less common differential diagnoses
3. Suggesting specific diagnostic tests or evaluations
4. Providing more precise timeline expectations

Focus on practical, actionable insights that add value beyond the initial analysis.

CRITICAL: Output ONLY valid JSON with no text before or after:
{{
    "enhanced_diagnosis": {{
        "primary": "More specific diagnosis based on pattern analysis",
        "confidence": 85,
        "key_pattern": "The critical symptom pattern that clarifies the diagnosis"
    }},
    "overlooked_considerations": [
        {{
            "factor": "Overlooked symptom or pattern",
            "significance": "Why this matters"
        }}
    ],
    "differential_refinement": [
        {{
            "condition": "Alternative diagnosis",
            "probability": 20,  // percentage as number (0-100)
            "distinguishing_features": ["What would make this more likely"]
        }}
    ],
    "specific_recommendations": [
        {{
            "action": "Specific test or evaluation",
            "rationale": "Why this is needed",
            "urgency": "immediate|within_days|routine"
        }}
    ],
    "timeline_expectations": {{
        "with_treatment": "Expected improvement timeline",
        "without_treatment": "Natural course",
        "red_flag_timeline": "When to worry if not improving"
    }},
    "confidence": 88,
    "reasoning_summary": "Brief summary of key reasoning that led to enhanced diagnosis"
}}"""

        # Call o4-mini
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": o4_mini_prompt},
                {"role": "user", "content": "Provide enhanced analysis with focused reasoning"}
            ],
            model=request.model,  # "openai/o4-mini"
            user_id=scan.get("user_id"),
            temperature=0.1,  # Very low temperature for consistency
            max_tokens=1500
        )
        
        # Parse response
        try:
            o4_mini_analysis = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not o4_mini_analysis:
                o4_mini_analysis = {
                    "error": "Failed to parse o4-mini analysis",
                    "raw_response": llm_response.get("raw_content", "")
                }
        except Exception as e:
            print(f"Parse error in o4-mini analysis: {e}")
            o4_mini_analysis = {
                "error": str(e),
                "raw_response": llm_response.get("raw_content", "")
            }
        
        # Calculate confidence improvement
        original_confidence = scan.get("confidence", 0)
        o4_mini_confidence = o4_mini_analysis.get("confidence", original_confidence)
        confidence_improvement = o4_mini_confidence - original_confidence
        
        # Update quick scan with o4-mini analysis
        try:
            supabase.table("quick_scans").update({
                "o4_mini_analysis": o4_mini_analysis,
                "o4_mini_confidence": o4_mini_confidence,
                "o4_mini_model": request.model,
                "o4_mini_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", scan_id).execute()
        except Exception as db_error:
            print(f"Error updating quick scan with o4-mini analysis: {db_error}")
        
        return {
            "status": "success",
            "analysis_tier": "enhanced",
            "o4_mini_analysis": o4_mini_analysis,
            "original_confidence": original_confidence,
            "o4_mini_confidence": o4_mini_confidence,
            "confidence_improvement": confidence_improvement,
            "model_used": request.model,
            "processing_message": "o4-mini-ized",
            "next_tier_available": True,
            "next_tier_preview": "Ultra Think with Grok can explore rare conditions and complex symptom interactions",
            "scan_id": scan_id,
            "usage": llm_response.get("usage", {})
        }
        
    except Exception as e:
        print(f"Error in quick scan o4-mini analysis: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/quick-scan/ultra-think")
async def quick_scan_ultra_think(request: QuickScanUltraThinkRequest):
    """Maximum reasoning analysis using Grok 4 for complex cases - handles both Quick Scan and Deep Dive"""
    try:
        # Determine which type of scan we're dealing with
        scan_data = None
        scan_type = None
        
        # Try quick scan first
        if request.scan_id:
            scan_response = supabase.table("quick_scans").select("*").eq("id", request.scan_id).execute()
            if scan_response.data:
                scan_data = scan_response.data[0]
                scan_type = "quick_scan"
        
        # Try deep dive if no quick scan found or if deep_dive_id provided
        if not scan_data and (request.deep_dive_id or request.scan_id):
            dive_id = request.deep_dive_id or request.scan_id  # Frontend may send deep dive ID as scan_id
            dive_response = supabase.table("deep_dive_sessions").select("*").eq("id", dive_id).execute()
            if dive_response.data:
                scan_data = dive_response.data[0]
                scan_type = "deep_dive"
        
        if not scan_data:
            return {"error": "No scan or deep dive found with provided ID", "status": "error"}
        
        scan = scan_data
        
        # Get all previous analyses based on scan type
        if scan_type == "quick_scan":
            original_analysis = scan.get("analysis_result", {})
            o4_mini_analysis = scan.get("o4_mini_analysis", {})
            enhanced_analysis = scan.get("enhanced_analysis", {})
            form_data = scan.get("form_data", {})
            body_part = scan.get("body_part", "")
        else:  # deep_dive
            original_analysis = scan.get("final_analysis", {})
            o4_mini_analysis = {}  # Deep dives don't have o4-mini analysis
            enhanced_analysis = scan.get("enhanced_analysis", {})
            form_data = scan.get("form_data", {})
            body_part = scan.get("body_part", "")
        
        # Get user medical data if available
        medical_data = {}
        llm_context = ""
        if scan.get("user_id"):
            medical_data = await get_user_medical_data(scan["user_id"])
            llm_context = await get_llm_context_biz(scan["user_id"])
        
        # Create Grok 4 ultra reasoning prompt
        ultra_prompt = f"""You are Grok 4, applying maximum reasoning capability to solve a complex medical case.

COMPREHENSIVE CASE DATA:

Initial Symptoms:
{json.dumps(form_data, indent=2)}

Body Part: {body_part}

Medical History:
{json.dumps(medical_data, indent=2) if medical_data and "error" not in medical_data else "No history available"}

PREVIOUS ANALYSES:
1. Initial Analysis (Gemini 2.5 Pro):
{json.dumps(original_analysis, indent=2)}

2. o4-mini Enhanced Analysis:
{json.dumps(o4_mini_analysis, indent=2) if o4_mini_analysis else "Not performed"}

3. Standard Enhanced Analysis:
{json.dumps(enhanced_analysis, indent=2) if enhanced_analysis else "Not performed"}

ULTRA REASONING TASK:
Apply your maximum reasoning capability to:

1. DEEP PATTERN ANALYSIS
   - Identify subtle symptom clusters that suggest rare conditions
   - Analyze temporal relationships between symptoms
   - Consider genetic/familial predispositions

2. ADVANCED DIFFERENTIAL DIAGNOSIS
   - Include rare conditions (zebras) that fit the pattern
   - Calculate relative probabilities using Bayesian reasoning
   - Consider mimics and masqueraders

3. SYSTEMIC CONNECTIONS
   - How might this connect to other body systems?
   - What cascade effects should we consider?
   - Are there underlying metabolic/hormonal factors?

4. DIAGNOSTIC STRATEGY
   - What's the most efficient path to definitive diagnosis?
   - Which tests rule in/out the most conditions?
   - Cost-benefit analysis of different approaches

5. TREATMENT IMPLICATIONS
   - How does the diagnosis affect treatment urgency?
   - What are the risks of delayed diagnosis?
   - Prevention strategies for complications

CRITICAL: Output ONLY valid JSON:
{{
    "ultra_diagnosis": {{
        "primary": "Most likely diagnosis with nuanced understanding",
        "confidence": 95,
        "reasoning_chain": [
            "Step 1: Key observation...",
            "Step 2: This pattern suggests...",
            "Step 3: Ruling out X because..."
        ]
    }},
    "rare_considerations": [
        {{
            "condition": "Rare condition name",
            "probability": 5,
            "key_markers": ["Specific signs that suggest this"],
            "diagnostic_test": "Definitive test to confirm/exclude"
        }}
    ],
    "systemic_analysis": {{
        "primary_system": "Main affected system",
        "secondary_effects": ["Other systems potentially involved"],
        "underlying_factors": ["Possible root causes"]
    }},
    "diagnostic_strategy": {{
        "immediate_tests": ["Test 1 - rules out X", "Test 2 - confirms Y"],
        "staged_approach": ["If initial tests negative, then..."],
        "cost_efficient_path": "Recommended sequence to minimize cost/invasiveness"
    }},
    "critical_insights": [
        "Insight that changes management approach",
        "Finding that wasn't obvious in previous analyses"
    ],
    "confidence": 96,
    "complexity_score": 8.5,  // 1-10 scale of case complexity
    "recommendation_change": "How this analysis changes the recommended approach"
}}"""

        # Call Grok 4
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": ultra_prompt},
                {"role": "user", "content": "Apply maximum reasoning to provide definitive analysis"}
            ],
            model=request.model,  # "x-ai/grok-beta"
            user_id=scan.get("user_id"),
            temperature=0.1,
            max_tokens=2500
        )
        
        # Parse response
        try:
            ultra_analysis = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not ultra_analysis:
                ultra_analysis = {
                    "error": "Failed to parse ultra analysis",
                    "raw_response": llm_response.get("raw_content", "")
                }
        except Exception as e:
            print(f"Parse error in ultra analysis: {e}")
            ultra_analysis = {
                "error": str(e),
                "raw_response": llm_response.get("raw_content", "")
            }
        
        # Calculate cumulative confidence progression
        original_confidence = original_analysis.get("confidence", 0)
        o4_mini_confidence = o4_mini_analysis.get("confidence", original_confidence) if o4_mini_analysis else original_confidence
        ultra_confidence = ultra_analysis.get("confidence", o4_mini_confidence)
        
        # Update the appropriate table with ultra analysis
        try:
            update_data = {
                "ultra_analysis": ultra_analysis,
                "ultra_confidence": ultra_confidence,
                "ultra_model": request.model,
                "ultra_at": datetime.now(timezone.utc).isoformat()
            }
            
            if scan_type == "quick_scan":
                supabase.table("quick_scans").update(update_data).eq("id", request.scan_id).execute()
            else:  # deep_dive
                supabase.table("deep_dive_sessions").update(update_data).eq("id", request.deep_dive_id or request.scan_id).execute()
        except Exception as db_error:
            print(f"Error updating {scan_type} with ultra analysis: {db_error}")
        
        return {
            "status": "success",
            "analysis_tier": "ultra",
            "ultra_analysis": ultra_analysis,
            "confidence_progression": {
                "original": original_confidence,
                "o4_mini": o4_mini_confidence,
                "ultra": ultra_confidence
            },
            "total_confidence_gain": ultra_confidence - original_confidence,
            "model_used": request.model,
            "processing_message": "Grokked your symptoms",
            "complexity_score": ultra_analysis.get("complexity_score", 0),
            "critical_insights": ultra_analysis.get("critical_insights", []),
            "scan_id": request.scan_id if scan_type == "quick_scan" else None,
            "deep_dive_id": (request.deep_dive_id or request.scan_id) if scan_type == "deep_dive" else None,
            "scan_type": scan_type,
            "usage": llm_response.get("usage", {})
        }
        
    except Exception as e:
        print(f"Error in quick scan ultra think: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/quick-scan/ask-more")
async def quick_scan_ask_more(request: QuickScanAskMoreRequest):
    """Generate follow-up questions for Quick Scan to improve confidence"""
    try:
        # Get quick scan data
        scan_response = supabase.table("quick_scans").select("*").eq("id", request.scan_id).execute()
        
        if not scan_response.data:
            return {"error": "Quick scan not found", "status": "error"}
        
        scan = scan_response.data[0]
        
        # Get current confidence from analysis result
        analysis_result = scan.get("analysis_result", {})
        current_confidence = analysis_result.get("confidence", 0)
        
        if current_confidence >= request.target_confidence:
            return {
                "status": "success",
                "message": f"Target confidence of {request.target_confidence}% already achieved",
                "current_confidence": current_confidence,
                "questions_needed": 0
            }
        
        # Get existing follow-up questions if any
        follow_up_questions = scan.get("follow_up_questions", [])
        questions_asked = len(follow_up_questions)
        
        if questions_asked >= request.max_questions:
            return {
                "status": "success",
                "message": f"Maximum of {request.max_questions} follow-up questions reached",
                "current_confidence": current_confidence,
                "questions_asked": questions_asked
            }
        
        # Get medical data if available
        medical_data = {}
        if request.user_id or scan.get("user_id"):
            user_id = request.user_id or scan.get("user_id")
            medical_data = await get_user_medical_data(user_id)
        
        # Extract all previous questions to avoid duplicates
        previous_questions = []
        if "questions" in scan.get("form_data", {}):
            previous_questions.append(scan["form_data"]["questions"])
        previous_questions.extend([q.get("question", "") for q in follow_up_questions])
        
        # Create prompt for targeted follow-up question
        follow_up_prompt = f"""You are a physician generating a follow-up question to improve diagnostic confidence for a Quick Scan result.

CURRENT ANALYSIS:
{json.dumps(analysis_result, indent=2)}

Current Confidence: {current_confidence}%
Target Confidence: {request.target_confidence}%
Confidence Gap: {request.target_confidence - current_confidence}%

PATIENT DATA:
- Body Part: {scan.get("body_part", "")}
- Initial Symptoms: {json.dumps(scan.get("form_data", {}), indent=2)}
- Medical History: {json.dumps(medical_data) if medical_data else "Not available"}

PREVIOUS FOLLOW-UP QUESTIONS:
{chr(10).join([f"Q{i+1}: {q.get('question', 'N/A')}" for i, q in enumerate(follow_up_questions)])}

Generate ONE highly targeted question that will:
1. Address the biggest uncertainty in the current diagnosis
2. Help distinguish between the top differential diagnoses
3. Identify any missed red flags
4. Be specific and easy for the patient to answer

The question should NOT repeat any previous questions.

Return JSON:
{{
    "question": "Your specific follow-up question",
    "focus_area": "differential_diagnosis|severity_assessment|timeline_clarification|red_flags|associated_symptoms",
    "reasoning": "Why this question will improve confidence",
    "expected_confidence_gain": 15  // Realistic estimate (10-25)
}}"""

        # Call LLM
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": follow_up_prompt},
                {"role": "user", "content": "Generate the most valuable follow-up question"}
            ],
            model="deepseek/deepseek-chat",
            user_id=request.user_id or scan.get("user_id"),
            temperature=0.7,
            max_tokens=500
        )
        
        # Parse response
        try:
            question_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not question_data or not question_data.get("question"):
                # Fallback question
                question_data = {
                    "question": f"How long have you been experiencing these {scan.get('body_part', 'symptoms')} symptoms, and have they gotten better or worse?",
                    "focus_area": "timeline_clarification",
                    "reasoning": "Understanding symptom progression helps narrow the diagnosis",
                    "expected_confidence_gain": 15
                }
        except Exception as e:
            print(f"Parse error in quick scan ask more: {e}")
            question_data = {
                "question": "Have you tried any treatments or medications, and if so, did they help?",
                "focus_area": "treatment_response",
                "reasoning": "Treatment response can confirm or exclude certain conditions",
                "expected_confidence_gain": 12
            }
        
        # Check for duplicate question
        if is_duplicate_question(question_data.get("question", ""), previous_questions):
            print(f"Duplicate question detected in quick scan ask-more")
            # Generate alternate question
            question_data = {
                "question": f"Are there any other symptoms or details about your {scan.get('body_part', 'condition')} that might be important?",
                "focus_area": "associated_symptoms",
                "reasoning": "Additional details may reveal overlooked aspects",
                "expected_confidence_gain": 10
            }
        
        # Calculate estimated questions to reach target
        avg_confidence_gain = 15
        confidence_gap = request.target_confidence - current_confidence
        estimated_questions = min(
            max(1, int(confidence_gap / avg_confidence_gain)),
            request.max_questions - questions_asked
        )
        
        # Store the new question
        try:
            follow_up_questions.append({
                "question": question_data.get("question"),
                "focus_area": question_data.get("focus_area"),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending"
            })
            
            supabase.table("quick_scans").update({
                "follow_up_questions": follow_up_questions,
                "ask_more_active": True
            }).eq("id", request.scan_id).execute()
        except Exception as db_error:
            print(f"Error updating quick scan with follow-up question: {db_error}")
        
        return {
            "status": "success",
            "question": question_data.get("question"),
            "question_number": questions_asked + 1,
            "focus_area": question_data.get("focus_area"),
            "current_confidence": current_confidence,
            "target_confidence": request.target_confidence,
            "confidence_gap": confidence_gap,
            "estimated_questions_remaining": estimated_questions,
            "max_questions_remaining": request.max_questions - questions_asked - 1,
            "reasoning": question_data.get("reasoning"),
            "expected_confidence_gain": question_data.get("expected_confidence_gain", 15)
        }
        
    except Exception as e:
        print(f"Error in quick scan ask more: {e}")
        return {"error": str(e), "status": "error"}