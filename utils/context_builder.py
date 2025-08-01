"""Context building utilities for Oracle chat"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from supabase_client import supabase
from utils.token_counter import count_tokens
import requests
import os

# Using string format for order clauses ("created_at.desc")

async def get_enhanced_llm_context(user_id: str, conversation_id: str, current_query: str = "") -> str:
    """Build comprehensive context from summaries, quick scans, and deep dives"""
    context_parts = []
    
    print(f"Building enhanced context for user: {user_id}")
    print(f"User ID type: {type(user_id)}, value: {repr(user_id)}")
    
    try:
        # 1. Get LLM summaries from previous conversations
        summaries_response = supabase.table("llm_context")\
            .select("llm_summary, created_at")\
            .eq("user_id", str(user_id))\
            .order("created_at", desc=True)\
            .limit(5)\
            .execute()
        
        print(f"LLM summaries response: {summaries_response}")
        print(f"Found {len(summaries_response.data) if summaries_response.data else 0} LLM summaries")
        
        if summaries_response.data:
            context_parts.append("=== Previous Health Discussions ===")
            for summary in summaries_response.data[:3]:  # Use top 3 most recent
                date = summary['created_at'][:10] if summary.get('created_at') else 'Unknown date'
                context_parts.append(f"\n[{date}]")
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
        
        print(f"Quick scans cutoff date: {cutoff_date}")
        print(f"Quick scans query response: {scans_response}")
        print(f"Found {len(scans_response.data) if scans_response.data else 0} quick scans")
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
        
        print(f"Deep dives query response: {dives_response}")
        print(f"Found {len(dives_response.data) if dives_response.data else 0} deep dives")
        
        if dives_response.data:
            context_parts.append("\n\n=== Deep Health Analyses ===")
            for dive in dives_response.data[:2]:  # Use top 2 most recent
                date = dive['created_at'][:10]
                body_part = dive.get('body_part', 'Unknown')
                condition = dive.get('final_analysis', {}).get('primaryCondition', 'Unknown')
                confidence = dive.get('final_confidence', 0)
                context_parts.append(f"\n[{date} - {body_part}] Deep analysis: {condition} (confidence: {confidence}%)")
        
        # 4. Get current conversation summary if exists (optional)
        if conversation_id and conversation_id != "debug-conversation":
            try:
                current_summary = supabase.table("llm_context")\
                    .select("llm_summary")\
                    .eq("user_id", str(user_id))\
                    .eq("conversation_id", str(conversation_id))\
                    .execute()
                
                if current_summary.data:
                    context_parts.append("\n\n=== Current Conversation Context ===")
                    context_parts.append(current_summary.data[0].get('llm_summary', '')[:500])
            except Exception as e:
                print(f"Error fetching current conversation summary: {e}")
                # Continue without current conversation context
        
        # Join all context parts
        full_context = "\n".join(context_parts)
        
        print(f"Context parts collected: {len(context_parts)} sections")
        print(f"Full context length: {len(full_context)} characters")
        
        # Check if we need to compress
        total_tokens = count_tokens(full_context)
        if total_tokens > 2000:  # Keep context reasonable
            # Compress by summarizing
            return await compress_context(full_context, current_query, total_tokens)
        
        return full_context
        
    except Exception as e:
        import traceback
        print(f"Error building enhanced context: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
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

async def get_enhanced_llm_context_time_range(
    user_id: str, 
    start_date: datetime, 
    end_date: datetime,
    context_type: str = "time_range"
) -> str:
    """
    Build comprehensive context for a specific time range
    Used for week-over-week comparisons in intelligence generation
    """
    context_parts = []
    
    print(f"Building time-range context for user: {user_id}")
    print(f"Time range: {start_date.isoformat()} to {end_date.isoformat()}")
    
    try:
        # Convert dates to ISO format for Supabase queries
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()
        
        # 1. Get LLM summaries within time range
        summaries_response = supabase.table("llm_context")\
            .select("llm_summary, created_at")\
            .eq("user_id", str(user_id))\
            .gte("created_at", start_iso)\
            .lte("created_at", end_iso)\
            .order("created_at", desc=True)\
            .execute()
        
        if summaries_response.data:
            context_parts.append(f"=== Health Discussions ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) ===")
            for summary in summaries_response.data:
                date = summary['created_at'][:10] if summary.get('created_at') else 'Unknown date'
                context_parts.append(f"\n[{date}]")
                context_parts.append(summary.get('llm_summary', '')[:500])
        
        # 2. Get quick scans within time range
        scans_response = supabase.table("quick_scans")\
            .select("created_at, body_part, analysis_result, form_data")\
            .eq("user_id", str(user_id))\
            .gte("created_at", start_iso)\
            .lte("created_at", end_iso)\
            .order("created_at", desc=True)\
            .execute()
        
        if scans_response.data:
            context_parts.append(f"\n\n=== Quick Scans ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) ===")
            for scan in scans_response.data:
                date = scan['created_at'][:10]
                body_part = scan.get('body_part', 'Unknown')
                symptoms = scan.get('form_data', {}).get('symptoms', 'No symptoms recorded')
                condition = scan.get('analysis_result', {}).get('primaryCondition', 'Unknown condition')
                severity = scan.get('form_data', {}).get('painLevel', 'Unknown')
                context_parts.append(f"\n[{date} - {body_part}] {symptoms} (severity: {severity}/10) → {condition}")
        
        # 3. Get deep dives within time range
        dives_response = supabase.table("deep_dive_sessions")\
            .select("created_at, body_part, final_analysis, final_confidence, llm_summary")\
            .eq("user_id", str(user_id))\
            .gte("created_at", start_iso)\
            .lte("created_at", end_iso)\
            .order("created_at", desc=True)\
            .execute()
        
        if dives_response.data:
            context_parts.append(f"\n\n=== Deep Dive Analyses ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) ===")
            for dive in dives_response.data:
                date = dive['created_at'][:10]
                body_part = dive.get('body_part', 'Unknown')
                condition = dive.get('final_analysis', {}).get('primaryCondition', 'Unknown')
                confidence = dive.get('final_confidence', 0)
                summary = dive.get('llm_summary', '')[:200]
                context_parts.append(f"\n[{date} - {body_part}] {condition} (confidence: {confidence}%)")
                if summary:
                    context_parts.append(f"Summary: {summary}")
        
        # 4. Get symptom tracking data within time range
        symptoms_response = supabase.table("symptom_tracking")\
            .select("created_at, symptom_name, body_part, severity")\
            .eq("user_id", str(user_id))\
            .gte("created_at", start_iso)\
            .lte("created_at", end_iso)\
            .order("created_at", desc=True)\
            .execute()
        
        if symptoms_response.data:
            context_parts.append(f"\n\n=== Symptom Tracking ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) ===")
            # Group symptoms by body part
            symptoms_by_part = {}
            for symptom in symptoms_response.data:
                part = symptom.get('body_part', 'General')
                if part not in symptoms_by_part:
                    symptoms_by_part[part] = []
                symptoms_by_part[part].append({
                    'date': symptom['created_at'][:10],
                    'name': symptom.get('symptom_name', 'Unknown'),
                    'severity': symptom.get('severity', 0)
                })
            
            for part, symptoms in symptoms_by_part.items():
                context_parts.append(f"\n{part}:")
                for s in symptoms[:5]:  # Limit to 5 per body part
                    context_parts.append(f"  [{s['date']}] {s['name']} (severity: {s['severity']}/10)")
        
        # 5. Get health stories within time range
        stories_response = supabase.table("health_stories")\
            .select("created_at, story_text")\
            .eq("user_id", str(user_id))\
            .gte("created_at", start_iso)\
            .lte("created_at", end_iso)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if stories_response.data:
            context_parts.append(f"\n\n=== Health Story Summary ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) ===")
            story = stories_response.data[0]
            story_text = story.get('story_text', '')[:500]
            context_parts.append(story_text)
        
        # Join all context parts
        full_context = "\n".join(context_parts)
        
        # Add metadata about the time range
        days_covered = (end_date - start_date).days
        full_context = f"[Time Period: {days_covered} days from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}]\n\n" + full_context
        
        print(f"Time-range context built: {len(full_context)} characters")
        
        # Check if we need to compress
        total_tokens = count_tokens(full_context)
        if total_tokens > 2000:
            return await compress_context(full_context, f"{context_type} analysis", total_tokens)
        
        return full_context
        
    except Exception as e:
        import traceback
        print(f"Error building time-range context: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        return f"Error gathering data for {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"