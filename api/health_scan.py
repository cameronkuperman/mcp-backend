"""Health Scan API endpoints - Quick Scan and Deep Dive"""
from fastapi import APIRouter
from datetime import datetime, timezone
import uuid
import json

from models.requests import (
    QuickScanRequest, 
    DeepDiveStartRequest, 
    DeepDiveContinueRequest, 
    DeepDiveCompleteRequest
)
from supabase_client import supabase
from business_logic import call_llm, make_prompt, get_llm_context as get_llm_context_biz, get_user_data
from utils.json_parser import extract_json_from_response
from api.chat import get_user_medical_data

router = APIRouter(prefix="/api", tags=["health-scan"])

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
                    "confidence_score": analysis_result.get("confidence", 0),
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
        
        # Use chimera model for deep dive (like Oracle chat which works great!)
        model = request.model or "tngtech/deepseek-r1t-chimera:free"
        
        # Add model validation and fallback
        WORKING_MODELS = [
            "tngtech/deepseek-r1t-chimera:free",  # Best for deep dive!
            "deepseek/deepseek-chat",
            "meta-llama/llama-3.2-3b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "microsoft/phi-3-mini-128k-instruct:free"
        ]
        
        # If specified model not in list, use chimera
        if model not in WORKING_MODELS:
            print(f"Model {model} not in working list, using chimera")
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
            
            if not question_data:
                # Fallback: Create a generic first question
                question_data = {
                    "question": f"Can you describe the {request.body_part} pain in more detail? Is it sharp, dull, burning, or aching?",
                    "question_type": "symptom_characterization",
                    "internal_analysis": {"fallback": True}
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
            "created_at": datetime.now(timezone.utc).isoformat()
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
            model=session.get("model_used", "tngtech/deepseek-r1t-chimera:free"),  # Use chimera like Oracle
            user_id=session.get("user_id"),
            temperature=0.3,
            max_tokens=1024
        )
        
        # Parse response with fallback
        try:
            decision_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not decision_data:
                # Create fallback decision
                decision_data = {
                    "need_another_question": request.question_number < 2,
                    "current_confidence": 50 + (request.question_number * 15),  # Incremental confidence
                    "question": "Have you experienced any other symptoms along with this?",
                    "confidence_projection": "Gathering more information",
                    "updated_analysis": session.get("internal_state", {})
                }
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
        
        # Define thresholds
        CONFIDENCE_THRESHOLD = 90  # Target confidence level
        MIN_QUESTIONS = 2  # Minimum questions before allowing completion
        MAX_QUESTIONS = 10  # Maximum questions to prevent infinite loops
        
        print(f"Deep Dive Progress: Question {request.question_number}, Confidence: {current_confidence}%, Target: {CONFIDENCE_THRESHOLD}%")
        
        # Check if we need another question based on confidence
        need_more_questions = (
            current_confidence < CONFIDENCE_THRESHOLD and 
            request.question_number < MAX_QUESTIONS
        )
        
        # Always ask at least MIN_QUESTIONS
        if request.question_number < MIN_QUESTIONS:
            need_more_questions = True
        
        # Check if LLM also thinks we need another question
        llm_wants_more = decision_data.get("need_another_question", False)
        
        if need_more_questions or llm_wants_more:
            # Store the question for next iteration
            try:
                supabase.table("deep_dive_sessions").update({
                    "last_question": decision_data.get("question", ""),
                    "current_confidence": current_confidence
                }).eq("id", request.session_id).execute()
            except Exception as e:
                print(f"Error storing last question: {e}")
            
            # Check if we're approaching max questions
            is_final_question = request.question_number >= (MAX_QUESTIONS - 1)
            
            return {
                "question": decision_data.get("question", ""),
                "question_number": request.question_number + 1,
                "is_final_question": is_final_question,
                "confidence_projection": decision_data.get("confidence_projection", ""),
                "current_confidence": current_confidence,
                "confidence_threshold": CONFIDENCE_THRESHOLD,
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
            model=session.get("model_used", "tngtech/deepseek-r1t-chimera:free"),  # Use chimera like Oracle
            user_id=session.get("user_id"),
            temperature=0.3,
            max_tokens=2048
        )
        
        # Parse final analysis with comprehensive fallback
        try:
            analysis_result = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not analysis_result:
                # Create structured fallback analysis
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