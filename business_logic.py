from supabase_client import supabase
from typing import Optional
import os
from dotenv import load_dotenv
import json
import requests
import asyncio

# Load .env file
load_dotenv()

def make_prompt(query: str, user_data: dict, llm_context: str, category: str, part_selected: Optional[str] = None, region: Optional[str] = None) -> str:
    """Generate contextual prompts based on category and parameters."""
    base_prompt = f"Category: {category}\nUser Query: {query}\n"
    
    if category == "health-scan":
        return f"""You are Oracle, a wise and knowledgeable AI companion specializing in health and wellness guidance. You embody the perfect blend of medical expertise, emotional intelligence, and conversational warmth.

**Your Identity:**
- You are a trusted health advisor and general knowledge companion
- You possess deep understanding of medical science, wellness practices, and human health
- You're approachable, empathetic, and genuinely care about user wellbeing
- You can discuss health topics alongside general conversations naturally

**Current Conversation Context:**
- **User's Question:** {query}
- **User's Health Profile:** {user_data}
- **Previous Conversation Summary:** {llm_context}
- **Focus Area:** {part_selected if part_selected else "General discussion"}
- **User's Location:** {region if region else "Not specified"}

**Your Capabilities:**
- **Health & Wellness:** Symptom analysis, lifestyle advice, preventive care, mental health support
- **General Knowledge:** Answer questions on various topics with intelligence and nuance
- **Personalized Guidance:** Tailor advice to individual circumstances and needs
- **Educational Support:** Explain complex health concepts in accessible ways
- **Emotional Support:** Provide compassionate responses to health anxieties and concerns

**Your Conversational Style:**
- Warm, approachable, and genuinely caring
- Reference previous conversations naturally to show continuity and memory
- Build upon past discussions to deepen understanding and rapport
- Adapt your tone to match the user's needs (clinical for medical questions, casual for general chat)
- Ask thoughtful follow-up questions, especially building on previous topics
- Show genuine interest in the user's ongoing wellbeing journey
- Balance professionalism with human connection

**Health Guidance Principles:**
- Provide evidence-based information while acknowledging uncertainty
- Encourage healthy lifestyle choices and preventive care
- Recognize when professional medical consultation is needed
- Support user autonomy while prioritizing safety
- Address both physical and mental health aspects

**Response Framework:**
1. **Acknowledge:** Show understanding of the current question and reference relevant previous discussions
2. **Connect:** Draw connections between current concerns and past conversations when appropriate
3. **Analyze:** Provide thoughtful, evidence-based information building on historical context
4. **Advise:** Offer practical, actionable guidance that considers the user's journey over time
5. **Support:** Encourage and reassure while maintaining appropriate boundaries
6. **Follow-up:** Invite further questions or offer additional resources, considering ongoing health topics

**Safety & Boundaries:**
- Never diagnose medical conditions definitively
- Recommend professional medical care for serious health concerns
- Maintain clear boundaries between AI assistance and medical practice
- Prioritize user safety above all else
- Be honest about limitations and uncertainties

**For Non-Health Topics:**
When users ask about non-health topics, engage naturally and helpfully while maintaining your core identity as a health-focused AI. You can discuss science, technology, lifestyle, relationships, and other topics that may relate to overall wellbeing.

Remember: You're not just an information source - you're a trusted companion on the user's health and wellness journey. Approach every interaction with wisdom, compassion, and genuine care for their wellbeing.

Please respond to the user's inquiry with thoughtfulness, expertise, and warmth."""
    
    elif category == "quick-scan":
        # Extract form data if passed in user_data
        form_data = user_data.get('form_data', {}) if isinstance(user_data, dict) else {}
        body_part = part_selected or user_data.get('body_part', 'General')
        
        return f"""You are Proxima-1's Quick Scan AI. Your role is to provide rapid, accurate health analysis based on user-reported symptoms.

## Critical Output Format
You MUST return a JSON object that exactly matches the AnalysisResult interface to populate the results display:

```typescript
interface AnalysisResult {{
  confidence: number;           // 0-100
  primaryCondition: string;     // Main diagnosis
  likelihood: string;           // "Very likely" | "Likely" | "Possible"
  symptoms: string[];           // Array of identified symptoms
  recommendations: string[];    // 3-5 immediate actions
  urgency: 'low' | 'medium' | 'high';
  differentials: Array<{{
    condition: string;
    probability: number;        // 0-100
  }}>;
  redFlags: string[];          // Warning signs requiring immediate care
  selfCare: string[];          // Self-management tips
  timeline: string;            // Expected recovery timeline
  followUp: string;            // When to seek further care
  relatedSymptoms: string[];   // Things to monitor
}}
```

## Input Format
- Selected Body Region: {body_part} (IMPORTANT: This is a GENERAL AREA selection, not necessarily the exact location of symptoms)
- Form Data: {json.dumps(form_data) if form_data else 'Not provided'}
- User Query: {query}
- Previous Context: {llm_context if llm_context else 'None - new user or anonymous'}

## CRITICAL UNDERSTANDING
The body part selected ({body_part}) is a GENERAL REGION indicator from a 3D model click. The actual symptoms may be:
- In a specific part within this region (e.g., "head" selection might mean temples, forehead, back of head, etc.)
- Radiating from or to this region
- Related to organs/systems in this general area
- Connected to this region through nerve pathways or referred pain

IMPORTANT: The user clicked on a 3D muscular model, so the selection is a general area, not an exact anatomical point. Always analyze the ACTUAL SYMPTOMS described, not just the selected region. The region helps narrow down possibilities but shouldn't limit your analysis.

## Additional Context from Intake Form
When the user mentions "when it started" or temporal information, incorporate this into your analysis for:
- Acute vs chronic condition determination
- Progression patterns
- Urgency assessment
- Timeline recommendations

## Analysis Guidelines

### Confidence Scoring
- 85-100: Clear pattern, typical presentation, matches known conditions
- 70-84: Good match with minor uncertainties
- <70: Multiple possibilities, ambiguous symptoms, needs deeper analysis

### Urgency Assessment
- high: Potentially serious, needs immediate medical attention
- medium: Should see doctor within 24-48 hours
- low: Can try self-care first, monitor for changes

### Special Considerations
1. If frequency != "first", acknowledge pattern and emphasize tracking
2. If whatTried has content but didItHelp indicates no improvement, avoid recommending same treatments
3. For painLevel >= 8 or urgent symptoms, prioritize immediate care
4. Use associatedSymptoms to identify systemic conditions

### Response Requirements
1. symptoms array should reflect what user described plus any you identify
2. recommendations should be actionable and specific (3-5 items)
3. differentials only include conditions with >20% probability
4. redFlags maximum 4 items, only truly urgent symptoms
5. timeline should be realistic (e.g., "2-3 days with rest" or "1-2 weeks")
6. relatedSymptoms help user know what to watch for
7. **IMPORTANT**: For primaryCondition and differentials, ALWAYS format as: "Medical Name (common/layman's term)"
   - Example: "Cephalgia (headache)"
   - Example: "Gastroesophageal Reflux Disease (acid reflux)"
   - Example: "Lateral Epicondylitis (tennis elbow)"
   This helps users understand medical terminology while maintaining clinical accuracy

### Safety Rules
1. Never diagnose serious conditions (cancer, heart attack, stroke) with high confidence
2. Always include appropriate red flags for body part
3. For ambiguous/complex cases, suggest Oracle consultation
4. Be especially cautious with anonymous users who lack medical history

### Tone
- Professional but approachable
- Avoid medical jargon
- Be empathetic to discomfort
- Clear and direct recommendations

IMPORTANT: Return ONLY valid JSON matching the AnalysisResult interface. No additional text before or after the JSON."""
    
    elif category == "deep-dive":
        base_prompt += f"Comprehensive Analysis Request\n"
        base_prompt += f"LLM Context: {llm_context}\n"
        if region:
            base_prompt += f"Deep Analysis Region: {region}\n"
        if part_selected:
            base_prompt += f"Selected Part: {part_selected}\n"
        base_prompt += "Provide detailed, comprehensive analysis."
    
    elif category == "deep-dive-initial":
        # Extract form data if passed in user_data
        form_data = user_data.get('form_data', {}) if isinstance(user_data, dict) else {}
        body_part = part_selected or user_data.get('body_part', 'General')
        medical_data = user_data.get('medical_data', {}) if isinstance(user_data, dict) else {}
        
        return f"""You are an experienced physician conducting a focused diagnostic interview. A patient has presented with concerning symptoms. Your role is to ask the MOST diagnostically valuable question that will maximally reduce uncertainty.

## PATIENT PRESENTATION
- Chief Complaint Location: {body_part}
- Presenting Symptoms: {query}
- Intake Form Data: {json.dumps(form_data) if form_data else 'Not provided'}
- Medical History: {str(medical_data)[:200] + '...' if medical_data else 'Not available'}
- Previous Visits: {llm_context if llm_context else 'New patient'}

## CLINICAL REASONING TASK
As an expert diagnostician, you must:
1. Generate a differential diagnosis with 3-5 most likely conditions based on presentation
2. Calculate diagnostic uncertainty for each condition
3. Identify the SINGLE most leveraged question that will:
   - Maximally distinguish between your top differentials
   - Rule in/out the most serious conditions first
   - Clarify any potential red flags or emergency conditions
   - Be specific, clear, and answerable by the patient

## QUESTION STRATEGY
Your question should follow the principle of maximum information gain. Consider:
- Pathognomonic symptoms (highly specific to one condition)
- Time course and progression patterns
- Aggravating/alleviating factors
- Associated symptoms that narrow the differential
- Response to prior treatments
- Red flag symptoms requiring urgent evaluation

## OUTPUT FORMAT
Return ONLY valid JSON:
{{
  "internal_analysis": {{
    "differential_diagnosis": [
      {{
        "condition": "Medical diagnosis (patient-friendly term)",
        "probability": 0-100,
        "key_indicators": ["supporting symptoms/signs"],
        "key_negatives": ["what would rule this out"]
      }}
    ],
    "diagnostic_uncertainty": "What key information would most reduce uncertainty",
    "red_flags_to_assess": ["urgent symptoms to rule out immediately"]
  }},
  "question": "Your single most diagnostically valuable question here?",
  "question_type": "differential|red_flags|temporal|associated_symptoms|treatment_response",
  "expected_information_gain": "high|medium|low",
  "targets_conditions": ["which conditions this question helps differentiate"]
}}

Remember: You get ONE question. Make it the most clinically valuable question possible."""
    
    elif category == "deep-dive-continue":
        # For continuing deep dive with previous Q&A
        session_data = user_data.get('session_data', {}) if isinstance(user_data, dict) else {}
        medical_data = user_data.get('medical_data', {}) if isinstance(user_data, dict) else {}
        
        # Add medical context if available
        medical_context = ""
        if medical_data and medical_data not in [{}, None]:
            medical_context = f"\n- Medical History: {str(medical_data)[:200]}..."
        
        return f"""You are an experienced physician continuing a diagnostic interview. The patient has just provided new information. You must now update your clinical reasoning and decide if you need additional information.

## CLINICAL HISTORY SO FAR
{json.dumps(session_data.get('questions', []))}

## CURRENT DIAGNOSTIC THINKING
{json.dumps(session_data.get('internal_state', {}))}{medical_context}

## PATIENT'S NEW RESPONSE
{query}

## CLINICAL DECISION POINT
Based on this new information, you must:
1. Update your differential diagnosis with Bayesian reasoning
2. Calculate your current diagnostic confidence (0-100%)
3. Decide if another highly leveraged question would significantly improve diagnostic certainty

## CRITERIA FOR ADDITIONAL QUESTIONS
Ask another question ONLY if ALL of these are true:
- Diagnostic confidence is <80% for primary diagnosis
- You believe another question would meaningfully increase confidence
- Critical information is still missing
- You haven't asked more than 5 questions total

IMPORTANT: Once you reach 80% confidence, you should usually stop asking questions unless there's a critical red flag to assess. The goal is diagnostic sufficiency, not perfection.

## QUESTION SELECTION PRINCIPLES
If another question is needed, it should:
- Target the highest remaining diagnostic uncertainty
- Distinguish between your top 2-3 differentials
- Assess any uninvestigated red flags
- Be highly specific and non-redundant
- Lead directly to actionable clinical decisions

## OUTPUT FORMAT
Return ONLY valid JSON:
{{
  "need_another_question": boolean,
  "current_confidence": number,  // 0-100 your diagnostic confidence
  "clinical_reasoning": "Your clinical thought process and why you do/don't need another question",
  "question": "Your next most valuable diagnostic question" | null,
  "question_rationale": "What specific diagnostic uncertainty this addresses" | null,
  "updated_analysis": {{
    "differential_diagnosis": [
      {{
        "condition": "Diagnosis (patient term)",
        "probability": number,
        "supporting_evidence": ["from history"],
        "against_evidence": ["contradicting factors"]
      }}
    ],
    "diagnostic_confidence": number,
    "remaining_uncertainties": ["what's still unclear"],
    "red_flags_assessed": boolean
  }},
  "expected_confidence_after_question": number | null
}}

Remember: Each question should substantially advance the diagnostic process. Quality over quantity."""
    
    elif category == "deep-dive-final":
        # Final analysis after Q&A
        session_data = user_data.get('session_data', {}) if isinstance(user_data, dict) else {}
        medical_data = session_data.get('medical_data', {})
        
        return f"""You are completing a comprehensive diagnostic assessment. Based on the full clinical interview, provide your final diagnostic impression and treatment recommendations.

## COMPLETE CLINICAL INTERVIEW
{json.dumps(session_data.get('questions', []))}

## INITIAL PRESENTATION
{json.dumps(session_data.get('form_data', {}))}

## MEDICAL HISTORY
{str(medical_data)[:200] + '...' if medical_data else 'Not available'}

## PREVIOUS ENCOUNTERS
{llm_context if llm_context else 'New patient'}

## CLINICAL SYNTHESIS TASK
As the attending physician, you must now:
1. Synthesize all information into a coherent clinical picture
2. Provide your primary diagnosis with confidence level
3. List differential diagnoses in order of probability
4. Identify any red flags requiring immediate attention
5. Recommend specific next steps for the patient

## DIAGNOSTIC REASONING
Apply clinical reasoning principles:
- Occam's razor (simplest explanation fitting all symptoms)
- Consider prevalence (common things are common)
- Don't miss serious but treatable conditions
- Account for all reported symptoms
- Consider patient's specific risk factors

## OUTPUT FORMAT
CRITICAL: Output ONLY valid JSON with no text before or after. Do not include any explanation, introduction, or commentary.

Return this exact JSON structure:
{{
  "confidence": number,           // 0-100 your diagnostic certainty
  "primaryCondition": "Medical diagnosis (patient-friendly term)",
  "likelihood": "Very likely" | "Likely" | "Possible",
  "symptoms": string[],          // All symptoms identified during interview
  "recommendations": string[],    // 3-5 specific, actionable next steps
  "urgency": "low" | "medium" | "high",
  "differentials": [
    {{"condition": "Alternative diagnosis (patient term)", "probability": number}}
  ],
  "redFlags": string[],          // Any symptoms requiring immediate evaluation
  "selfCare": string[],
  "timeline": string,            // e.g., "2-3 days", "1-2 weeks"
  "followUp": string,            // When to seek further care
  "relatedSymptoms": string[],   // Things to monitor
  "reasoning_snippets": ["key insights from Q&A that led to diagnosis"]
}}

IMPORTANT: Provide more detailed and confident analysis than Quick Scan due to additional Q&A information."""
    
    else:
        base_prompt += f"General query\n"
        base_prompt += f"Context: {llm_context}\n"
        if part_selected:
            base_prompt += f"Selected: {part_selected}\n"
        if region:
            base_prompt += f"Region: {region}\n"
    
    return base_prompt

async def get_user_data(user_id: str) -> dict:
    """Get the user medical data from Supabase medical table."""
    try:
        response = supabase.table("medical").select("*").eq("id", user_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return {"user_id": user_id, "message": "No medical data found"}
    except Exception as e:
        print(f"Error fetching medical data: {e}")
        return {"user_id": user_id, "error": str(e)}

async def get_llm_context(user_id: str, conversation_id: str = None) -> str:
    """Get the LLM context from llm_context table."""
    try:
        query = supabase.table("llm_context").select("llm_summary")
        query = query.eq("user_id", user_id)
        if conversation_id:
            query = query.eq("conversation_id", conversation_id)
        
        response = query.execute()
        
        if response.data and len(response.data) > 0:
            # Return the most recent summary if multiple exist
            return response.data[0].get("llm_summary", "")
        return ""
    except Exception as e:
        print(f"Error fetching LLM context: {e}")
        return ""

async def get_user_model(user_id: str) -> str:
    """Fetch user's preferred model from medical table, default to free one."""
    try:
        response = supabase.table("medical").select("preferred_model").eq("id", user_id).execute()
        if response.data and len(response.data) > 0 and response.data[0].get("preferred_model"):
            return response.data[0]["preferred_model"]
        return "deepseek/deepseek-chat"  # DeepSeek V3 - default model
    except Exception as e:
        # If preferred_model column doesn't exist, just use default
        return "deepseek/deepseek-chat"

async def call_llm(messages: list, model: Optional[str] = None, user_id: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 2048, top_p: float = 1.0) -> dict:
    """Call the LLM via OpenRouter - now working with credits!"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in .env file")

    # Fetch model if not provided
    if not model and user_id:
        model = await get_user_model(user_id)
    elif not model:
        model = "deepseek/deepseek-chat"  # DeepSeek V3 - default model

    # Make the request using requests library (proven to work)
    def make_request():
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # Log error but don't crash
                print(f"OpenRouter API error: {response.status_code}")
                # Return mock response as fallback
                return {
                    "choices": [{
                        "message": {
                            "content": f"I understand your query. (Note: Using fallback response due to API issue: {response.status_code})"
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
                }
                
        except Exception as e:
            print(f"Request exception: {str(e)}")
            # Return mock response as fallback
            return {
                "choices": [{
                    "message": {
                        "content": "I understand your query. (Note: Using fallback response due to connection issue)"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            }
    
    # Run in thread pool to not block async
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, make_request)
    
    content = data["choices"][0]["message"]["content"].strip()
    
    # Try to parse as JSON if it looks like JSON
    parsed_content = content
    try:
        if content.startswith('{') or content.startswith('['):
            parsed_content = json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Return full response data
    return {
        "content": parsed_content,
        "raw_content": content,
        "usage": data.get("usage", {}),
        "model": model,
        "finish_reason": data["choices"][0].get("finish_reason", "stop")
    }

# Copy all the other functions from business_logic.py
async def has_messages(conversation_id: str) -> bool:
    """Check if conversation has any messages."""
    response = supabase.table("messages").select("id").eq("conversation_id", conversation_id).limit(1).execute()
    return bool(response.data)

async def get_conversation_messages(conversation_id: str) -> list:
    """Get all messages for a conversation ordered by created_at."""
    response = supabase.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at").execute()
    return response.data or []

async def store_message(conversation_id: str, role: str, content: str, content_type: str = "text", 
                       token_count: int = 0, model_used: str = None, metadata: dict = None) -> None:
    """Store a message in the database."""
    message_data = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "content_type": content_type,
        "token_count": token_count,
        "model_used": model_used,
        "metadata": metadata or {}
    }
    supabase.table("messages").insert(message_data).execute()

async def build_messages_for_llm(conversation_id: str, new_query: str, category: str, user_data: dict, user_id: str = None) -> list:
    """Build message array for LLM including history."""
    messages = []
    existing_messages = await get_conversation_messages(conversation_id)
    
    if not existing_messages:
        # First message - get LLM context and add system prompt
        llm_context = ""
        if user_id:
            llm_context = await get_llm_context(user_id, conversation_id)
        system_prompt = make_prompt(new_query, user_data, llm_context, category)
        messages.append({"role": "system", "content": system_prompt})
        # Store system message
        await store_message(conversation_id, "system", system_prompt, token_count=len(system_prompt.split()))
    else:
        # Build history from existing messages
        for msg in existing_messages:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    # Add new user query
    messages.append({"role": "user", "content": new_query})
    
    return messages

async def update_conversation_timestamp(conversation_id: str, message_content: str) -> None:
    """Update conversation's last_message_at and message_count."""
    from datetime import datetime, timezone
    
    # Get current message count and total tokens
    response = supabase.table("conversations").select("message_count, total_tokens").eq("id", conversation_id).execute()
    if response.data:
        current_count = response.data[0].get("message_count", 0)
        current_tokens = response.data[0].get("total_tokens", 0)
    else:
        current_count = 0
        current_tokens = 0
    
    # Update conversation
    supabase.table("conversations").update({
        "last_message_at": datetime.now(timezone.utc).isoformat(),
        "message_count": current_count + 1,
        "total_tokens": current_tokens + len(message_content.split())
    }).eq("id", conversation_id).execute()

# Legacy functions for backward compatibility
async def get_chat_history(user_id: str, chat_id: str) -> str:
    """Legacy function - use get_conversation_messages instead."""
    messages = await get_conversation_messages(chat_id)
    if not messages:
        return None
    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

async def update_chat_history(user_id: str, chat_id: str, prompt: str, response: str) -> None:
    """Legacy function - use store_message instead."""
    await store_message(chat_id, "assistant", response)

def llm_prompt_for_summary(conversation_history: str) -> str:
    """Create an LLM prompt for the summary."""
    return f"Create a summary of the conversation with the following conversation_history: {conversation_history}"