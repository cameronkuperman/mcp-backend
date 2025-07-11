from fastmcp import FastMCP
from business_logic import (
    make_prompt, get_user_data, get_llm_context, 
    call_llm, update_chat_history, get_chat_history,
    llm_prompt_for_summary
)
from supabase_client import supabase

# Create FastMCP instance
mcp = FastMCP("mcp-backend")

@mcp.tool
async def oracle_query(query: str, user_id: str, conversation_id: str, model: str = None) -> str:
    """
    Query the oracle - MCP tool for Claude Desktop with proper conversation handling.
    """
    from business_logic import build_messages_for_llm, store_message, update_conversation_timestamp
    
    # Get user data
    user_data = await get_user_data(user_id)
    
    # Build messages array - this handles checking for existing messages!
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
    
    # Call LLM with the full message history
    llm_response = await call_llm(messages, model=model, user_id=user_id)
    
    # Extract response content
    if isinstance(llm_response["content"], dict):
        import json
        response_text = json.dumps(llm_response["content"])
    else:
        response_text = llm_response["content"]
    
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
    
    return response_text

@mcp.tool
async def health_scan_query(query: str, user_id: str, part_selected: str = None, region: str = None) -> str:
    """
    Health scan analysis - MCP tool for medical queries.
    """
    user_data = await get_user_data(user_id)
    llm_context = await get_llm_context(user_id)
    
    prompt = make_prompt(
        query=query,
        user_data=user_data,
        llm_context=llm_context,
        category="health-scan",
        part_selected=part_selected,
        region=region
    )
    
    # Convert to messages format
    messages = [{"role": "system", "content": prompt}]
    llm_response = await call_llm(messages, user_id=user_id)
    
    if isinstance(llm_response["content"], dict):
        import json
        return json.dumps(llm_response["content"])
    return llm_response["content"]

@mcp.tool
async def quick_scan_query(query: str, user_id: str, region: str = None) -> str:
    """
    Quick scan analysis - MCP tool for rapid medical assessment.
    """
    user_data = await get_user_data(user_id)
    llm_context = await get_llm_context(user_id)
    
    prompt = make_prompt(
        query=query,
        user_data=user_data,
        llm_context=llm_context,
        category="quick-scan",
        region=region
    )
    
    # Convert to messages format
    messages = [{"role": "system", "content": prompt}]
    llm_response = await call_llm(messages, user_id=user_id)
    
    if isinstance(llm_response["content"], dict):
        import json
        return json.dumps(llm_response["content"])
    return llm_response["content"]

@mcp.tool
async def create_llm_summary(conversation_id: str, user_id: str) -> str:
    """
    Create an LLM summary of the conversation.
    """
    # Get conversation history
    from business_logic import get_conversation_messages
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
    llm_response = await call_llm(summary_messages, user_id=user_id, max_tokens=500)
    summary = llm_response["content"] if isinstance(llm_response["content"], str) else str(llm_response["content"])
    
    # Store summary
    existing = supabase.table("summaries").select("*").eq("conversation_id", conversation_id).execute()
    if existing.data:
        supabase.table("summaries").update({"summary": summary}).eq("conversation_id", conversation_id).execute()
    else:
        supabase.table("summaries").insert({"conversation_id": conversation_id, "user_id": user_id, "summary": summary}).execute()
    
    return summary

@mcp.tool
async def deep_dive_query(query: str, user_id: str, part_selected: str = None, region: str = None) -> str:
    """
    Deep dive analysis - MCP tool for comprehensive medical analysis.
    """
    user_data = await get_user_data(user_id)
    llm_context = await get_llm_context(user_id)
    
    prompt = make_prompt(
        query=query,
        user_data=user_data,
        llm_context=llm_context,
        category="deep-dive",
        part_selected=part_selected,
        region=region
    )
    
    # Convert to messages format
    messages = [{"role": "system", "content": prompt}]
    llm_response = await call_llm(messages, user_id=user_id)
    
    if isinstance(llm_response["content"], dict):
        import json
        return json.dumps(llm_response["content"])
    return llm_response["content"]