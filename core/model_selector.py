"""
Tier-based model selection system for Oracle Health API
Handles dynamic model selection based on user subscription tier
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

# Cache for user tiers to reduce database queries
_tier_cache: Dict[str, Dict[str, Any]] = {}
CACHE_DURATION = timedelta(minutes=5)

# Model configuration - Loaded from JSON file or defaults
# This is the fallback configuration if JSON file is not found
MODEL_CONFIG = {
    "free": {
        "chat": {
            "models": ["deepseek/deepseek-chat", "google/gemini-2.0-flash-exp:free"],
            "reasoning_models": ["deepseek/deepseek-r1", "google/gemini-2.5-flash"]
        },
        "quick_scan": ["deepseek/deepseek-chat", "google/gemini-2.0-flash-exp:free"],
        "deep_dive": ["deepseek/deepseek-r1", "google/gemini-2.5-flash"],
        "photo_analysis": ["openai/gpt-5", "google/gemini-2.5-pro"],
        "reports": ["openai/gpt-5", "google/gemini-2.5-pro"],
        "ultra_think": ["x-ai/grok-4", "google/gemini-2.5-pro"],
        "think_harder": ["deepseek/deepseek-r1", "google/gemini-2.5-flash"],
    },
    "basic": {
        "chat": {
            "models": ["google/gemini-2.5-flash", "openai/gpt-5"],
            "reasoning_models": ["openai/gpt-5", "google/gemini-2.5-pro"]
        },
        "quick_scan": ["openai/gpt-5-mini", "google/gemini-2.5-flash"],
        "deep_dive": ["openai/gpt-5", "google/gemini-2.5-pro"],
        "photo_analysis": ["openai/gpt-5", "google/gemini-2.5-pro"],
        "reports": ["openai/gpt-5", "google/gemini-2.5-pro"],
        "ultra_think": ["x-ai/grok-4", "google/gemini-2.5-pro"],
        "think_harder": ["openai/gpt-5-mini", "google/gemini-2.5-pro"],
    },
    "pro": {
        "chat": {
            "models": ["anthropic/claude-4-sonnet", "openai/gpt-5"],
            "reasoning_models": ["openai/gpt-5", "google/gemini-2.5-pro"]
        },
        "quick_scan": ["openai/gpt-5-mini", "google/gemini-2.5-flash"],
        "deep_dive": ["openai/gpt-5", "google/gemini-2.5-pro"],
        "photo_analysis": ["openai/gpt-5", "google/gemini-2.5-pro"],
        "reports": ["openai/gpt-5", "google/gemini-2.5-pro"],
        "ultra_think": ["x-ai/grok-4", "google/gemini-2.5-pro"],
        "think_harder": ["openai/gpt-5-mini", "google/gemini-2.5-pro"],
    },
    "pro_plus": {
        "chat": {
            "models": ["anthropic/claude-4-sonnet", "openai/gpt-5"],
            "reasoning_models": ["openai/gpt-5", "google/gemini-2.5-pro"]
        },
        "quick_scan": ["openai/gpt-5-mini", "google/gemini-2.5-flash"],
        "deep_dive": ["openai/gpt-5", "google/gemini-2.5-pro"],
        "photo_analysis": ["openai/gpt-5", "google/gemini-2.5-pro"],
        "reports": ["openai/gpt-5", "google/gemini-2.5-pro"],
        "ultra_think": ["x-ai/grok-4", "google/gemini-2.5-pro"],
        "think_harder": ["openai/gpt-5-mini", "google/gemini-2.5-pro"],
    }
}

# Load config from JSON file if it exists (allows runtime updates)
def load_model_config():
    """Load model configuration from JSON file if available"""
    config_path = Path(__file__).parent.parent / "config" / "model_tiers.json"
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load model config from file: {e}")
    return MODEL_CONFIG


async def get_user_tier(user_id: str) -> str:
    """
    Get user's subscription tier from database with caching
    Returns: 'free', 'basic', 'pro', 'pro_plus', or 'max'
    """
    if not user_id:
        return "free"
    
    # Check cache first
    if user_id in _tier_cache:
        cached = _tier_cache[user_id]
        if cached['expires'] > datetime.now():
            return cached['tier']
    
    try:
        # Query subscriptions table
        response = supabase.table("subscriptions").select(
            "tier, status, current_period_end"
        ).eq("user_id", user_id).eq("status", "active").execute()
        
        if response.data and len(response.data) > 0:
            subscription = response.data[0]
            
            # Check if subscription is still valid
            if subscription.get("current_period_end"):
                end_date = datetime.fromisoformat(
                    subscription["current_period_end"].replace('Z', '+00:00')
                )
                if end_date > datetime.now(end_date.tzinfo):
                    tier = subscription.get("tier", "free")
                    
                    # Cache the result
                    _tier_cache[user_id] = {
                        'tier': tier,
                        'expires': datetime.now() + CACHE_DURATION
                    }
                    
                    return tier
        
        # No active subscription = free tier
        _tier_cache[user_id] = {
            'tier': 'free',
            'expires': datetime.now() + CACHE_DURATION
        }
        return "free"
        
    except Exception as e:
        logger.error(f"Error fetching user tier: {e}")
        return "free"  # Default to free on error


async def get_models_for_endpoint(
    user_id: str, 
    endpoint: str,
    reasoning_mode: bool = False,
    tier_override: Optional[str] = None
) -> Optional[List[str]]:
    """
    Get list of models for a specific endpoint based on user tier
    
    Args:
        user_id: User ID to check tier for
        endpoint: Type of endpoint (chat, quick_scan, deep_dive, etc.)
        reasoning_mode: Whether to use reasoning models (for chat endpoint)
        tier_override: Optional tier override for testing
    
    Returns:
        List of model names in priority order, or None if not available
    """
    # Load latest config
    config = load_model_config()
    
    # Determine actual tier
    if tier_override:
        tier = tier_override
    else:
        tier = await get_user_tier(user_id)
    
    # Get models for this tier and endpoint
    tier_config = config.get(tier, config.get("free", {}))
    endpoint_config = tier_config.get(endpoint)
    
    if endpoint_config is None:
        logger.info(f"Endpoint {endpoint} not available for tier {tier}")
        return None
    
    # Handle chat endpoint with reasoning mode
    if isinstance(endpoint_config, dict):
        if reasoning_mode and "reasoning_models" in endpoint_config:
            return endpoint_config["reasoning_models"]
        elif "models" in endpoint_config:
            return endpoint_config["models"]
    
    # Regular endpoint - return list directly
    if isinstance(endpoint_config, list):
        return endpoint_config
    
    return None


async def select_model_with_fallback(
    user_id: str,
    endpoint: str,
    reasoning_mode: bool = False,
    preferred_index: int = 0
) -> Optional[str]:
    """
    Select a specific model with fallback options
    
    Args:
        user_id: User ID
        endpoint: Endpoint type
        reasoning_mode: Whether to use reasoning models
        preferred_index: Which model to prefer (0 = primary, 1 = first fallback, etc.)
    
    Returns:
        Model name or None if not available
    """
    models = await get_models_for_endpoint(user_id, endpoint, reasoning_mode)
    
    if not models:
        return None
    
    # Return requested model or last available
    if preferred_index < len(models):
        return models[preferred_index]
    else:
        return models[-1]  # Return last model as ultimate fallback


async def get_user_tier_info(user_id: str) -> Dict[str, Any]:
    """
    Get detailed tier information for a user
    
    Returns dict with:
        - tier: Current tier name
        - model_group: 'free' or 'premium'
        - features: Available features for this tier
    """
    tier = await get_user_tier(user_id)
    model_group = "premium" if tier != "free" else "free"
    
    # Define features by tier
    features = {
        "free": {
            "chat": True,
            "quick_scan": True,
            "deep_dive": True,
            "photo_analysis": True,
            "ultra_think": False,
            "think_harder": False,
            "reports": "basic",
            "max_tokens": 2000,
            "rate_limit_per_hour": 10,
        },
        "basic": {
            "chat": True,
            "quick_scan": True,
            "deep_dive": True,
            "photo_analysis": True,
            "ultra_think": False,
            "think_harder": True,
            "reports": "standard",
            "max_tokens": 4000,
            "rate_limit_per_hour": 50,
        },
        "pro": {
            "chat": True,
            "quick_scan": True,
            "deep_dive": True,
            "photo_analysis": True,
            "ultra_think": True,
            "think_harder": True,
            "reports": "advanced",
            "max_tokens": 8000,
            "rate_limit_per_hour": 200,
        },
        "pro_plus": {
            "chat": True,
            "quick_scan": True,
            "deep_dive": True,
            "photo_analysis": True,
            "ultra_think": True,
            "think_harder": True,
            "reports": "all",
            "max_tokens": 16000,
            "rate_limit_per_hour": 1000,
        },
        "max": {
            "chat": True,
            "quick_scan": True,
            "deep_dive": True,
            "photo_analysis": True,
            "ultra_think": True,
            "think_harder": True,
            "reports": "all",
            "experimental": True,
            "max_tokens": 32000,
            "rate_limit_per_hour": -1,  # Unlimited
        }
    }
    
    return {
        "tier": tier,
        "model_group": model_group,
        "features": features.get(tier, features["free"])
    }


def invalidate_tier_cache(user_id: str):
    """Invalidate cached tier for a user (call after subscription changes)"""
    if user_id in _tier_cache:
        del _tier_cache[user_id]