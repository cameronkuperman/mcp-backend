#!/usr/bin/env python3
"""
LLM Summary Tools - Generate and Aggregate Medical Summaries
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone
import os
from typing import Optional
import math
from supabase_client import supabase
from business_logic import call_llm
import tiktoken

# Token counter
encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

def count_tokens(text: str) -> int:
    """Count tokens in text"""
    return len(encoding.encode(text))

class GenerateSummaryRequest(BaseModel):
    conversation_id: Optional[str] = None
    quick_scan_id: Optional[str] = None
    user_id: str

class AggregateSummariesRequest(BaseModel):
    user_id: str
    current_query: str

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def calculate_summary_length(total_tokens: int) -> int:
    """Calculate optimal summary length based on conversation tokens"""
    if total_tokens < 1000:
        return 100
    elif total_tokens < 10000:
        return int(100 + (total_tokens - 1000) / 9000 * 400)  # 100-500
    elif total_tokens < 20000:
        return int(500 + (total_tokens - 10000) / 10000 * 250)  # 500-750
    elif total_tokens < 100000:
        return int(750 + (total_tokens - 20000) / 80000 * 1250)  # 750-2000
    else:
        return 2000  # Max 2000 tokens for very long conversations

def calculate_compression_ratio(total_tokens: int) -> float:
    """Calculate compression ratio for aggregate summaries"""
    if total_tokens < 25000:
        return 1.0  # No compression
    elif total_tokens < 50000:
        return 1.5
    elif total_tokens < 100000:
        return 2.0
    elif total_tokens < 200000:
        return 5.0
    elif total_tokens < 500000:
        return 10.0
    elif total_tokens < 1000000:
        return 20.0
    else:
        return 100.0

@app.post("/api/generate_summary")
async def generate_llm_summary(request: GenerateSummaryRequest):
    """Generate medical summary of conversation or quick scan"""
    try:
        # Validate request
        if not request.conversation_id and not request.quick_scan_id:
            return {"error": "Either conversation_id or quick_scan_id must be provided", "status": "error"}
        
        if request.quick_scan_id:
            # Handle Quick Scan summary
            scan_response = supabase.table("quick_scans").select("*").eq("id", request.quick_scan_id).execute()
            
            if not scan_response.data:
                return {"error": "Quick scan not found", "status": "error"}
            
            scan_data = scan_response.data[0]
            
            # Create summary for quick scan
            summary_prompt = f"""You are a physician creating a clinical note from a Quick Scan assessment.

SCAN DATE: {scan_data.get('created_at', '')[:10]}
BODY PART: {scan_data.get('body_part', 'Not specified')}
CONFIDENCE: {scan_data.get('confidence_score', 0)}%
URGENCY: {scan_data.get('urgency_level', 'Not specified')}

PATIENT REPORTED DATA:
{scan_data.get('form_data', {})}

AI ANALYSIS:
{scan_data.get('analysis_result', {})}

Create a concise 150-word clinical summary focusing on:
- Chief complaint and location
- Reported symptoms and severity
- AI assessment findings
- Recommended actions
- Any red flags noted

IMPORTANT: Only mention symptoms and findings that were explicitly reported by the patient or identified in the analysis. Do not add or infer information not present in the data.

Write the clinical summary:"""

            # Generate summary
            summary_response = await call_llm(
                messages=[{"role": "system", "content": summary_prompt}],
                model="deepseek/deepseek-chat",
                max_tokens=200,
                temperature=0.3
            )
            
            summary_content = summary_response["content"]
            
            # Update quick_scans table with summary
            supabase.table("quick_scans").update({
                "llm_summary": summary_content
            }).eq("id", request.quick_scan_id).execute()
            
            return {
                "summary": summary_content,
                "type": "quick_scan",
                "scan_id": request.quick_scan_id,
                "status": "success"
            }
            
        else:
            # Handle conversation summary (existing logic)
            messages_response = supabase.table("messages").select("*").eq("conversation_id", request.conversation_id).order("created_at").execute()
            
            if not messages_response.data:
                return {"error": "No messages found", "status": "error"}
        
            messages = messages_response.data
            
            # 2. Build conversation text and count tokens
            conversation_text = ""
            for msg in messages:
                timestamp = msg.get("created_at", "")[:10]  # Date only
                role = msg.get("role", "").capitalize()
                content = msg.get("content", "")
                conversation_text += f"{timestamp} - {role}: {content}\n\n"
            
            total_tokens = count_tokens(conversation_text)
            summary_tokens = calculate_summary_length(total_tokens)
            
            # 3. Create medical summary prompt
            summary_prompt = f"""You are a physician creating clinical notes for future reference.

CONSULTATION DATE: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
CONVERSATION LENGTH: {len(messages)} messages

Create a {summary_tokens}-token medical summary including:
- Chief complaints and symptom timeline
- Patient's reported symptoms and severity
- Treatments discussed and patient's response
- Risk factors or concerning symptoms noted
- Recommended follow-up actions
- Any medications or interventions mentioned

Focus on clinically relevant information that would help in future consultations.

CONVERSATION:
{conversation_text[:10000]}...  # Truncate if too long

Write a concise medical summary:"""

            # 4. Generate summary
            summary_response = await call_llm(
                messages=[{"role": "system", "content": summary_prompt}],
                model="deepseek/deepseek-chat",
                max_tokens=summary_tokens + 100,  # Buffer
                temperature=0.3  # Lower temp for factual summary
            )
            
            summary_content = summary_response["content"]
            
            # 5. Delete old summary if exists
            delete_response = supabase.table("llm_context").delete().eq("conversation_id", request.conversation_id).eq("user_id", request.user_id).execute()
            
            # 6. Insert new summary
            insert_data = {
                "conversation_id": request.conversation_id,
                "user_id": request.user_id,
                "llm_summary": summary_content,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "token_count": count_tokens(summary_content),
                "original_message_count": len(messages),
                "original_token_count": total_tokens
            }
            
            insert_response = supabase.table("llm_context").insert(insert_data).execute()
            
            return {
                "summary": summary_content,
                "token_count": count_tokens(summary_content),
                "compression_ratio": round(total_tokens / count_tokens(summary_content), 2),
                "status": "success"
            }
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/aggregate_summaries")
async def aggregate_llm_summaries(request: AggregateSummariesRequest):
    """Aggregate all user's summaries with intelligent compression"""
    try:
        # 1. Fetch all summaries for user
        summaries_response = supabase.table("llm_context").select("*").eq("user_id", request.user_id).order("created_at", desc=True).execute()
        
        if not summaries_response.data:
            return {"aggregated_summary": "No previous medical history found.", "status": "success"}
        
        summaries = summaries_response.data
        
        # 2. Calculate total tokens
        all_summaries_text = ""
        for summary in summaries:
            date = summary.get("created_at", "")[:10]
            content = summary.get("llm_summary", "")
            all_summaries_text += f"[{date}] {content}\n\n"
        
        total_tokens = count_tokens(all_summaries_text)
        compression_ratio = calculate_compression_ratio(total_tokens)
        target_tokens = int(total_tokens / compression_ratio)
        
        # 3. Choose model based on context size
        if total_tokens > 200000:
            model = "google/gemini-2.0-flash-exp:free"  # Better for huge contexts
        else:
            model = "deepseek/deepseek-chat"
        
        # 4. Create aggregate prompt
        aggregate_prompt = f"""You are reviewing a patient's complete medical history to provide context for current consultation.

CURRENT QUERY: {request.current_query}
TOTAL CONSULTATIONS: {len(summaries)}
COMPRESSION NEEDED: {compression_ratio}x reduction to ~{target_tokens} tokens

Create a {target_tokens}-token summary that:
1. Prioritizes information relevant to the current query
2. Highlights recurring symptoms or chronic conditions
3. Notes treatment responses and patterns
4. Includes recent consultations with more detail
5. Preserves critical medical information

Focus on continuity of care and patterns that inform current consultation.

MEDICAL HISTORY:
{all_summaries_text[:50000]}...  # Truncate if needed

Write comprehensive medical history summary:"""

        # 5. Generate aggregate summary
        aggregate_response = await call_llm(
            messages=[{"role": "system", "content": aggregate_prompt}],
            model=model,
            max_tokens=target_tokens + 200,  # Buffer
            temperature=0.3
        )
        
        aggregated_content = aggregate_response["content"]
        
        return {
            "aggregated_summary": aggregated_content,
            "original_token_count": total_tokens,
            "compressed_token_count": count_tokens(aggregated_content),
            "compression_ratio": compression_ratio,
            "consultations_included": len(summaries),
            "model_used": model,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error aggregating summaries: {e}")
        return {"error": str(e), "status": "error"}

# Function to be called from Oracle when needed
async def get_optimized_llm_context(user_id: str, conversation_id: str, current_query: str) -> str:
    """Get LLM context, aggregating if too large"""
    try:
        # First get regular context
        context_response = supabase.table("llm_context").select("llm_summary").eq("user_id", user_id).eq("conversation_id", conversation_id).execute()
        
        if context_response.data:
            context = context_response.data[0].get("llm_summary", "")
            
            # Check token count
            if count_tokens(context) > 25000:
                # Need to aggregate
                aggregate_result = await aggregate_llm_summaries(
                    AggregateSummariesRequest(user_id=user_id, current_query=current_query)
                )
                return aggregate_result.get("aggregated_summary", context)
            else:
                return context
        
        return ""
        
    except Exception as e:
        print(f"Error getting optimized context: {e}")
        return ""

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "LLM Summary Tools"}

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🧠 LLM SUMMARY TOOLS - READY!")
    print("="*60)
    print("📝 Generate Summary: POST /api/generate_summary")
    print("🔄 Aggregate Summaries: POST /api/aggregate_summaries")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)