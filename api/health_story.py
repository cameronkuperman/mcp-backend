"""Health Story API endpoint"""
from fastapi import APIRouter
from datetime import datetime, timezone
import json
import uuid

from models.requests import HealthStoryRequest
from supabase_client import supabase
from utils.data_gathering import get_health_story_data
from utils.token_counter import count_tokens
from utils.json_parser import extract_json_from_response
from business_logic import call_llm

router = APIRouter(prefix="/api", tags=["health-story"])

@router.post("/health-story")
async def generate_health_story(request: HealthStoryRequest):
    """Generate weekly health story analysis"""
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
                model="deepseek/deepseek-chat",  # Good for summarization
                user_id=request.user_id,
                temperature=0.3,
                max_tokens=1024
            )
            context = summary_response.get("content", "\n".join(context_parts[:2]))
        else:
            context = "\n\n".join(context_parts)
        
        # Generate health story with creative title
        system_prompt = """You are a creative health journalist analyzing patterns and trends to create an engaging narrative health story with a compelling title.

        CRITICAL FORMATTING RULES:
        1. You MUST return ONLY a valid JSON object - nothing before or after
        2. Do NOT include any text, explanations, or markdown formatting
        3. Do NOT wrap the JSON in ```json``` code blocks
        4. The response must start with { and end with }
        5. Use proper JSON syntax with double quotes for all strings
        
        The JSON MUST have this EXACT structure:
        {
            "title": "Creative, engaging title that captures the main health theme",
            "subtitle": "Brief tagline that complements the title",
            "content": "2-3 paragraphs of narrative content"
        }

        Title Guidelines:
        - Be creative and engaging while clearly tied to the week's health story
        - Use compelling language that reflects the actual health patterns
        - Create titles that are intriguing but immediately understandable
        - Keep it under 8 words
        - Examples: If headaches are the focus: "Breaking the Morning Headache Pattern"
                    If sleep improved: "Your Sleep Recovery Story"
                    If pain decreased: "The Week Pain Took a Break"
        - Balance creativity with clarity - readers should know what it's about
        
        Subtitle Guidelines:
        - Complement the poetic title with a clearer health connection
        - Use elegant language that bridges the artistic and informative
        - Keep it intriguing but slightly more grounded than the title

        Content Guidelines:
        - Write 2-3 paragraphs with mostly clear, informative tone
        - Use medical terminology naturally within flowing sentences
        - Include percentages and confidence levels smoothly in the narrative
        - Add just a touch of descriptive language (about 1% creative touches)
        - Structure content logically while maintaining readability
        - Write in second person with warmth and very subtle narrative elements

        Style Examples:
        - "Your week revealed a clear pattern: muscle strains appearing across your left pectoralis major (75% confidence) and left biceps (78% confidence)"
        - "Sleep efficiency climbed to 85%, with deep sleep phases extending by 23%—a notable shift that correlates with symptom improvement"
        - "The connection between your stress levels and physical symptoms has become undeniable, with a correlation of 0.78"
        - "Your cardiovascular system is adapting well, with resting heart rate settling from 72 to 68 bpm"

        Do NOT:
        - Mention app features, scans, or technical terms
        - Use excessive medical jargon
        - Be overly dramatic or flowery
        - Give medical advice
        - Overuse metaphors or abstract language
        - Include ANY text outside the JSON object
        
        Remember: Keep it engaging but grounded. The goal is a clear, warm narrative that makes health insights accessible and interesting.
        
        FINAL REMINDER: Return ONLY the JSON object, no other text."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Based on the following health data from the past week, generate a health story. Remember to return ONLY valid JSON with no additional text:\n\n{context}"}
        ]
        
        # Call LLM
        print(f"Calling Kimi K2 for health story generation...")
        print(f"System prompt length: {len(system_prompt)} chars")
        print(f"Context length: {len(context)} chars")
        
        llm_response = await call_llm(
            messages=messages,
            model="deepseek/deepseek-chat",  # FIXED: Use DeepSeek V3 - non-reasoning mode, excellent JSON compliance
            user_id=request.user_id,
            temperature=0.8,  # Slightly higher for more creative writing
            max_tokens=1024
        )
        
        print(f"LLM Response received. Model used: {llm_response.get('model', 'unknown')}")
        print(f"Token usage: {llm_response.get('usage', {})}")

        # Parse the JSON response to get title and content
        # Handle both direct content and OpenRouter format
        story_response = None
        if "choices" in llm_response and len(llm_response["choices"]) > 0:
            story_response = llm_response["choices"][0]["message"].get("content", "")
        else:
            story_response = llm_response.get("content", "")
        
        # Log raw response
        print(f"Raw LLM response type: {type(story_response)}")
        if isinstance(story_response, str):
            print(f"Raw response length: {len(story_response)} chars")
            print(f"Raw response (first 200 chars): {story_response[:200]}")
            print(f"Raw response (last 200 chars): {story_response[-200:]}")
        else:
            print(f"Raw response (dict): {story_response}")

        # Use aggressive JSON extraction
        story_data = extract_json_from_response(story_response)

        # Debug logging
        if not story_data:
            print(f"ERROR: Failed to extract JSON from response")
            print(f"Full raw response length: {len(story_response) if story_response else 0}")
            print(f"Full raw response: {story_response}")
        else:
            print(f"Successfully extracted JSON. Keys: {list(story_data.keys()) if isinstance(story_data, dict) else 'Not a dict'}")
        
        if story_data and isinstance(story_data, dict):
            story_title = story_data.get("title", "Your Health Patterns This Week")
            story_subtitle = story_data.get("subtitle", "An analysis of your wellness trends")
            story_content = story_data.get("content", "Unable to generate health story at this time.")
            
            print(f"Extracted title: {story_title[:50]}...")
            print(f"Extracted subtitle: {story_subtitle[:50]}...")
            print(f"Content length: {len(story_content)} chars")
        else:
            # Fallback values
            print("WARNING: Using fallback values for story")
            story_title = "Your Health Patterns This Week"
            story_subtitle = "An analysis of your wellness trends"
            story_content = str(story_response) if story_response else "Unable to generate health story at this time."
        
        # Generate response
        story_id = str(uuid.uuid4())
        generated_date = datetime.now(timezone.utc)
        
        # Save to database (create health_stories table if needed)
        try:
            story_db_data = {
                "id": story_id,
                "user_id": request.user_id,
                "title": story_title,
                "subtitle": story_subtitle,
                "story_text": story_content,
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
                supabase.table("health_stories").insert(story_db_data).execute()
            except Exception as db_error:
                print(f"Health stories table may not exist: {db_error}")
                # Continue without saving
                
        except Exception as save_error:
            print(f"Error saving health story: {save_error}")
        
        return {
            "story_id": story_id,
            "title": story_title,
            "subtitle": story_subtitle,
            "date": generated_date.strftime('%B %d, %Y'),
            "content": story_content,
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