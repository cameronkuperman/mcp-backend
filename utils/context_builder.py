"""Context building utilities for Oracle chat"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from supabase_client import supabase
from utils.token_counter import count_tokens
import requests
import os

async def get_enhanced_llm_context(user_id: str, conversation_id: str, current_query: str = "") -> str:
    """Build comprehensive context from summaries, quick scans, and deep dives"""
    context_parts = []
    
    try:
        # 1. Get LLM summaries from previous conversations
        summaries_response = supabase.table("llm_context")\
            .select("llm_summary, created_at, context_type")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(5)\
            .execute()
        
        if summaries_response.data:
            context_parts.append("=== Previous Health Discussions ===")
            for summary in summaries_response.data[:3]:  # Use top 3 most recent
                date = summary['created_at'][:10] if summary.get('created_at') else 'Unknown date'
                context_type = summary.get('context_type', 'conversation')
                context_parts.append(f"\n[{date} - {context_type}]")
                context_parts.append(summary.get('llm_summary', '')[:500])  # Limit each summary
        
        # 2. Get recent quick scans (last 30 days)
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        scans_response = supabase.table("quick_scans")\
            .select("created_at, body_part, analysis_result, form_data")\
            .eq("user_id", str(user_id))\
            .gte("created_at", cutoff_date)\
            .order("created_at", desc=True)\
            .limit(5)\
            .execute()
        
        if scans_response.data:
            context_parts.append("\n\n=== Recent Health Scans ===")
            for scan in scans_response.data[:3]:  # Use top 3 most recent
                date = scan['created_at'][:10]
                body_part = scan.get('body_part', 'Unknown')
                symptoms = scan.get('form_data', {}).get('symptoms', 'No symptoms recorded')
                condition = scan.get('analysis_result', {}).get('primaryCondition', 'Unknown condition')
                context_parts.append(f"\n[{date} - {body_part}] {symptoms} → Assessed as: {condition}")
        
        # 3. Get recent deep dives (last 30 days)
        dives_response = supabase.table("deep_dive_sessions")\
            .select("created_at, body_part, final_analysis, final_confidence")\
            .eq("user_id", str(user_id))\
            .eq("status", "completed")\
            .gte("created_at", cutoff_date)\
            .order("created_at", desc=True)\
            .limit(3)\
            .execute()
        
        if dives_response.data:
            context_parts.append("\n\n=== Deep Health Analyses ===")
            for dive in dives_response.data[:2]:  # Use top 2 most recent
                date = dive['created_at'][:10]
                body_part = dive.get('body_part', 'Unknown')
                condition = dive.get('final_analysis', {}).get('primaryCondition', 'Unknown')
                confidence = dive.get('final_confidence', 0)
                context_parts.append(f"\n[{date} - {body_part}] Deep analysis: {condition} (confidence: {confidence}%)")
        
        # 4. Get current conversation summary if exists
        current_summary = supabase.table("llm_context")\
            .select("summary")\
            .eq("user_id", user_id)\
            .eq("conversation_id", conversation_id)\
            .execute()
        
        if current_summary.data:
            context_parts.append("\n\n=== Current Conversation Context ===")
            context_parts.append(current_summary.data[0].get('summary', '')[:500])
        
        # Join all context parts
        full_context = "\n".join(context_parts)
        
        # Check if we need to compress
        total_tokens = count_tokens(full_context)
        if total_tokens > 2000:  # Keep context reasonable
            # Compress by summarizing
            return await compress_context(full_context, current_query, total_tokens)
        
        return full_context
        
    except Exception as e:
        print(f"Error building enhanced context: {e}")
        return ""

async def compress_context(context: str, current_query: str, total_tokens: int) -> str:
    """Compress context if too large"""
    try:
        target_tokens = min(1500, total_tokens // 2)
        
        compress_prompt = f"""Summarize this medical history in {target_tokens} tokens, preserving key health issues, patterns, and conditions relevant to: {current_query}

{context[:8000]}

Write a concise medical summary focusing on:
1. Chronic conditions and recurring symptoms
2. Recent health concerns (last 30 days)
3. Any red flags or serious conditions
4. Treatment responses and what has/hasn't worked"""
        
        api_key = os.getenv("OPENROUTER_API_KEY")
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "system", "content": compress_prompt}],
                "max_tokens": target_tokens,
                "temperature": 0.3
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            # Fallback to simple truncation
            return context[:2000] + "\n[Context truncated for length]"
            
    except Exception as e:
        print(f"Error compressing context: {e}")
        return context[:2000]