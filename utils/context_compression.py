"""Context compression utilities for managing conversation token limits"""
import re
from typing import List, Dict, Any, Optional
from utils.token_counter import count_tokens
import os
from utils.async_http import make_async_post_with_retry
from dotenv import load_dotenv

load_dotenv()

# Token limits by tier
PREMIUM_TOKEN_LIMIT = 200000  # Premium users get 200k
FREE_TOKEN_LIMIT = 100000      # Free users get 100k - HARD STOP
AGGRESSIVE_COMPRESSION_LIMIT = 250000  # When to use aggressive compression for premium

# Medical keywords to preserve
URGENT_KEYWORDS = [
    'emergency', 'urgent', 'severe', 'critical', 'immediate',
    'hospital', 'ER', '911', 'chest pain', 'difficulty breathing',
    'stroke', 'heart attack', 'bleeding', 'unconscious', 'seizure'
]

MEDICATION_KEYWORDS = [
    'medication', 'medicine', 'drug', 'prescription', 'dosage',
    'mg', 'ml', 'daily', 'twice', 'allergic', 'allergy',
    'side effect', 'interaction'
]

def has_urgent_keywords(message: Dict[str, Any]) -> bool:
    """Check if message contains urgent medical keywords"""
    content = message.get('content', '').lower()
    return any(keyword in content for keyword in URGENT_KEYWORDS)

def has_medication_keywords(message: Dict[str, Any]) -> bool:
    """Check if message contains medication-related keywords"""
    content = message.get('content', '').lower()
    return any(keyword in content for keyword in MEDICATION_KEYWORDS)

def is_ai_recommendation(message: Dict[str, Any]) -> bool:
    """Check if message is an AI recommendation or diagnosis"""
    if message.get('role') != 'assistant':
        return False
    
    content = message.get('content', '').lower()
    recommendation_patterns = [
        'recommend', 'suggest', 'should', 'consider',
        'diagnosis', 'assessment', 'likely', 'appears to be',
        'treatment', 'next steps', 'follow up'
    ]
    return any(pattern in content for pattern in recommendation_patterns)

def extract_medical_flags(messages: List[Dict[str, Any]]) -> List[str]:
    """Extract medical flags from conversation"""
    flags = set()
    
    for message in messages:
        content = message.get('content', '').lower()
        
        # Check for medications discussed
        if any(med in content for med in ['medication', 'prescription', 'drug']):
            flags.add('prescription_discussed')
        
        # Check for symptoms tracked
        if any(symptom in content for symptom in ['pain', 'fever', 'nausea', 'headache']):
            flags.add('symptoms_tracked')
        
        # Check for urgency
        if has_urgent_keywords(message):
            flags.add('urgent_care_mentioned')
        
        # Check for follow-up needed
        if 'follow up' in content or 'appointment' in content:
            flags.add('followup_recommended')
        
        # Check for test results
        if any(test in content for test in ['test', 'lab', 'scan', 'x-ray', 'mri']):
            flags.add('tests_discussed')
    
    return list(flags)

async def generate_medical_summary(messages: List[Dict[str, Any]], max_tokens: int = 500) -> str:
    """Generate a medical-focused summary of messages"""
    # Build conversation text
    conversation_text = "\n".join([
        f"{msg['role']}: {msg['content'][:500]}"
        for msg in messages
    ])
    
    prompt = f"""Summarize this medical conversation focusing on:
1. Initial complaint/symptoms
2. Key medical information discussed
3. Medications mentioned
4. Recommendations given
5. Any urgent concerns

Keep it under {max_tokens} tokens.

Conversation:
{conversation_text[:3000]}

Medical Summary:"""
    
    try:
        api_key = os.getenv("OPENROUTER_API_KEY")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        json_data = {
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "system", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3
        }
        
        # Use async HTTP client
        result = await make_async_post_with_retry(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json_data=json_data,
            timeout=30
        )
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error generating summary: {e}")
        return f"Unable to generate summary. Conversation has {len(messages)} messages."

async def compress_medical_context(messages: List[Dict[str, Any]], target_tokens: int = 30000) -> List[Dict[str, Any]]:
    """Intelligently compress conversation while preserving medical context"""
    if not messages:
        return []
    
    preserved = []
    
    # Always keep first 3 messages (original complaint)
    preserved.extend(messages[:3] if len(messages) >= 3 else messages)
    
    # Find and keep urgent messages
    urgent_messages = [msg for msg in messages[3:-10] if has_urgent_keywords(msg)]
    preserved.extend(urgent_messages)
    
    # Find and keep medication-related messages
    medication_messages = [msg for msg in messages[3:-10] if has_medication_keywords(msg)]
    preserved.extend(medication_messages)
    
    # Find and keep AI recommendations
    ai_recommendations = [msg for msg in messages[3:-10] if is_ai_recommendation(msg)]
    preserved.extend(ai_recommendations)
    
    # Generate summary of excluded messages
    excluded = [msg for msg in messages[3:-10] 
                if msg not in preserved 
                and msg not in urgent_messages 
                and msg not in medication_messages 
                and msg not in ai_recommendations]
    
    if excluded:
        summary = await generate_medical_summary(excluded)
        preserved.append({
            "role": "system",
            "content": f"[Previous conversation summary: {summary}]"
        })
    
    # Always keep last 10 messages for recent context
    if len(messages) > 10:
        preserved.extend(messages[-10:])
    
    # Remove duplicates while preserving order
    seen = set()
    deduplicated = []
    for msg in preserved:
        msg_id = f"{msg.get('role')}:{msg.get('content', '')[:100]}"
        if msg_id not in seen:
            seen.add(msg_id)
            deduplicated.append(msg)
    
    # Sort by original order
    deduplicated.sort(key=lambda x: messages.index(x) if x in messages else -1)
    
    return deduplicated

async def free_tier_context(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create limited context for free tier users"""
    if len(messages) <= 15:
        return messages
    
    # Generate brief summary of older messages
    summary = await generate_medical_summary(messages[:-10], max_tokens=300)
    
    context_messages = [
        {
            "role": "system",
            "content": f"Medical history summary: {summary}"
        }
    ]
    
    # Add last 10 messages
    context_messages.extend(messages[-10:])
    
    return context_messages

async def generate_medical_title(messages: List[Dict[str, Any]]) -> str:
    """Generate a medical-focused conversation title"""
    # Use first few messages to generate title
    conversation_start = "\n".join([
        f"{msg['role']}: {msg['content'][:200]}"
        for msg in messages[:6]
    ])
    
    prompt = f"""Generate a brief, descriptive title (3-7 words) for this medical conversation:

{conversation_start}

Title:"""
    
    try:
        api_key = os.getenv("OPENROUTER_API_KEY")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        json_data = {
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "system", "content": prompt}],
            "max_tokens": 20,
            "temperature": 0.5
        }
        
        # Use async HTTP client
        result = await make_async_post_with_retry(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json_data=json_data,
            timeout=10
        )
        title = result["choices"][0]["message"]["content"].strip()
        # Clean up the title
        title = title.replace('"', '').replace("'", '').strip()
        return title[:100]  # Limit length
    except Exception as e:
        print(f"Error generating title: {e}")
        return "Health Discussion"

def calculate_context_status(messages: List[Dict[str, Any]], is_premium: bool) -> Dict[str, Any]:
    """Calculate the context status for a conversation"""
    total_tokens = count_tokens(str(messages))
    
    if is_premium:
        if total_tokens < PREMIUM_TOKEN_LIMIT:
            return {
                "status": "within_limits",
                "can_continue": True,
                "needs_compression": False,
                "tokens": total_tokens,
                "limit": PREMIUM_TOKEN_LIMIT,
                "percentage": (total_tokens / PREMIUM_TOKEN_LIMIT) * 100
            }
        elif total_tokens < AGGRESSIVE_COMPRESSION_LIMIT:
            return {
                "status": "compressed",
                "can_continue": True,
                "needs_compression": True,
                "tokens": total_tokens,
                "limit": PREMIUM_TOKEN_LIMIT,
                "percentage": (total_tokens / PREMIUM_TOKEN_LIMIT) * 100,
                "notice": "Using intelligent compression to extend conversation"
            }
        else:
            return {
                "status": "aggressive_compression",
                "can_continue": True,
                "needs_compression": True,
                "tokens": total_tokens,
                "limit": PREMIUM_TOKEN_LIMIT,
                "percentage": (total_tokens / PREMIUM_TOKEN_LIMIT) * 100,
                "notice": "Maximum compression active. Consider starting a new conversation soon."
            }
    else:  # Free tier
        if total_tokens < FREE_TOKEN_LIMIT:
            return {
                "status": "within_limits",
                "can_continue": True,
                "needs_compression": False,
                "tokens": total_tokens,
                "limit": FREE_TOKEN_LIMIT,
                "percentage": (total_tokens / FREE_TOKEN_LIMIT) * 100
            }
        else:
            # FREE USERS BLOCKED AT 100k
            return {
                "status": "blocked",
                "can_continue": False,  # HARD STOP
                "needs_compression": False,
                "tokens": total_tokens,
                "limit": FREE_TOKEN_LIMIT,
                "percentage": 100,
                "upgrade_prompt": {
                    "title": "🚫 Conversation Limit Reached",
                    "description": "You've reached the maximum conversation length for free users (100k tokens).",
                    "benefits": [
                        "📈 2X larger conversations (200k tokens)",
                        "🧠 Intelligent compression for even longer chats",
                        "💬 Never lose conversation context",
                        "🔄 Continue conversations indefinitely"
                    ],
                    "cta": "Upgrade to Continue - $9.99/month"
                }
            }