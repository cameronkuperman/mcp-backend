from fastmcp import FastMCP
from business_logic import (
    get_user_data, call_llm,
    build_messages_for_llm, store_message, update_conversation_timestamp,
    get_conversation_messages
)
import json

# Create FastMCP instance
mcp = FastMCP("mcp-backend")

@mcp.tool
async def oracle_query(query: str, user_id: str, conversation_id: str, model: str = None) -> str:
    """
    Query the oracle - MCP tool for health conversations with history management.
    Returns the response which can be plain text or JSON.
    """
    # Get user data
    user_data = await get_user_data(user_id)
    
    # Build messages array (handles new vs existing conversation)
    messages = await build_messages_for_llm(
        conversation_id=conversation_id,
        new_query=query,
        category="health-scan",
        user_data=user_data
    )
    
    # Store user message
    await store_message(
        conversation_id=conversation_id,
        role="user",
        content=query,
        token_count=len(query.split())
    )
    
    # Call LLM
    llm_response = await call_llm(
        messages=messages,
        model=model,
        user_id=user_id
    )
    
    # Store assistant response
    await store_message(
        conversation_id=conversation_id,
        role="assistant",
        content=llm_response["raw_content"],
        token_count=llm_response["usage"].get("completion_tokens", 0),
        model_used=llm_response["model"],
        metadata={
            "finish_reason": llm_response["finish_reason"],
            "total_tokens": llm_response["usage"].get("total_tokens", 0)
        }
    )
    
    # Update conversation metadata
    await update_conversation_timestamp(conversation_id, llm_response["raw_content"])
    
    # Return content (could be JSON if LLM returned structured data)
    if isinstance(llm_response["content"], dict):
        return json.dumps(llm_response["content"])
    return llm_response["content"]

@mcp.tool
async def create_llm_summary(conversation_id: str, user_id: str) -> str:
    """
    Create an LLM summary of the conversation for quick context.
    """
    # Get all messages in conversation
    messages = await get_conversation_messages(conversation_id)
    
    if not messages:
        return "No messages found in conversation."
    
    # Build summary prompt
    conversation_text = "\n".join([f"{msg['role']}: {msg['content'][:200]}..." 
                                   for msg in messages[-10:]])  # Last 10 messages
    
    summary_messages = [
        {"role": "system", "content": "Summarize the following medical conversation concisely, focusing on key symptoms, diagnoses discussed, and recommendations made."},
        {"role": "user", "content": f"Conversation:\n{conversation_text}\n\nProvide a brief summary."}
    ]
    
    # Call LLM for summary
    llm_response = await call_llm(
        messages=summary_messages,
        user_id=user_id,
        max_tokens=500
    )
    
    return llm_response["content"]

@mcp.tool
async def get_structured_response(query: str, user_id: str, response_format: str) -> str:
    """
    Get a structured response from the LLM in a specific format.
    response_format can be: 'confidence_levels', 'symptom_checklist', 'risk_assessment'
    """
    formats = {
        "confidence_levels": {
            "system": "You are a medical AI. Respond ONLY with valid JSON containing confidence levels.",
            "format": """{"diagnosis_confidence": 0.0-1.0, "symptom_match": 0.0-1.0, "urgency_level": "low|medium|high", "recommendation": "string"}"""
        },
        "symptom_checklist": {
            "system": "You are a medical AI. Respond ONLY with valid JSON containing a symptom checklist.",
            "format": """{"symptoms": [{"name": "string", "present": true/false, "severity": 1-10}], "total_symptoms": int}"""
        },
        "risk_assessment": {
            "system": "You are a medical AI. Respond ONLY with valid JSON containing risk assessment.",
            "format": """{"risk_level": "low|moderate|high", "risk_factors": ["string"], "protective_factors": ["string"], "recommendations": ["string"]}"""
        }
    }
    
    if response_format not in formats:
        return json.dumps({"error": f"Unknown format: {response_format}"})
    
    format_info = formats[response_format]
    messages = [
        {"role": "system", "content": f"{format_info['system']}\nExpected format: {format_info['format']}"},
        {"role": "user", "content": query}
    ]
    
    llm_response = await call_llm(
        messages=messages,
        user_id=user_id,
        temperature=0.3  # Lower temperature for structured output
    )
    
    # Return the response (already parsed as JSON if valid)
    if isinstance(llm_response["content"], dict):
        return json.dumps(llm_response["content"])
    return llm_response["content"]