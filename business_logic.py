from supabase_client import supabase
from typing import Optional, List
import os
from dotenv import load_dotenv
import json
import asyncio
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.model_selector import get_models_for_endpoint, select_model_with_fallback
from utils.token_counter import count_tokens
from utils.async_http import make_async_post_with_retry

# Load .env file
load_dotenv()

def make_prompt(query: str, user_data: dict, llm_context: str, category: str, part_selected: Optional[str] = None, region: Optional[str] = None) -> str:
    """Generate contextual prompts based on category and parameters."""
    
    # Helper function to load and format prompt from file
    def load_prompt_template(file_path: str) -> str:
        """Load a prompt template from file."""
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: Prompt file not found: {file_path}")
            return None
    
    # Base directory for prompts
    prompts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts', 'medical')
    
    if category == "health-scan":
        template = load_prompt_template(os.path.join(prompts_dir, 'health_scan.txt'))
        if template:
            return template.format(
                query=query,
                user_data=user_data,
                llm_context=llm_context,
                part_selected=part_selected if part_selected else "General discussion",
                region=region if region else "Not specified"
            )
        # Fallback to inline prompt if file not found
        return f"Category: {category}\nUser Query: {query}\nContext: {llm_context}"
    
    elif category == "quick-scan":
        # Extract form data if passed in user_data
        form_data = user_data.get('form_data', {}) if isinstance(user_data, dict) else {}
        body_part = part_selected or user_data.get('body_part', 'General')
        
        template = load_prompt_template(os.path.join(prompts_dir, 'quick_scan.txt'))
        if template:
            return template.format(
                body_part=body_part,
                form_data=json.dumps(form_data) if form_data else 'Not provided',
                query=query,
                llm_context=llm_context if llm_context else 'None - new user or anonymous'
            )
        # Fallback
        return f"Quick scan for {body_part}: {query}"
    
    elif category == "deep-dive":
        # Generic deep dive - use basic format
        base_prompt = f"Category: {category}\nUser Query: {query}\n"
        base_prompt += f"Comprehensive Analysis Request\n"
        base_prompt += f"LLM Context: {llm_context}\n"
        if region:
            base_prompt += f"Deep Analysis Region: {region}\n"
        if part_selected:
            base_prompt += f"Selected Part: {part_selected}\n"
        base_prompt += "Provide detailed, comprehensive analysis."
        return base_prompt
    
    elif category == "deep-dive-initial":
        # Extract form data if passed in user_data
        form_data = user_data.get('form_data', {}) if isinstance(user_data, dict) else {}
        body_part = part_selected or user_data.get('body_part', 'General')
        medical_data = user_data.get('medical_data', {}) if isinstance(user_data, dict) else {}
        
        template = load_prompt_template(os.path.join(prompts_dir, 'deep_dive', 'initial.txt'))
        if template:
            return template.format(
                body_part=body_part,
                query=query,
                form_data=json.dumps(form_data) if form_data else 'Not provided',
                medical_data=str(medical_data)[:200] + '...' if medical_data else 'Not available',
                llm_context=llm_context if llm_context else 'New patient'
            )
        # Fallback
        return f"Deep dive initial for {body_part}: {query}"
    
    elif category == "deep-dive-continue":
        # For continuing deep dive with previous Q&A
        session_data = user_data.get('session_data', {}) if isinstance(user_data, dict) else {}
        medical_data = user_data.get('medical_data', {}) if isinstance(user_data, dict) else {}
        
        # Add medical context if available
        medical_context = ""
        if medical_data and medical_data not in [{}, None]:
            medical_context = f"\n- Medical History: {str(medical_data)[:200]}..."
        
        template = load_prompt_template(os.path.join(prompts_dir, 'deep_dive', 'continue.txt'))
        if template:
            return template.format(
                questions=json.dumps(session_data.get('questions', [])),
                internal_state=json.dumps(session_data.get('internal_state', {})),
                medical_context=medical_context,
                query=query
            )
        # Fallback
        return f"Deep dive continue: {query}"
    
    elif category == "deep-dive-final":
        # Final analysis after Q&A
        session_data = user_data.get('session_data', {}) if isinstance(user_data, dict) else {}
        medical_data = session_data.get('medical_data', {})
        
        template = load_prompt_template(os.path.join(prompts_dir, 'deep_dive', 'final.txt'))
        if template:
            return template.format(
                questions=json.dumps(session_data.get('questions', [])),
                form_data=json.dumps(session_data.get('form_data', {})),
                medical_data=str(medical_data)[:200] + '...' if medical_data else 'Not available',
                llm_context=llm_context if llm_context else 'New patient'
            )
        # Fallback
        return f"Deep dive final analysis"
    
    else:
        # Default case for any other category
        base_prompt = f"Category: {category}\nUser Query: {query}\n"
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

async def call_llm_with_fallback(
    messages: list,
    user_id: Optional[str] = None,
    endpoint_type: Optional[str] = None,
    reasoning_mode: bool = False,
    **kwargs
) -> dict:
    """Call LLM with automatic fallback to secondary models if primary fails"""
    
    # Get all available models for this endpoint
    models = None
    if user_id and endpoint_type:
        models = await get_models_for_endpoint(user_id, endpoint_type, reasoning_mode)
    
    if not models:
        # Fallback to single model
        return await call_llm(messages=messages, user_id=user_id, reasoning_mode=reasoning_mode, endpoint_type=endpoint_type, **kwargs)
    
    # Try each model in order
    last_error = None
    for i, model in enumerate(models):
        try:
            print(f"Trying model: {model}")
            result = await call_llm(
                messages=messages,
                model=model,
                user_id=user_id,
                reasoning_mode=reasoning_mode,
                endpoint_type=endpoint_type,
                **kwargs
            )
            
            # Check if we got a valid response
            if result and result.get("choices") and len(result["choices"]) > 0 and result["choices"][0].get("message"):
                print(f"Success with model: {model}")
                return result
                
        except Exception as e:
            print(f"Model {model} failed: {e}")
            last_error = e
            if i < len(models) - 1:
                print(f"Trying fallback model {i+2}/{len(models)}")
            continue
    
    # All models failed
    print(f"All models failed. Last error: {last_error}")
    raise Exception(f"All models failed. Last error: {last_error}")

async def call_llm(
    messages: list, 
    model: Optional[str] = None, 
    user_id: Optional[str] = None, 
    reasoning_mode: bool = False,
    endpoint_type: Optional[str] = None,
    temperature: float = 0.7, 
    max_tokens: int = 2048, 
    top_p: float = 1.0
) -> dict:
    """Call the LLM via OpenRouter with tier-based model selection and reasoning support"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in .env file")

    # Get tier-based model if not provided
    if not model:
        if user_id and endpoint_type:
            # Use new tier-based selection
            model = await select_model_with_fallback(
                user_id=user_id,
                endpoint=endpoint_type,
                reasoning_mode=reasoning_mode,
                preferred_index=0
            )
        elif user_id:
            # Fallback to old method
            model = await get_user_model(user_id)
        
        if not model:
            model = "deepseek/deepseek-chat"  # Ultimate fallback

    # Adjust parameters for reasoning mode or specific endpoints
    request_params = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
    }
    
    # Handle reasoning models and high-reasoning endpoints
    if reasoning_mode or endpoint_type in ["deep_dive", "reports", "health_analysis", "ultra_think"]:
        if "o1" in model or "gpt-5" in model:
            # Use max_completion_tokens for o1/GPT-5 models
            request_params["max_completion_tokens"] = 8000  # Allow up to 8k, model uses what it needs
        elif "deepseek-r1" in model:
            # Use OpenRouter's standardized reasoning parameter for DeepSeek R1
            request_params["reasoning"] = {
                "effort": "high"  # High effort for detailed reasoning (no max_tokens when using effort)
            }
            request_params["max_tokens"] = 8000  # Overall max tokens
        elif "claude" in model.lower():
            # Claude models support reasoning parameter
            # IMPORTANT: max_tokens must be strictly higher than reasoning budget
            # For Claude, we use max_tokens approach for precise control
            request_params["reasoning"] = {
                "max_tokens": 4000  # Direct specification of reasoning token budget
            }
            request_params["max_tokens"] = 6000  # Must be > reasoning.max_tokens (4000)
        elif "grok" in model:
            # Grok models for ultra thinking
            request_params["reasoning"] = {
                "effort": "high"  # Use effort-based approach
            }
            request_params["max_tokens"] = 12000  # Higher for Grok
            request_params["temperature"] = 0.3  # Lower for focused reasoning
        else:
            # Other models with reasoning support
            request_params["reasoning"] = {
                "effort": "medium"  # Use effort-based approach
            }
            request_params["max_tokens"] = 6000  # Higher limit, model uses what it needs
            request_params["temperature"] = 0.3  # Lower for focused reasoning
    else:
        # Standard completion (no reasoning)
        request_params["max_tokens"] = max_tokens
    
    # Debug logging for reasoning mode
    if reasoning_mode:
        print(f"=== REQUEST PARAMS DEBUG ===")
        print(f"Model: {model}")
        print(f"Request params: {json.dumps(request_params, indent=2)}")
    
    # Build headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Add provider API keys for BYOK (Bring Your Own Key)
    if model:
        # OpenAI models (GPT-5, GPT-4, etc.)
        if "gpt-" in model.lower() or "o1-" in model.lower():
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                headers["X-API-Key"] = openai_key
                print(f"Using OpenAI API key for {model}")
        
        # Anthropic models (Claude)
        elif "claude" in model.lower():
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if anthropic_key:
                headers["X-API-Key"] = anthropic_key
                print(f"Using Anthropic API key for {model}")
            else:
                print(f"No Anthropic API key found for {model}, using OpenRouter credits")
    
    # Final debug before sending
    if reasoning_mode:
        print(f"=== FINAL REQUEST TO OPENROUTER ===")
        print(f"Headers: {headers}")
        print(f"Request JSON: {json.dumps(request_params, indent=2)}")
    
    # Use async HTTP client with connection pooling and retry
    try:
        data = await make_async_post_with_retry(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json_data=request_params,
            max_retries=3,
            timeout=240  # 4 minutes for reasoning models
        )
    except Exception as e:
        print(f"Request exception: {str(e)}")
        # Return mock response as fallback
        data = {
            "choices": [{
                "message": {
                    "content": "I understand your query. (Note: Using fallback response due to connection issue)"
                },
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        }
    
    # Debug logging to see exact response structure
    if reasoning_mode:
        print(f"=== REASONING MODE RESPONSE DEBUG ===")
        print(f"Model: {model}")
        if "choices" in data and len(data["choices"]) > 0:
            message_keys = data["choices"][0].get("message", {}).keys()
            print(f"Message keys: {list(message_keys)}")
            if "reasoning" in data["choices"][0].get("message", {}):
                reasoning_preview = data["choices"][0]["message"]["reasoning"]
                print(f"Reasoning found! Length: {len(reasoning_preview) if reasoning_preview else 0} chars")
                if reasoning_preview:
                    print(f"Reasoning preview: {reasoning_preview[:200]}...")
            else:
                print("No reasoning field in message")
    
    # Extract reasoning if present
    reasoning_content = None
    reasoning_tokens = 0
    content = data["choices"][0]["message"]["content"].strip()
    
    # Check if reasoning is in the response
    if "choices" in data and len(data["choices"]) > 0:
        choice = data["choices"][0]
        if "message" in choice:
            # Check for reasoning field (Claude 3.7, DeepSeek R1, etc.)
            if "reasoning" in choice["message"] and choice["message"]["reasoning"]:
                reasoning_content = choice["message"]["reasoning"]
                # Count reasoning tokens (since OpenRouter includes them in completion_tokens)
                reasoning_tokens = count_tokens(reasoning_content) if reasoning_content else 0
                print(f"✅ Extracted reasoning: {len(reasoning_content) if reasoning_content else 0} chars, ~{reasoning_tokens} tokens")
            
            # Also check for reasoning_details (Claude 3.7 format)
            if "reasoning_details" in choice["message"] and not reasoning_content:
                details = choice["message"]["reasoning_details"]
                if details and len(details) > 0 and "text" in details[0]:
                    reasoning_content = details[0]["text"]
                    reasoning_tokens = count_tokens(reasoning_content) if reasoning_content else 0
                    print(f"✅ Extracted reasoning from details: {len(reasoning_content)} chars, ~{reasoning_tokens} tokens")
    
    # Also check for reasoning tokens in usage details (OpenRouter format)
    if "usage" in data and "completion_tokens_details" in data["usage"]:
        if "reasoning_tokens" in data["usage"]["completion_tokens_details"]:
            reported_reasoning_tokens = data["usage"]["completion_tokens_details"]["reasoning_tokens"]
            if reported_reasoning_tokens > 0:
                reasoning_tokens = reported_reasoning_tokens
                print(f"OpenRouter reported {reasoning_tokens} reasoning tokens")
    
    # Try to parse as JSON if it looks like JSON
    parsed_content = content
    try:
        if content.startswith('{') or content.startswith('['):
            parsed_content = json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Build enhanced usage info
    usage = data.get("usage", {})
    
    # Pass through completion_tokens_details if present (contains reasoning_tokens for DeepSeek)
    if "completion_tokens_details" in data.get("usage", {}):
        usage["completion_tokens_details"] = data["usage"]["completion_tokens_details"]
    
    if reasoning_tokens > 0:
        # Add reasoning_tokens to usage (these are included in completion_tokens)
        usage["reasoning_tokens"] = reasoning_tokens
        # Calculate actual response tokens (completion minus reasoning)
        usage["response_tokens"] = usage.get("completion_tokens", 0) - reasoning_tokens
    
    # Return full response data in OpenRouter format with reasoning
    return {
        "choices": [{
            "message": {
                "content": content,
                "reasoning": reasoning_content  # Include reasoning in message
            },
            "finish_reason": data["choices"][0].get("finish_reason", "stop")
        }],
        "usage": usage,
        "model": model,
        "reasoning": reasoning_content,  # Top-level reasoning for easy access
        "has_reasoning": bool(reasoning_content),  # Flag for frontend
        # Keep these for backward compatibility
        "content": parsed_content,
        "raw_content": content
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

# Message storage removed - backend no longer stores messages to Supabase

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
        # System message storage removed - messages are no longer saved
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

# Conversation timestamp updates removed - backend no longer tracks conversation metadata

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