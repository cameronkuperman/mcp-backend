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
        self.timeout = 90  # Longer timeout for complex analysis
        
    async def _call_ai(self, prompt: str, temperature: float = 0.7) -> Dict:
        """Make API call to Gemini 2.5 Pro via OpenRouter"""
        try:
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
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert health intelligence analyst. Provide supportive, actionable insights based on health data patterns. Never diagnose conditions. Focus on patterns, correlations, and wellness optimization. Always return valid JSON."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": temperature,
                        "max_tokens": 4000
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"AI API error: {response.status_code} - {response.text}")
                    raise Exception(f"AI API error: {response.status_code}")
                
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Extract JSON from the response
                return self._extract_json(content)
                
        except Exception as e:
            logger.error(f"AI call failed: {str(e)}")
            raise
    
    def _extract_json(self, content: str) -> Dict:
        """Extract JSON from AI response, handling various formats"""
        content = content.strip()
        
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
        content = content.replace("'", '"')  # Replace single quotes
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Content: {content[:500]}...")
            # Return a safe default
            return {}
    
    async def generate_insights(self, story: str, health_data: Dict, user_id: str) -> List[Dict]:
        """Generate key health insights from the story and data"""
        prompt = f"""
        Analyze this health story and data to generate 4-6 key insights.
        
        Health Story:
        {story[:2000]}  # Limit story length to avoid token issues
        
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
    
    async def detect_shadow_patterns(self, health_data: Dict, user_id: str) -> List[Dict]:
        """Identify patterns that are missing from recent data"""
        # Get historical data for comparison
        historical_data = await self._get_historical_data(user_id, weeks=4)
        
        prompt = f"""
        Compare current health data with historical patterns to identify what's missing.
        
        Current Week Data:
        - Symptoms mentioned: {health_data.get('recent_symptoms', [])}
        - Activities tracked: {health_data.get('activities', [])}
        - Body parts noted: {health_data.get('body_parts', [])}
        - Tracking frequency: {health_data.get('tracking_frequency', 'unknown')}
        
        Historical Patterns (last 4 weeks):
        {json.dumps(historical_data, indent=2)[:1500]}
        
        Identify 3-5 patterns that were previously prominent but are missing this week.
        Focus on:
        1. Regular activities not mentioned (exercise, meditation, etc.)
        2. Symptoms that disappeared (could be good or concerning)
        3. Tracking habits that changed
        4. Wellness practices not continued
        
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
    
    async def generate_strategies(self, insights: List[Dict], predictions: List[Dict], 
                                patterns: List[Dict], user_id: str) -> List[Dict]:
        """Generate strategic health moves based on all analysis"""
        prompt = f"""
        Based on these health insights, predictions, and missing patterns, create 5-7 strategic health moves.
        
        Key Insights:
        {json.dumps(insights, indent=2)[:1000]}
        
        Predictions:
        {json.dumps(predictions, indent=2)[:1000]}
        
        Shadow Patterns (missing):
        {json.dumps(patterns, indent=2)[:1000]}
        
        Generate strategic moves that are:
        1. Specific and actionable (can be done this week)
        2. Based on the analysis above
        3. Focused on discovery, prevention, or optimization
        4. Realistic and achievable
        
        For each strategy:
        - strategy: Specific action to take (one clear sentence)
        - type: "discovery" (learn something new), "pattern" (track correlation), "prevention" (avoid issues), "optimization" (improve wellness)
        - priority: 1-10 (10 being highest priority)
        - rationale: Why this strategy is recommended
        - outcome: Expected benefit if followed
        
        Prioritize strategies that:
        - Address high-confidence warnings
        - Leverage positive patterns
        - Fill important shadow patterns
        - Prevent predicted issues
        
        Return ONLY a JSON object:
        {{
            "strategies": [
                {{
                    "strategy": "Track energy levels hourly for 3 days to identify patterns",
                    "type": "discovery",
                    "priority": 8,
                    "rationale": "Energy fluctuations predicted; need data to understand triggers",
                    "outcome": "Identify specific times and triggers for energy dips"
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
            
            # Get various health data points
            oracle_chats = supabase.table('oracle_chats').select(
                'message, created_at'
            ).eq('user_id', user_id).gte('created_at', cutoff).execute()
            
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