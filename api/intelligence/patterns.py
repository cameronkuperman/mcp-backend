"""
Pattern Discovery Module - Integrates with existing pattern detection
Enhances existing insights/shadow patterns with card-based interface
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import logging

from supabase_client import supabase
from api.health_analysis import (
    generate_insights_only,
    generate_shadow_patterns_only,
    generate_predictions_only,
    get_current_week_monday
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/intelligence/patterns", tags=["patterns"])

class PatternCard(BaseModel):
    id: str
    type: str  # 'correlation' | 'prediction' | 'success' | 'environmental' | 'behavioral'
    priority: str  # 'high' | 'medium' | 'low'
    front: Dict[str, Any]
    back: Dict[str, Any]

@router.get("/{user_id}")
async def get_pattern_discovery_cards(
    user_id: str, 
    limit: int = 10,
    time_range: str = "30D"
):
    """
    Get pattern discovery cards combining insights, predictions, and shadow patterns
    Reuses existing intelligence endpoints and formats as interactive cards
    """
    try:
        logger.info(f"Generating pattern cards for user {user_id}")
        week_of = get_current_week_monday()
        
        # Fetch existing intelligence components
        insights = supabase.table('health_insights').select('*').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).order('confidence', desc=True).limit(5).execute()
        
        predictions = supabase.table('health_predictions').select('*').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).order('probability', desc=True).limit(5).execute()
        
        shadow_patterns = supabase.table('shadow_patterns').select('*').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).order('significance').limit(5).execute()
        
        # If no existing data, generate it
        if not insights.data and not predictions.data and not shadow_patterns.data:
            logger.info("No existing patterns, generating new ones")
            # Generate all intelligence components
            await generate_insights_only(user_id, force_refresh=False)
            await generate_predictions_only(user_id, force_refresh=False)
            await generate_shadow_patterns_only(user_id, force_refresh=False)
            
            # Re-fetch after generation
            insights = supabase.table('health_insights').select('*').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).order('confidence', desc=True).limit(5).execute()
            
            predictions = supabase.table('health_predictions').select('*').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).order('probability', desc=True).limit(5).execute()
            
            shadow_patterns = supabase.table('shadow_patterns').select('*').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).order('significance').limit(5).execute()
        
        # Convert to pattern cards
        cards = []
        
        # Convert insights to correlation cards
        for insight in (insights.data or [])[:3]:
            card = PatternCard(
                id=insight['id'],
                type='correlation',
                priority='high' if insight['confidence'] > 80 else 'medium' if insight['confidence'] > 60 else 'low',
                front={
                    'icon': '',
                    'headline': insight['title'],
                    'confidence': insight['confidence'],
                    'dataPoints': 10,  # Would calculate from actual data
                    'actionable': True
                },
                back={
                    'fullInsight': insight['description'],
                    'visualization': 'correlation',
                    'actions': [
                        {'text': 'Track this pattern', 'type': 'primary'},
                        {'text': 'View details', 'type': 'secondary'}
                    ],
                    'explanation': f"Based on {insight.get('metadata', {}).get('context_tokens', 'multiple')} data points analyzed"
                }
            )
            cards.append(card)
        
        # Convert predictions to prediction cards
        for pred in (predictions.data or [])[:3]:
            card = PatternCard(
                id=pred['id'],
                type='prediction',
                priority='high' if pred['probability'] > 75 else 'medium' if pred['probability'] > 50 else 'low',
                front={
                    'icon': '',
                    'headline': pred['event_description'][:50] + '...' if len(pred['event_description']) > 50 else pred['event_description'],
                    'confidence': pred['probability'],
                    'dataPoints': 15,
                    'actionable': pred.get('preventable', False)
                },
                back={
                    'fullInsight': pred['event_description'],
                    'visualization': 'timeline',
                    'actions': [
                        {'text': action, 'type': 'primary' if i == 0 else 'secondary'}
                        for i, action in enumerate(pred.get('suggested_actions', [])[:2])
                    ],
                    'explanation': pred.get('reasoning', 'Pattern-based prediction')
                }
            )
            cards.append(card)
        
        # Convert shadow patterns to behavioral cards
        for pattern in (shadow_patterns.data or [])[:2]:
            card = PatternCard(
                id=pattern['id'],
                type='behavioral',
                priority=pattern['significance'],
                front={
                    'icon': '',
                    'headline': f"Missing: {pattern['pattern_name']}",
                    'confidence': 85,  # Shadow patterns have high confidence
                    'dataPoints': pattern.get('days_missing', 7),
                    'actionable': True
                },
                back={
                    'fullInsight': pattern['last_seen_description'],
                    'visualization': 'comparison',
                    'actions': [
                        {'text': 'Resume tracking', 'type': 'primary'},
                        {'text': 'Dismiss pattern', 'type': 'secondary'}
                    ],
                    'explanation': f"Not tracked for {pattern.get('days_missing', 'several')} days"
                }
            )
            cards.append(card)
        
        # Add a success pattern if improvements found
        if insights.data:
            positive_insights = [i for i in insights.data if i.get('insight_type') == 'positive']
            if positive_insights:
                success = positive_insights[0]
                card = PatternCard(
                    id=f"success-{success['id']}",
                    type='success',
                    priority='medium',
                    front={
                        'icon': '',
                        'headline': f"Success: {success['title']}",
                        'confidence': success['confidence'],
                        'dataPoints': 20,
                        'actionable': False
                    },
                    back={
                        'fullInsight': success['description'],
                        'visualization': 'chart',
                        'actions': [
                            {'text': 'Continue this approach', 'type': 'primary'}
                        ],
                        'explanation': 'Positive pattern detected in your health data'
                    }
                )
                cards.append(card)
        
        # Sort by priority and limit
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        cards.sort(key=lambda x: priority_order.get(x.priority, 3))
        cards = cards[:limit]
        
        logger.info(f"Generated {len(cards)} pattern cards for user {user_id}")
        return cards
        
    except Exception as e:
        logger.error(f"Failed to generate pattern cards: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate pattern cards: {str(e)}")