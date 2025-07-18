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
    DeepDiveAskMoreRequest
)
from supabase_client import supabase
from business_logic import call_llm, make_prompt, get_llm_context as get_llm_context_biz, get_user_data
from utils.json_parser import extract_json_from_response
from utils.data_gathering import get_user_medical_data

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
            "likelihood": "percentage or descriptor",
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
        
        # Check how many additional questions have already been asked
        additional_questions = session.get("additional_questions", [])
        questions_remaining = request.max_questions - len(additional_questions)
        
        if questions_remaining <= 0:
            return {
                "status": "success", 
                "message": f"Maximum of {request.max_questions} additional questions reached",
                "current_confidence": current_confidence,
                "questions_asked": len(additional_questions)
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
{chr(10).join([f"Q{i+1}: {q.get('question', 'N/A')}\nA: {q.get('answer', 'N/A')}" for i, q in enumerate(questions_asked)])}

ADDITIONAL QUESTIONS ASKED:
{chr(10).join([f"Q{i+1}: {q.get('question', 'N/A')}\nA: {q.get('answer', 'N/A')}" for i, q in enumerate(additional_questions)])}

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