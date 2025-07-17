"""Health Story API endpoint"""
from fastapi import APIRouter
from datetime import datetime, timezone
import json
import uuid
import os

from models.requests import HealthStoryRequest
from supabase_client import supabase
from utils.data_gathering import get_health_story_data
from utils.token_counter import count_tokens
from business_logic import call_llm

router = APIRouter(prefix="/api", tags=["health-story"])

@router.post("/health-story")
async def generate_health_story(request: HealthStoryRequest):
    """Generate weekly health story analysis"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    print(f"Health story request received for user_id: '{request.user_id}'")
    print(f"User ID type: {type(request.user_id)}, length: {len(request.user_id)}")
    
    try:
        # Gather all relevant data
        health_data = await get_health_story_data(request.user_id, request.date_range)
        
        # Count tokens and prepare context
        total_tokens = 0
        context_parts = []
        
        # Add medical profile if available
        if health_data["medical_profile"]:
            profile_text = f"Medical Profile: {json.dumps(health_data['medical_profile'], indent=2)}"
            context_parts.append(profile_text)
            total_tokens += count_tokens(profile_text)
        
        # Add recent oracle chats (limit to most relevant)
        if health_data["oracle_chats"]:
            recent_chats = health_data["oracle_chats"][-10:]  # Last 10 messages
            chat_text = "Recent Oracle Conversations:\n"
            for msg in recent_chats:
                chat_text += f"- {msg.get('created_at', '')}: {msg.get('content', '')[:200]}...\n"
            context_parts.append(chat_text)
            total_tokens += count_tokens(chat_text)
        
        # Add quick scans with detailed information
        if health_data["quick_scans"]:
            print(f"Adding {len(health_data['quick_scans'])} quick scans to health story context")
            scan_text = "Recent Quick Scans:\n"
            for scan in health_data["quick_scans"]:
                # Get the analysis result - it's stored directly in the scan
                analysis = scan.get('analysis_result', {})
                form_data = scan.get('form_data', {})
                
                # Format the date more nicely
                created_at = scan.get('created_at', '')
                if created_at:
                    try:
                        date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime('%Y-%m-%d %H:%M')
                    except:
                        formatted_date = created_at[:10]
                else:
                    formatted_date = 'Unknown date'
                
                scan_text += f"\n- {formatted_date}: {scan.get('body_part', 'Unknown body part')} scan\n"
                
                # Add user-reported symptoms from form data
                if form_data.get('symptoms'):
                    scan_text += f"  Reported Symptoms: {form_data.get('symptoms')}\n"
                if form_data.get('painLevel'):
                    scan_text += f"  Pain Level: {form_data.get('painLevel')}/10\n"
                if form_data.get('duration'):
                    scan_text += f"  Duration: {form_data.get('duration')}\n"
                
                # Add analysis results
                scan_text += f"  Primary Condition: {analysis.get('primaryCondition', 'Unknown')}\n"
                scan_text += f"  Likelihood: {analysis.get('likelihood', 'Unknown')}\n"
                scan_text += f"  Confidence: {analysis.get('confidence', scan.get('confidence_score', 0))}%\n"
                scan_text += f"  Urgency: {analysis.get('urgency', scan.get('urgency_level', 'unknown'))}\n"
                
                # Add symptoms identified by AI
                symptoms = analysis.get('symptoms', [])
                if symptoms and isinstance(symptoms, list):
                    scan_text += f"  Identified Symptoms: {', '.join(str(s) for s in symptoms[:5])}\n"
                
                # Add key recommendations
                recommendations = analysis.get('recommendations', [])
                if recommendations and isinstance(recommendations, list):
                    scan_text += f"  Key Recommendations: {', '.join(str(r) for r in recommendations[:3])}\n"
                
                # Add self-care if available
                self_care = analysis.get('selfCare', [])
                if self_care and isinstance(self_care, list) and len(self_care) > 0:
                    scan_text += f"  Self-Care Tips: {str(self_care[0])}\n"
                
                # Add red flags if any
                red_flags = analysis.get('redFlags', [])
                if red_flags and isinstance(red_flags, list) and len(red_flags) > 0:
                    scan_text += f"  Warning Signs: {str(red_flags[0])}\n"
                
            context_parts.append(scan_text)
            total_tokens += count_tokens(scan_text)
        else:
            print("No quick scans found for health story")
            # Explicitly add a note about no quick scans
            no_scans_text = "Recent Quick Scans: No quick scans recorded during this period.\n"
            context_parts.append(no_scans_text)
            total_tokens += count_tokens(no_scans_text)
        
        # Add deep dive summaries
        if health_data["deep_dives"]:
            dive_text = "Deep Dive Analyses:\n"
            for dive in health_data["deep_dives"]:
                if dive.get("status") == "completed" and dive.get("final_analysis"):
                    dive_text += f"- {dive.get('created_at', '')}: {dive.get('body_part', '')} - "
                    dive_text += f"{dive.get('final_analysis', {}).get('primaryCondition', 'Analysis completed')}\n"
            context_parts.append(dive_text)
            total_tokens += count_tokens(dive_text)
        
        # Add symptom tracking
        if health_data["symptom_tracking"]:
            symptom_text = "Symptom Tracking:\n"
            for entry in health_data["symptom_tracking"]:
                symptom_text += f"- {entry.get('date', '')}: "
                symptoms = entry.get('symptoms', [])
                if symptoms:
                    symptom_text += f"{', '.join(symptoms[:3])}\n"
            context_parts.append(symptom_text)
            total_tokens += count_tokens(symptom_text)
        
        # If context is too large, summarize it
        if total_tokens > 10000:
            # Use LLM to summarize the context
            summary_response = await call_llm(
                messages=[
                    {"role": "system", "content": "Summarize the following health data concisely, focusing on key patterns and changes:"},
                    {"role": "user", "content": "\n".join(context_parts)}
                ],
                model="deepseek/deepseek-chat",
                user_id=request.user_id,
                temperature=0.3,
                max_tokens=1024
            )
            context = summary_response.get("content", "\n".join(context_parts[:2]))
        else:
            context = "\n\n".join(context_parts)
        
        # Generate health story
        system_prompt = """You are analyzing health patterns and trends from user data to create a narrative health story.

        Write 2-3 paragraphs in a flowing, narrative style that:
        - Identifies patterns and correlations in the health data
        - Uses specific percentages and metrics when available
        - Connects symptoms to lifestyle factors
        - Highlights improvements and positive changes
        - Acknowledges ongoing concerns without alarm
        - Focuses on trends over time

        Style Guidelines:
        - Write in second person ("Your health journey...")
        - Use natural, flowing language without technical jargon
        - Avoid mentioning specific tools, scans, or app features
        - Present insights as observations about their health patterns
        - Include specific metrics (percentages, timeframes, correlations)
        - Connect different health aspects (sleep, pain, exercise, etc.)

        Do NOT:
        - Mention "quick scan", "deep dive", "oracle", or any app features
        - Use medical terminology without explanation
        - Give direct medical advice
        - Use alarmist language
        - Reference the data sources directly
        
        Transform the data into insights like:
        - "Your morning headaches show a pattern..."
        - "The chest discomfort you've been experiencing..."
        - "Your sleep quality has improved by X%..."
        - "Pain levels tend to spike when..."
        
        Example style:
        Your health journey continues to show positive momentum. This week has been marked by significant improvements in your sleep quality, with an average increase of 23% in deep sleep phases compared to last week. This improvement correlates strongly with the reduction in evening screen time you've implemented.

        The persistent morning headaches you've been experiencing appear to be linked to a combination of factors: dehydration, elevated stress levels on weekdays, and potentially your sleeping position. The pattern analysis shows that headaches are 78% more likely on days following less than 6 hours of sleep.

        Your body's response to the new exercise routine has been overwhelmingly positive. Heart rate variability has improved by 15%, and your resting heart rate has decreased by 4 bpm over the past month. These are strong indicators of improving cardiovascular health."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Based on the following health data from the past week, generate a health story:\n\n{context}"}
        ]
        
        # Call LLM
        llm_response = await call_llm(
            messages=messages,
            model="moonshotai/kimi-k2",  # Using Kimi K2 for article generation
            user_id=request.user_id,
            temperature=0.7,
            max_tokens=1024
        )
        
        story_text = llm_response.get("content", "Unable to generate health story at this time.")
        
        # Generate response
        story_id = str(uuid.uuid4())
        generated_date = datetime.now(timezone.utc)
        
        # Save to database (create health_stories table if needed)
        try:
            story_data = {
                "id": story_id,
                "user_id": request.user_id,
                "header": "Current Analysis",
                "story_text": story_text,
                "date_range": request.date_range,
                "data_sources": {
                    "quick_scans": len(health_data["quick_scans"]),
                    "deep_dives": len(health_data["deep_dives"]),
                    "oracle_chats": len(health_data["oracle_chats"]),
                    "symptom_tracking": len(health_data["symptom_tracking"])
                },
                "created_at": generated_date.isoformat(),
                "generation_model": llm_response.get("model", ""),
                "tokens_used": llm_response.get("usage", {})
            }
            
            # Try to insert, handle table not existing
            try:
                supabase.table("health_stories").insert(story_data).execute()
            except Exception as db_error:
                print(f"Health stories table may not exist: {db_error}")
                # Continue without saving
                
        except Exception as save_error:
            print(f"Error saving health story: {save_error}")
        
        return {
            "story_id": story_id,
            "header": "Current Analysis",
            "date": generated_date.strftime('%B %d, %Y'),
            "content": story_text,
            "data_sources": {
                "quick_scans": len(health_data["quick_scans"]),
                "deep_dives": len(health_data["deep_dives"]),
                "oracle_chats": len(health_data["oracle_chats"]),
                "symptom_tracking": len(health_data["symptom_tracking"])
            },
            "usage": llm_response.get("usage", {}),
            "model": llm_response.get("model", ""),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating health story: {e}")
        return {
            "error": str(e),
            "status": "error"
        }