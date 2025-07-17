"""Helper functions for generating summaries"""
from datetime import datetime, timezone
import uuid
from supabase_client import supabase
from business_logic import call_llm
from utils.token_counter import count_tokens

async def create_conversational_summary(conversation_id: str, user_id: str) -> str:
    """Generate a summary for a conversation"""
    try:
        # Validate UUIDs
        uuid.UUID(str(conversation_id))
        uuid.UUID(str(user_id))
    except ValueError as e:
        raise ValueError(f"Invalid UUID format: {e}")
    
    # Fetch all messages from conversation
    print(f"Fetching messages for conversation: {conversation_id}")
    messages_response = supabase.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at").execute()
    
    if not messages_response.data:
        print(f"No messages found for conversation: {conversation_id}")
        raise ValueError("No messages found for this conversation")
    
    messages = messages_response.data
    
    # Build conversation context
    conversation_text = ""
    total_tokens = 0
    
    for msg in messages:
        role = "User" if msg["role"] == "user" else "Oracle AI"
        conversation_text += f"{role}: {msg['content']}\n\n"
        total_tokens += count_tokens(msg['content'])
    
    print(f"Total conversation tokens: {total_tokens}")
    
    # Generate summary using AI
    summary_prompt = f"""Generate a medical summary of this health conversation. Include:
1. Chief complaints or main health concerns discussed
2. Symptoms mentioned (severity, duration, triggers)
3. Medical history or relevant context shared
4. Recommendations or next steps suggested
5. Any red flags or urgent concerns identified

Be concise but comprehensive. Format as a structured medical note.

CONVERSATION:
{conversation_text[:8000]}"""  # Limit context to avoid token limits

    llm_response = await call_llm(
        messages=[
            {"role": "system", "content": "You are a medical AI assistant creating a clinical summary."},
            {"role": "user", "content": summary_prompt}
        ],
        model="deepseek/deepseek-chat",
        user_id=user_id,
        temperature=0.3,
        max_tokens=1000
    )
    
    summary_content = llm_response.get("content", "")
    
    if not summary_content:
        raise ValueError("Failed to generate summary from LLM")
    
    # Save summary to llm_context table
    summary_data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "conversation_id": conversation_id,
        "summary": summary_content,
        "context_type": "conversation_summary",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "token_count": count_tokens(summary_content),
        "source_message_count": len(messages),
        "model_used": "deepseek/deepseek-chat"
    }
    
    insert_response = supabase.table("llm_context").insert(summary_data).execute()
    
    if not insert_response.data:
        print(f"Failed to save summary: {insert_response}")
        raise ValueError("Failed to save summary to database")
    
    print(f"Summary saved with ID: {summary_data['id']}")
    return summary_content

async def create_quick_scan_summary(quick_scan_id: str, user_id: str) -> str:
    """Generate a summary for a quick scan"""
    try:
        # Validate UUIDs
        uuid.UUID(str(quick_scan_id))
        uuid.UUID(str(user_id))
    except ValueError as e:
        raise ValueError(f"Invalid UUID format: {e}")
    
    # Fetch quick scan data
    scan_response = supabase.table("quick_scans").select("*").eq("id", quick_scan_id).eq("user_id", user_id).execute()
    
    if not scan_response.data:
        raise ValueError("Quick scan not found")
    
    scan_data = scan_response.data[0]
    
    # Build scan context
    scan_context = f"""QUICK SCAN SUMMARY:
Date: {scan_data['created_at']}
Body Part: {scan_data.get('body_part', 'Not specified')}
User Input: {scan_data.get('form_data', {}).get('symptoms', 'No symptoms provided')}
Pain Level: {scan_data.get('form_data', {}).get('painLevel', 'Not specified')}/10

ANALYSIS RESULT:
Primary Condition: {scan_data.get('analysis_result', {}).get('primaryCondition', 'Unknown')}
Confidence: {scan_data.get('confidence_score', 0)}%
Symptoms Identified: {', '.join(scan_data.get('analysis_result', {}).get('symptoms', []))}
Red Flags: {', '.join(scan_data.get('analysis_result', {}).get('redFlags', []))}

RECOMMENDATIONS:
Immediate Actions: {', '.join(scan_data.get('analysis_result', {}).get('immediateActions', []))}
Self Care: {', '.join(scan_data.get('analysis_result', {}).get('selfCare', []))}
Seek Care If: {', '.join(scan_data.get('analysis_result', {}).get('seekCareIf', []))}"""

    # Generate enhanced summary
    summary_prompt = f"""Based on this quick scan assessment, create a brief medical summary that could be useful for future reference. Include:
1. Key findings and primary concerns
2. Symptom characteristics
3. Risk factors or red flags
4. Recommended actions
5. Follow-up considerations

{scan_context}"""

    llm_response = await call_llm(
        messages=[
            {"role": "system", "content": "You are a medical AI creating a clinical summary."},
            {"role": "user", "content": summary_prompt}
        ],
        model="deepseek/deepseek-chat",
        user_id=user_id,
        temperature=0.3,
        max_tokens=500
    )
    
    summary_content = llm_response.get("content", "")
    
    if not summary_content:
        raise ValueError("Failed to generate summary from LLM")
    
    # Save summary to llm_context
    summary_data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "quick_scan_id": quick_scan_id,
        "summary": summary_content,
        "context_type": "quick_scan_summary",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "token_count": count_tokens(summary_content),
        "metadata": {
            "body_part": scan_data.get('body_part'),
            "primary_condition": scan_data.get('analysis_result', {}).get('primaryCondition'),
            "confidence_score": scan_data.get('confidence_score')
        },
        "model_used": "deepseek/deepseek-chat"
    }
    
    insert_response = supabase.table("llm_context").insert(summary_data).execute()
    
    if not insert_response.data:
        print(f"Failed to save summary: {insert_response}")
        raise ValueError("Failed to save summary to database")
    
    print(f"Quick scan summary saved with ID: {summary_data['id']}")
    return summary_content