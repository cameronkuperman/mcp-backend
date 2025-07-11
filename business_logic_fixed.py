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
- **Previous Conversations Summary:** {llm_context}
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
        base_prompt += f"Quick Analysis Request\n"
        if region:
            base_prompt += f"Focus Region: {region}\n"
        if part_selected:
            base_prompt += f"Selected Part: {part_selected}\n"
        base_prompt += f"LLM Context: {llm_context}\n"
        base_prompt += "Provide rapid assessment and recommendations."
    
    elif category == "deep-dive":
        base_prompt += f"Comprehensive Analysis Request\n"
        base_prompt += f"LLM Context: {llm_context}\n"
        if region:
            base_prompt += f"Deep Analysis Region: {region}\n"
        if part_selected:
            base_prompt += f"Selected Part: {part_selected}\n"
        base_prompt += "Provide detailed, comprehensive analysis."
    
    else:
        base_prompt += f"General query\n"
        base_prompt += f"Context: {llm_context}\n"
        if part_selected:
            base_prompt += f"Selected: {part_selected}\n"
        if region:
            base_prompt += f"Region: {region}\n"
    
    return base_prompt

async def get_user_data(user_id: str) -> dict:
    """Get the user data."""
    return {"user_id": user_id}

async def get_llm_context(user_id: str) -> str:
    """Get the LLM context."""
    return "The LLM context is the context for the LLM."

async def get_user_model(user_id: str) -> str:
    """Fetch user's preferred model from Supabase, default to free one."""
    response = supabase.table("users").select("preferred_model").eq("id", user_id).execute()
    if response.data and response.data[0].get("preferred_model"):
        return response.data[0]["preferred_model"]
    return "openai/gpt-3.5-turbo"  # Use a reliable model

async def call_llm(messages: list, model: Optional[str] = None, user_id: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 2048, top_p: float = 1.0) -> dict:
    """Call the LLM via OpenRouter using requests (more reliable)."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in .env file")

    # Fetch model if not provided
    if not model and user_id:
        model = await get_user_model(user_id)
    elif not model:
        model = "openai/gpt-3.5-turbo"

    # Make the request using requests library (runs in thread pool)
    def make_request():
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": os.getenv("APP_URL", "http://localhost:3000"),
            "X-Title": "Medical Chat API",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }
        
        try:
            response = requests.post(
                "https://api.openrouter.ai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code != 200:
                raise ValueError(f"OpenRouter API error: {response.status_code} - {response.text}")
            
            return response.json()
        except Exception as e:
            raise ValueError(f"Request failed: {str(e)}")
    
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

async def build_messages_for_llm(conversation_id: str, new_query: str, category: str, user_data: dict) -> list:
    """Build message array for LLM including history."""
    messages = []
    existing_messages = await get_conversation_messages(conversation_id)
    
    if not existing_messages:
        # First message - add system prompt
        system_prompt = make_prompt(new_query, user_data, "", category)
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