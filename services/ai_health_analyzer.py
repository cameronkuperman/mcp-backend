"""
AI Health Analyzer Service
Uses Gemini 2.5 Pro for generating health insights, predictions, patterns, and strategies
"""

import httpx
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
import asyncio
import os
from supabase import create_client

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase client for historical data
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

class HealthAnalyzer:
    def __init__(self):
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = "google/gemini-2.5-pro"
        self.fallback_model = "moonshotai/kimi-k2"  # Fallback if primary fails
        self.timeout = 90  # 90 seconds timeout per attempt
        
    async def _call_ai(self, prompt: str, temperature: float = 0.7, use_fallback: bool = False) -> Dict:
        """Make API call with fallback model support"""
        model_to_use = self.fallback_model if use_fallback else self.model
        
        try:
            # Debug logging
            logger.info(f"🤖 Calling AI with model: {model_to_use}")
            logger.info(f"📏 Prompt length: {len(prompt)} chars")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://proxima-1.health",
                        "X-Title": "Proxima-1 Health Intelligence"
                    },
                    json={
                        "model": model_to_use,
                        "messages": [
                            {
                                "role": "system",
                                "content": """You are an expert health intelligence analyst. Provide supportive, actionable insights based on health data patterns. Never diagnose conditions. Focus on patterns, correlations, and wellness optimization. 

CRITICAL INSTRUCTIONS:
1. ALWAYS return valid JSON
2. NEVER return empty arrays
3. If data is limited, provide general wellness insights
4. Always include at least 2-3 insights/patterns
5. Escape quotes in JSON strings with backslash (\")"""
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": temperature,
                        "max_tokens": 2000
                    }
                )
                
                logger.info(f"📡 Response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"❌ {model_to_use} API error: {response.status_code}")
                    if not use_fallback:
                        logger.info("🔄 Trying fallback model...")
                        return await self._call_ai(prompt, temperature, use_fallback=True)
                    raise Exception(f"Both models failed: {response.status_code}")
                
                result = response.json()
                content = result['choices'][0]['message']['content']
                logger.info(f"✅ {model_to_use} response received")
                
                # Extract JSON from the response
                extracted = self._extract_json(content)
                
                # Ensure we always have content
                if not extracted or all(not v for v in extracted.values() if isinstance(v, list)):
                    logger.warning("⚠️ Empty response, using fallback model")
                    if not use_fallback:
                        return await self._call_ai(prompt, temperature, use_fallback=True)
                    # If even fallback returns empty, generate default content
                    return self._generate_default_response(prompt)
                
                return extracted
                
        except httpx.TimeoutException:
            logger.error(f"⏱️ {model_to_use} timed out after {self.timeout} seconds")
            if not use_fallback:
                logger.info("🔄 Trying fallback model due to timeout...")
                return await self._call_ai(prompt, temperature, use_fallback=True)
            return self._generate_default_response(prompt)
        except Exception as e:
            logger.error(f"❌ {model_to_use} failed: {str(e)}")
            if not use_fallback:
                logger.info("🔄 Trying fallback model due to error...")
                return await self._call_ai(prompt, temperature, use_fallback=True)
            return self._generate_default_response(prompt)
    
    def _extract_json(self, content: str) -> Dict:
        """Extract JSON from AI response, handling various formats"""
        content = content.strip()
        
        # Log what we're trying to parse
        logger.debug(f"🔍 Attempting to extract JSON from content starting with: {content[:100]}...")
        
        # First, try to parse as-is in case it's already valid JSON
        try:
            result = json.loads(content)
            logger.info("✅ Successfully parsed JSON on first try")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"❌ Initial JSON parse failed: {e}")
            pass
        
        # If the content has escaped quotes at the JSON structure level, unescape them
        # This handles cases where the AI over-escapes the JSON
        if '\\"' in content and content.startswith('[{') or content.startswith('{'):
            content = content.replace('\\"', '"')
            try:
                return json.loads(content)
            except:
                pass
        
        # Try to find JSON between code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                content = content[start:end].strip()
        
        # Clean up common issues
        # Don't blindly replace single quotes - it breaks strings containing quotes
        # content = content.replace("'", '"')  # REMOVED - this breaks valid strings
        content = content.strip()
        
        # Try to fix truncated JSON by closing open structures
        if content.count('{') > content.count('}'):
            # Count how many closing braces we need
            missing_braces = content.count('{') - content.count('}')
            content += '}' * missing_braces
        
        if content.count('[') > content.count(']'):
            # Count how many closing brackets we need
            missing_brackets = content.count('[') - content.count(']')
            content += ']' * missing_brackets
        
        # Fix unescaped quotes within string values
        # This regex finds strings that contain unescaped quotes
        import re
        # Match: "key": "value with "quotes" inside"
        # Replace with: "key": "value with \"quotes\" inside"
        pattern = r'("(?:[^"\\]|\\.)*")\s*:\s*"([^"]*)"([^"]*)"([^"]*)"'
        while re.search(pattern, content):
            content = re.sub(pattern, r'\1: "\2\"\3\"\4"', content)
        
        # Remove incomplete elements at the end
        # If the JSON ends with a comma, remove everything after the last complete element
        if content.rstrip().endswith(','):
            # Find the last complete object/value
            last_comma = content.rfind(',')
            content = content[:last_comma]
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Content: {content[:500]}...")
            # Try to extract what we can
            try:
                # If it's a partial response, try to extract complete parts
                if '"insights"' in content and content.find('"insights"'):
                    # Try to extract just the insights array
                    insights_start = content.find('"insights"') + len('"insights"') + 1
                    insights_text = content[insights_start:]
                    if insights_text.strip().startswith('['):
                        bracket_count = 0
                        end_pos = 0
                        for i, char in enumerate(insights_text):
                            if char == '[':
                                bracket_count += 1
                            elif char == ']':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    end_pos = i + 1
                                    break
                        if end_pos > 0:
                            insights_array = insights_text[:end_pos]
                            return {"insights": json.loads(insights_array)}
                return {}
            except:
                return {}
    
    def _generate_default_response(self, prompt: str) -> Dict:
        """Generate default response when AI fails"""
        logger.info("🎯 Generating default response")
        
        # Check what type of response is needed based on prompt
        if "insights" in prompt.lower():
            return {
                "insights": [
                    {
                        "type": "neutral",
                        "title": "Health Tracking Active",
                        "description": "Continue tracking your health data to receive personalized insights",
                        "confidence": 75,
                        "metadata": {"is_default": True}
                    },
                    {
                        "type": "positive",
                        "title": "Consistent Monitoring",
                        "description": "Regular health tracking helps identify patterns over time",
                        "confidence": 80,
                        "metadata": {"is_default": True}
                    }
                ]
            }
        elif "shadow" in prompt.lower() or "pattern" in prompt.lower():
            return {
                "patterns": [
                    {
                        "name": "Health data still building",
                        "category": "other",
                        "last_seen": "Continue tracking to identify patterns",
                        "significance": "low",
                        "days_missing": 0
                    }
                ]
            }
        else:
            return {"status": "default_response", "message": "Continue tracking for insights"}
    
    async def generate_insights(self, story: str, health_data: Dict, user_id: str) -> List[Dict]:
        """Generate key health insights from the story and data"""
        prompt = f"""
        Analyze this health story and data to generate 4-6 key insights.
        
        Health Story:
        {story[:1000]}  # Reduced to avoid token issues
        
        Health Data Summary:
        - Total Oracle chats: {health_data.get('oracle_sessions', {}).get('total_sessions', 0)}
        - Quick scans performed: {health_data.get('quick_scans', {}).get('total_scans', 0)}
        - Deep dives completed: {health_data.get('deep_dives', {}).get('total_dives', 0)}
        - Body parts mentioned: {', '.join(health_data.get('body_parts', [])[:10])}
        - Recent symptoms: {', '.join(health_data.get('recent_symptoms', [])[:10])}
        - Health notes: {health_data.get('notes_count', 0)}
        
        Generate insights that are:
        1. Specific and actionable
        2. Based on patterns in the data
        3. Supportive and encouraging
        4. Focused on wellness optimization
        
        For each insight, provide:
        - type: "positive" (good patterns), "warning" (concerns), or "neutral" (observations)
        - title: Brief, impactful statement (max 10 words)
        - description: One detailed sentence explaining the insight
        - confidence: 0-100 based on data strength
        - metadata: Additional context (optional)
        
        Return ONLY a JSON object with this structure:
        {{
            "insights": [
                {{
                    "type": "positive|warning|neutral",
                    "title": "Brief title",
                    "description": "Detailed explanation",
                    "confidence": 85,
                    "metadata": {{
                        "related_symptoms": ["symptom1", "symptom2"],
                        "body_parts": ["part1", "part2"]
                    }}
                }}
            ]
        }}
        """
        
        try:
            result = await self._call_ai(prompt, temperature=0.6)
            logger.info(f"AI returned for insights: {json.dumps(result)[:500]}")
            insights = result.get('insights', [])
            
            # Validate and clean insights
            valid_insights = []
            for insight in insights:
                if all(key in insight for key in ['type', 'title', 'description', 'confidence']):
                    # Ensure confidence is within range
                    insight['confidence'] = max(0, min(100, int(insight['confidence'])))
                    valid_insights.append(insight)
            
            return valid_insights[:6]  # Limit to 6 insights
            
        except Exception as e:
            logger.error(f"Failed to generate insights: {str(e)}")
            # Return default insights on failure
            return [
                {
                    "type": "neutral",
                    "title": "Health tracking active",
                    "description": "You're actively monitoring your health, which is a positive step toward wellness.",
                    "confidence": 90,
                    "metadata": {}
                }
            ]
    
    async def generate_predictions(self, story: str, health_data: Dict, user_id: str) -> List[Dict]:
        """Generate health predictions based on patterns"""
        # Get historical patterns for better predictions
        historical_patterns = await self._get_historical_patterns(user_id)
        
        prompt = f"""
        Based on this health story and patterns, generate 2-4 health predictions.
        
        Current Health Story:
        {story[:1500]}
        
        Recent Patterns:
        - Symptom frequency: {health_data.get('symptom_patterns', {})}
        - Body part mentions: {health_data.get('body_part_frequency', {})}
        - Historical trends: {historical_patterns}
        
        Generate predictions that are:
        1. Based on observable patterns, NOT medical diagnoses
        2. Focused on general wellness events (e.g., "energy levels", "sleep quality", "stress response")
        3. Supportive and actionable
        4. Time-bound and specific
        
        For each prediction:
        - event: General health event description (avoid specific medical conditions)
        - probability: 0-100 likelihood percentage
        - timeframe: "This week", "Next few days", "Coming weekend", etc.
        - preventable: true/false
        - reasoning: Brief explanation of why this might occur
        - actions: List of 1-3 preventive actions (if preventable)
        
        Return ONLY a JSON object:
        {{
            "predictions": [
                {{
                    "event": "Energy fluctuations likely",
                    "probability": 75,
                    "timeframe": "Next few days",
                    "preventable": true,
                    "reasoning": "Sleep pattern changes noted in recent tracking",
                    "actions": ["Maintain consistent sleep schedule", "Monitor caffeine intake"]
                }}
            ]
        }}
        """
        
        try:
            result = await self._call_ai(prompt, temperature=0.7)
            predictions = result.get('predictions', [])
            
            # Validate predictions
            valid_predictions = []
            for pred in predictions:
                if all(key in pred for key in ['event', 'probability', 'timeframe']):
                    pred['probability'] = max(0, min(100, int(pred['probability'])))
                    pred['preventable'] = pred.get('preventable', False)
                    pred['actions'] = pred.get('actions', [])[:3]
                    valid_predictions.append(pred)
            
            return valid_predictions[:4]
            
        except Exception as e:
            logger.error(f"Failed to generate predictions: {str(e)}")
            return []
    
    async def generate_insights_from_context(self, llm_context: str, health_data: Dict, user_id: str) -> List[Dict]:
        """Generate insights using the same context as Oracle chat"""
        prompt = f"""
        Analyze this comprehensive health context and generate 4-6 key insights.
        
        HEALTH CONTEXT (same data Oracle uses):
        {llm_context[:3000]}  # Limit to prevent token issues
        
        ADDITIONAL DATA SUMMARY:
        - Total health interactions: {health_data.get('oracle_sessions', {}).get('total_sessions', 0)}
        - Recent symptoms tracked: {len(health_data.get('recent_symptoms', []))}
        - Body parts of concern: {len(health_data.get('body_parts', []))}
        
        Generate insights that are:
        1. Based on patterns in the actual health data
        2. Specific to what the user has been tracking
        3. Actionable and supportive
        4. NOT generic health advice
        
        Focus on:
        - Patterns in symptoms or body parts
        - Changes from previous weeks
        - Areas not mentioned recently (shadow patterns)
        - Correlations between different health aspects
        
        Return ONLY a JSON object:
        {{
            "insights": [
                {{
                    "type": "positive|warning|neutral",
                    "title": "Brief, specific title (max 10 words)",
                    "description": "One detailed sentence about the specific pattern observed",
                    "confidence": 60-95,
                    "metadata": {{
                        "based_on": "specific data source (e.g., 'chest pain tracked 3 times')"
                    }}
                }}
            ]
        }}
        """
        
        try:
            result = await self._call_ai(prompt, temperature=0.6)
            insights = result.get('insights', [])
            
            # Validate and clean insights
            valid_insights = []
            for insight in insights:
                if all(key in insight for key in ['type', 'title', 'description', 'confidence']):
                    # Ensure confidence is within range
                    insight['confidence'] = max(60, min(95, int(insight['confidence'])))
                    # Ensure it's specific, not generic
                    if 'drink water' not in insight['description'].lower() and 'see a doctor' not in insight['title'].lower():
                        valid_insights.append(insight)
            
            return valid_insights[:6]
            
        except Exception as e:
            logger.error(f"Failed to generate insights from context: {str(e)}")
            # Return a context-aware fallback
            return [{
                "type": "neutral",
                "title": "Health tracking active",
                "description": "Your health data is being analyzed. Continue tracking for personalized insights.",
                "confidence": 70,
                "metadata": {"is_fallback": True}
            }]
    
    async def detect_shadow_patterns_from_context(self, current_week_context: str, historical_context: str, health_data: Dict, user_id: str) -> List[Dict]:
        """Detect patterns by comparing current week vs historical data"""
        prompt = f"""
        Analyze what health topics/symptoms the user mentioned BEFORE this week but DIDN'T mention THIS week.
        
        CURRENT WEEK HEALTH DATA:
        {current_week_context[:1500]}
        
        HISTORICAL HEALTH DATA (Before This Week):
        {historical_context[:1500]}
        
        SUMMARY STATS:
        - Total historical interactions: {health_data.get('oracle_sessions', {}).get('total_sessions', 0)}
        - Body parts tracked historically: {len(health_data.get('body_parts', []))}
        - Symptoms tracked historically: {len(health_data.get('recent_symptoms', []))}
        
        Identify 3-5 things that are MISSING from the current week that appeared in historical data.
        Look for:
        1. Symptoms they used to mention but didn't this week (e.g., "headaches" mentioned 5 times before, 0 times this week)
        2. Body parts they used to track but ignored (e.g., "knee pain" was frequent, now absent)
        3. Health concerns they stopped discussing (e.g., "anxiety", "sleep issues")
        4. Treatments/medications they used to mention
        5. Wellness activities they stopped reporting (exercise, meditation, diet)
        
        IMPORTANT: Only report things that were mentioned MULTIPLE times historically but are COMPLETELY absent this week.
        
        Return ONLY a JSON object:
        {{
            "patterns": [
                {{
                    "name": "Brief name (e.g., 'Knee pain updates')",
                    "category": "symptom|body_part|medication|wellness|mental_health|other",
                    "last_seen": "Description of how it appeared before (e.g., 'Mentioned knee pain 4 times last month')",
                    "significance": "high|medium|low",
                    "days_missing": 7,
                    "last_date": null
                }}
            ]
        }}
        
        If the user has been consistent and nothing significant is missing, return an empty patterns array.
        """
        
        try:
            result = await self._call_ai(prompt, temperature=0.6)
            patterns = result.get('patterns', [])
            
            # Validate patterns
            valid_patterns = []
            for pattern in patterns:
                if all(key in pattern for key in ['name', 'last_seen', 'significance']):
                    pattern['category'] = pattern.get('category', 'other')
                    pattern['days_missing'] = pattern.get('days_missing', 7)
                    valid_patterns.append(pattern)
            
            return valid_patterns[:5]
            
        except Exception as e:
            logger.error(f"Failed to detect shadow patterns from context: {str(e)}")
            return []
    
    async def detect_shadow_patterns(self, health_data: Dict, user_id: str) -> List[Dict]:
        """Identify patterns that are missing from recent data across ALL health interactions"""
        # Get comprehensive historical data
        historical_data = await self._get_comprehensive_historical_data(user_id, weeks=4)
        current_week_data = await self._get_current_week_comprehensive_data(user_id)
        
        prompt = f"""
        You are analyzing what health topics/concerns a user USUALLY mentions but HASN'T mentioned this week.
        Look across ALL their health interactions: stories, quick scans, deep dives, chats, tracking, etc.
        
        Current Week Activity:
        - Quick scans: {current_week_data.get('quick_scan_topics', [])}
        - Deep dive topics: {current_week_data.get('deep_dive_topics', [])}
        - Chat topics: {current_week_data.get('chat_topics', [])}
        - Symptoms tracked: {current_week_data.get('symptoms', [])}
        - Body parts mentioned: {current_week_data.get('body_parts', [])}
        
        Historical Patterns (previous 4 weeks):
        - Frequently scanned body parts: {historical_data.get('common_body_parts', [])}
        - Recurring symptoms: {historical_data.get('recurring_symptoms', [])}
        - Common health topics: {historical_data.get('common_topics', [])}
        - Regular concerns: {historical_data.get('regular_concerns', [])}
        - Usual medications: {historical_data.get('medications', [])}
        
        Identify 3-5 significant patterns that are MISSING this week.
        These could be:
        1. Symptoms they always mention but haven't this week (e.g., "daily headaches" suddenly not mentioned)
        2. Body parts they frequently scan but ignored this week (e.g., always checking knee pain, now silent)
        3. Health topics they discuss regularly but avoided (e.g., anxiety, sleep issues, diet)
        4. Medications or treatments usually tracked but missing
        5. Wellness activities they stopped mentioning (exercise, meditation, supplements)
        
        For each shadow pattern:
        - name: Brief pattern name (e.g., "Morning exercise routine")
        - category: "exercise", "sleep", "nutrition", "stress", "medication", "symptom", "other"
        - last_seen: Description of when/how it appeared before
        - significance: "high", "medium", or "low" based on health impact
        - days_missing: Approximate days since last mention
        - last_date: ISO date string if known, null otherwise
        
        Return ONLY a JSON object:
        {{
            "patterns": [
                {{
                    "name": "Morning yoga practice",
                    "category": "exercise",
                    "last_seen": "Practiced 4-5 times weekly for stress management",
                    "significance": "high",
                    "days_missing": 7,
                    "last_date": "2024-01-15"
                }}
            ]
        }}
        """
        
        try:
            result = await self._call_ai(prompt, temperature=0.6)
            patterns = result.get('patterns', [])
            
            # Validate patterns
            valid_patterns = []
            for pattern in patterns:
                if all(key in pattern for key in ['name', 'last_seen', 'significance']):
                    pattern['category'] = pattern.get('category', 'other')
                    pattern['days_missing'] = pattern.get('days_missing', 0)
                    valid_patterns.append(pattern)
            
            return valid_patterns[:5]
            
        except Exception as e:
            logger.error(f"Failed to detect shadow patterns: {str(e)}")
            return []
    
    async def generate_insights_from_context(self, llm_context: str, health_data: Dict, user_id: str) -> List[Dict]:
        """Generate insights using the same context as Oracle chat"""
        prompt = f"""
        Analyze this comprehensive health context and generate 4-6 key insights.
        
        HEALTH CONTEXT (same data Oracle uses):
        {llm_context[:3000]}  # Limit to prevent token issues
        
        ADDITIONAL DATA SUMMARY:
        - Total health interactions: {health_data.get('oracle_sessions', {}).get('total_sessions', 0)}
        - Recent symptoms tracked: {len(health_data.get('recent_symptoms', []))}
        - Body parts of concern: {len(health_data.get('body_parts', []))}
        
        Generate insights that are:
        1. Based on patterns in the actual health data
        2. Specific to what the user has been tracking
        3. Actionable and supportive
        4. NOT generic health advice
        
        Focus on:
        - Patterns in symptoms or body parts
        - Changes from previous weeks
        - Areas not mentioned recently (shadow patterns)
        - Correlations between different health aspects
        
        Return ONLY a JSON object:
        {{
            "insights": [
                {{
                    "type": "positive|warning|neutral",
                    "title": "Brief, specific title (max 10 words)",
                    "description": "One detailed sentence about the specific pattern observed",
                    "confidence": 60-95,
                    "metadata": {{
                        "based_on": "specific data source (e.g., 'chest pain tracked 3 times')"
                    }}
                }}
            ]
        }}
        """
        
        try:
            result = await self._call_ai(prompt, temperature=0.6)
            insights = result.get('insights', [])
            
            # Validate and clean insights
            valid_insights = []
            for insight in insights:
                if all(key in insight for key in ['type', 'title', 'description', 'confidence']):
                    # Ensure confidence is within range
                    insight['confidence'] = max(60, min(95, int(insight['confidence'])))
                    # Ensure it's specific, not generic
                    if 'drink water' not in insight['description'].lower() and 'see a doctor' not in insight['title'].lower():
                        valid_insights.append(insight)
            
            return valid_insights[:6]
            
        except Exception as e:
            logger.error(f"Failed to generate insights from context: {str(e)}")
            # Return a context-aware fallback
            return [{
                "type": "neutral",
                "title": "Health tracking active",
                "description": "Your health data is being analyzed. Continue tracking for personalized insights.",
                "confidence": 70,
                "metadata": {"is_fallback": True}
            }]
    
    async def generate_strategies(self, insights: List[Dict], predictions: List[Dict], 
                                patterns: List[Dict], user_id: str) -> List[Dict]:
        """Generate strategic health moves based on all analysis"""
        # Get current week activity for more specific recommendations
        current_week_data = await self._get_current_week_comprehensive_data(user_id)
        
        # Build activity summary
        activity_summary = []
        if current_week_data['quick_scan_topics']:
            activity_summary.append(f"Quick scans focused on: {', '.join(current_week_data['quick_scan_topics'][:3])}")
        if current_week_data['symptoms']:
            activity_summary.append(f"Symptoms tracked: {', '.join(current_week_data['symptoms'][:3])}")
        if current_week_data['body_parts']:
            activity_summary.append(f"Body areas of concern: {', '.join(current_week_data['body_parts'][:3])}")
        
        prompt = f"""
        Based on this week's health activity and analysis, create 5-7 strategic health moves.
        
        This Week's Activity:
        {chr(10).join(activity_summary) if activity_summary else "Limited health tracking this week"}
        
        Key Insights:
        {json.dumps(insights, indent=2)[:800]}
        
        Predictions:
        {json.dumps(predictions, indent=2)[:800]}
        
        Shadow Patterns (things usually mentioned but missing this week):
        {json.dumps(patterns, indent=2)[:800]}
        
        Generate strategic moves that are:
        1. Tailored to what the user ACTUALLY did this week
        2. Specific enough to be actionable but general enough to be flexible
        3. Mix of immediate actions (today/tomorrow) and week-long strategies
        4. Based on their actual tracking patterns and concerns
        
        For each strategy:
        - strategy: Action that relates to their SPECIFIC weekly activity (e.g., "Since you tracked headaches 3 times, try...")
        - type: "discovery" (learn patterns), "pattern" (track correlations), "prevention" (avoid issues), "optimization" (improve wellness)
        - priority: 1-10 (10 being highest)
        - rationale: Connect to their ACTUAL weekly data
        - outcome: Specific benefit based on their patterns
        
        Examples of good strategies:
        - If they tracked knee pain: "Log activities 30 minutes before knee pain episodes to identify triggers"
        - If they mentioned fatigue: "Track caffeine intake alongside your energy levels for 3 days"
        - If pattern is missing: "You usually track sleep but didn't this week - resume sleep logging to maintain insights"
        
        Return ONLY a JSON object:
        {{
            "strategies": [
                {{
                    "strategy": "Since you scanned your chest area twice this week, track any activities that precede chest discomfort",
                    "type": "discovery",
                    "priority": 8,
                    "rationale": "Your chest scans this week suggest concern; activity tracking helps identify triggers",
                    "outcome": "Understand if specific movements or stress triggers your chest symptoms"
                }}
            ]
        }}
        """
        
        try:
            result = await self._call_ai(prompt, temperature=0.7)
            strategies = result.get('strategies', [])
            
            # Validate strategies
            valid_strategies = []
            for strategy in strategies:
                if all(key in strategy for key in ['strategy', 'type', 'priority']):
                    strategy['priority'] = max(1, min(10, int(strategy['priority'])))
                    strategy['rationale'] = strategy.get('rationale', '')
                    strategy['outcome'] = strategy.get('outcome', '')
                    valid_strategies.append(strategy)
            
            # Sort by priority
            valid_strategies.sort(key=lambda x: x['priority'], reverse=True)
            
            return valid_strategies[:7]
            
        except Exception as e:
            logger.error(f"Failed to generate strategies: {str(e)}")
            return [
                {
                    "strategy": "Continue tracking your health symptoms daily",
                    "type": "pattern",
                    "priority": 7,
                    "rationale": "Consistent tracking enables better pattern recognition",
                    "outcome": "Improved understanding of your health patterns"
                }
            ]
    
    async def _get_historical_patterns(self, user_id: str) -> Dict:
        """Get historical patterns for better predictions"""
        try:
            # Get last 30 days of data
            cutoff = (date.today() - timedelta(days=30)).isoformat()
            
            # Get symptom tracking data
            symptoms = supabase.table('symptom_tracking').select(
                'symptom_name, severity, created_at'
            ).eq('user_id', user_id).gte('created_at', cutoff).execute()
            
            # Process into patterns
            symptom_counts = {}
            for record in symptoms.data:
                symptom = record['symptom_name']
                symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1
            
            return {
                'symptom_frequency': symptom_counts,
                'total_tracking_days': len(set(r['created_at'][:10] for r in symptoms.data))
            }
            
        except Exception as e:
            logger.error(f"Failed to get historical patterns: {str(e)}")
            return {}
    
    async def _get_historical_data(self, user_id: str, weeks: int = 4) -> Dict:
        """Get historical health data for comparison"""
        try:
            cutoff = (date.today() - timedelta(weeks=weeks)).isoformat()
            
            # Get various health data points through conversations
            conv_result = supabase.table('conversations').select(
                'id'
            ).eq('user_id', user_id).gte('updated_at', cutoff).execute()
            
            oracle_chats = {'data': []}
            if conv_result.data:
                conv_ids = [c['id'] for c in conv_result.data]
                oracle_chats = supabase.table('messages').select(
                    'content as message, created_at'
                ).in_('conversation_id', conv_ids).execute()
            
            symptom_tracking = supabase.table('symptom_tracking').select(
                'symptom_name, body_part, created_at'
            ).eq('user_id', user_id).gte('created_at', cutoff).execute()
            
            # Process into weekly summaries
            weekly_data = {}
            
            # Group by week
            for chat in oracle_chats.data:
                week = self._get_week_start(chat['created_at'])
                if week not in weekly_data:
                    weekly_data[week] = {
                        'symptoms': set(),
                        'body_parts': set(),
                        'chat_count': 0
                    }
                weekly_data[week]['chat_count'] += 1
            
            for symptom in symptom_tracking.data:
                week = self._get_week_start(symptom['created_at'])
                if week not in weekly_data:
                    weekly_data[week] = {
                        'symptoms': set(),
                        'body_parts': set(),
                        'chat_count': 0
                    }
                weekly_data[week]['symptoms'].add(symptom['symptom_name'])
                if symptom.get('body_part'):
                    weekly_data[week]['body_parts'].add(symptom['body_part'])
            
            # Convert sets to lists for JSON serialization
            for week in weekly_data:
                weekly_data[week]['symptoms'] = list(weekly_data[week]['symptoms'])
                weekly_data[week]['body_parts'] = list(weekly_data[week]['body_parts'])
            
            return weekly_data
            
        except Exception as e:
            logger.error(f"Failed to get historical data: {str(e)}")
            return {}
    
    def _get_week_start(self, date_str: str) -> str:
        """Get the Monday of the week for a given date"""
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        days_since_monday = dt.weekday()
        week_start = dt - timedelta(days=days_since_monday)
        return week_start.date().isoformat()
    
    async def _get_comprehensive_historical_data(self, user_id: str, weeks: int = 4) -> Dict:
        """Get comprehensive historical health data from ALL interactions"""
        try:
            cutoff = (date.today() - timedelta(weeks=weeks)).isoformat()
            now = date.today()
            current_week_start = self._get_week_start(now.isoformat())
            
            data = {
                'common_body_parts': [],
                'recurring_symptoms': [],
                'common_topics': [],
                'regular_concerns': [],
                'medications': []
            }
            
            # 1. Quick Scans - extract body parts and symptoms
            scans = supabase.table('quick_scans').select(
                'body_part, form_data, created_at'
            ).eq('user_id', user_id).gte('created_at', cutoff).lt('created_at', current_week_start).execute()
            
            body_part_counts = {}
            symptom_counts = {}
            
            for scan in (scans.data or []):
                # Count body parts
                body_part = scan.get('body_part', '').lower()
                if body_part:
                    body_part_counts[body_part] = body_part_counts.get(body_part, 0) + 1
                
                # Extract symptoms from form_data
                form_data = scan.get('form_data', {})
                if isinstance(form_data, dict):
                    symptoms = form_data.get('symptoms', '').lower()
                    for symptom in symptoms.split(','):
                        symptom = symptom.strip()
                        if symptom:
                            symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1
            
            # 2. Deep Dives - extract topics and concerns
            dives = supabase.table('deep_dive_sessions').select(
                'body_part, form_data, analysis_result, final_analysis'
            ).eq('user_id', user_id).gte('created_at', cutoff).lt('created_at', current_week_start).execute()
            
            topics = []
            for dive in (dives.data or []):
                if dive.get('body_part'):
                    body_part_counts[dive['body_part'].lower()] = body_part_counts.get(dive['body_part'].lower(), 0) + 1
                
                # Extract topics from analysis
                analysis = dive.get('final_analysis', {})
                if isinstance(analysis, dict):
                    # Look for conditions, concerns, recommendations
                    if 'primaryCondition' in analysis:
                        topics.append(analysis['primaryCondition'])
                    if 'symptoms' in analysis:
                        for symptom in analysis['symptoms']:
                            symptom_counts[symptom.lower()] = symptom_counts.get(symptom.lower(), 0) + 1
            
            # 3. Conversations - extract health topics discussed
            conv_result = supabase.table('conversations').select('id').eq(
                'user_id', user_id
            ).gte('updated_at', cutoff).lt('updated_at', current_week_start).execute()
            
            if conv_result.data:
                conv_ids = [c['id'] for c in conv_result.data]
                messages = supabase.table('messages').select(
                    'content, role'
                ).in_('conversation_id', conv_ids).eq('role', 'user').execute()
                
                # Analyze messages for health topics
                health_keywords = ['pain', 'ache', 'symptom', 'feeling', 'medication', 'doctor', 
                                 'anxiety', 'stress', 'sleep', 'energy', 'fatigue', 'dizzy',
                                 'nausea', 'headache', 'breathing', 'heart', 'stomach']
                
                medication_keywords = ['taking', 'medication', 'pill', 'medicine', 'prescribed',
                                     'tylenol', 'ibuprofen', 'advil', 'aspirin']
                
                for msg in (messages.data or []):
                    content = msg.get('content', '').lower()
                    # Extract health topics
                    for keyword in health_keywords:
                        if keyword in content:
                            topics.append(keyword)
                    
                    # Extract medications
                    for med_keyword in medication_keywords:
                        if med_keyword in content:
                            # Try to extract medication name
                            words = content.split()
                            idx = words.index(med_keyword) if med_keyword in words else -1
                            if idx > 0 and idx < len(words) - 1:
                                data['medications'].append(words[idx + 1])
            
            # 4. Symptom Tracking
            tracking = supabase.table('symptom_tracking').select(
                'symptom_name, body_part'
            ).eq('user_id', user_id).gte('created_at', cutoff).lt('created_at', current_week_start).execute()
            
            for entry in (tracking.data or []):
                symptom = entry.get('symptom_name', '').lower()
                if symptom:
                    symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1
                body_part = entry.get('body_part', '').lower()
                if body_part:
                    body_part_counts[body_part] = body_part_counts.get(body_part, 0) + 1
            
            # Process counts into lists
            # Common = mentioned at least 2 times
            data['common_body_parts'] = [bp for bp, count in body_part_counts.items() if count >= 2]
            data['recurring_symptoms'] = [s for s, count in symptom_counts.items() if count >= 2]
            data['common_topics'] = list(set(topics))[:10]  # Top 10 unique topics
            data['regular_concerns'] = [s for s, count in symptom_counts.items() if count >= 3]
            data['medications'] = list(set(data['medications']))
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive historical data: {str(e)}")
            return {
                'common_body_parts': [],
                'recurring_symptoms': [],
                'common_topics': [],
                'regular_concerns': [],
                'medications': []
            }
    
    async def _get_current_week_comprehensive_data(self, user_id: str) -> Dict:
        """Get all health mentions from current week"""
        try:
            week_start = self._get_week_start(date.today().isoformat())
            
            data = {
                'quick_scan_topics': [],
                'deep_dive_topics': [],
                'chat_topics': [],
                'symptoms': [],
                'body_parts': []
            }
            
            # 1. Quick Scans this week
            scans = supabase.table('quick_scans').select(
                'body_part, form_data'
            ).eq('user_id', user_id).gte('created_at', week_start).execute()
            
            for scan in (scans.data or []):
                if scan.get('body_part'):
                    data['body_parts'].append(scan['body_part'].lower())
                    data['quick_scan_topics'].append(scan['body_part'].lower())
                
                form_data = scan.get('form_data', {})
                if isinstance(form_data, dict):
                    symptoms = form_data.get('symptoms', '').lower()
                    for symptom in symptoms.split(','):
                        symptom = symptom.strip()
                        if symptom:
                            data['symptoms'].append(symptom)
                            data['quick_scan_topics'].append(symptom)
            
            # 2. Deep Dives this week
            dives = supabase.table('deep_dive_sessions').select(
                'body_part, form_data, final_analysis'
            ).eq('user_id', user_id).gte('created_at', week_start).execute()
            
            for dive in (dives.data or []):
                if dive.get('body_part'):
                    data['body_parts'].append(dive['body_part'].lower())
                    data['deep_dive_topics'].append(dive['body_part'].lower())
                
                analysis = dive.get('final_analysis', {})
                if isinstance(analysis, dict) and 'symptoms' in analysis:
                    for symptom in analysis['symptoms']:
                        data['symptoms'].append(symptom.lower())
                        data['deep_dive_topics'].append(symptom.lower())
            
            # 3. Conversations this week
            conv_result = supabase.table('conversations').select('id').eq(
                'user_id', user_id
            ).gte('updated_at', week_start).execute()
            
            if conv_result.data:
                conv_ids = [c['id'] for c in conv_result.data]
                messages = supabase.table('messages').select(
                    'content'
                ).in_('conversation_id', conv_ids).eq('role', 'user').execute()
                
                health_keywords = ['pain', 'ache', 'symptom', 'feeling', 'medication', 
                                 'anxiety', 'stress', 'sleep', 'energy', 'fatigue']
                
                for msg in (messages.data or []):
                    content = msg.get('content', '').lower()
                    for keyword in health_keywords:
                        if keyword in content:
                            data['chat_topics'].append(keyword)
            
            # 4. Symptom Tracking this week
            tracking = supabase.table('symptom_tracking').select(
                'symptom_name, body_part'
            ).eq('user_id', user_id).gte('created_at', week_start).execute()
            
            for entry in (tracking.data or []):
                if entry.get('symptom_name'):
                    data['symptoms'].append(entry['symptom_name'].lower())
                if entry.get('body_part'):
                    data['body_parts'].append(entry['body_part'].lower())
            
            # Remove duplicates
            for key in data:
                data[key] = list(set(data[key]))
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to get current week comprehensive data: {str(e)}")
            return {
                'quick_scan_topics': [],
                'deep_dive_topics': [],
                'chat_topics': [],
                'symptoms': [],
                'body_parts': []
            }