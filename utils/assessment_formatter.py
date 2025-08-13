"""
Assessment Response Formatter
Provides consistent formatting for health assessment responses with new enhanced fields
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


def add_general_assessment_fields(
    existing_data: Dict[str, Any],
    llm_generated: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Add all new fields for General Assessment responses.
    
    Args:
        existing_data: Current response data
        llm_generated: Optional LLM-generated fields to use
    
    Returns:
        Enhanced response with all new fields
    """
    enhanced = existing_data.copy()
    
    # Use LLM-generated fields if available, otherwise generate defaults
    if llm_generated:
        enhanced["severity_level"] = llm_generated.get("severity_level", "moderate")
        enhanced["confidence_level"] = llm_generated.get("confidence_level", "medium")
        enhanced["what_this_means"] = llm_generated.get("what_this_means", 
            "Your symptoms require further evaluation.")
        enhanced["immediate_actions"] = llm_generated.get("immediate_actions", [
            "Monitor your symptoms",
            "Rest and stay hydrated",
            "Note any changes"
        ])
        enhanced["red_flags"] = llm_generated.get("red_flags", [
            "Sudden severe symptoms",
            "Difficulty breathing",
            "Chest pain or pressure"
        ])
        enhanced["tracking_metrics"] = llm_generated.get("tracking_metrics", [
            "Daily symptom severity (1-10)",
            "Energy levels morning and evening",
            "Any new symptoms"
        ])
        enhanced["follow_up_timeline"] = llm_generated.get("follow_up_timeline", {
            "check_progress": "3 days",
            "see_doctor_if": "No improvement in 1 week or symptoms worsen"
        })
    else:
        # Generate from existing data
        urgency = existing_data.get("analysis", {}).get("urgency", "medium")
        enhanced["severity_level"] = determine_severity_from_urgency(urgency)
        
        confidence = existing_data.get("analysis", {}).get("confidence", 70)
        enhanced["confidence_level"] = determine_confidence_from_score(confidence)
        
        # Generate what_this_means from primary assessment
        primary = existing_data.get("analysis", {}).get("primary_assessment", "")
        enhanced["what_this_means"] = f"{primary} This assessment is based on the information you provided." if primary else "Your symptoms require further evaluation."
        
        # Use existing recommendations as immediate actions
        recommendations = existing_data.get("analysis", {}).get("recommendations", [])
        enhanced["immediate_actions"] = recommendations[:3] if recommendations else [
            "Monitor your symptoms",
            "Rest and stay hydrated", 
            "Note any changes"
        ]
        
        enhanced["red_flags"] = [
            "Sudden severe symptoms",
            "Difficulty breathing",
            "Chest pain or pressure"
        ]
        
        enhanced["tracking_metrics"] = [
            "Daily symptom severity (1-10)",
            "Energy levels morning and evening",
            "Any new symptoms"
        ]
        
        enhanced["follow_up_timeline"] = {
            "check_progress": "3 days",
            "see_doctor_if": "No improvement in 1 week or symptoms worsen"
        }
    
    logger.info(f"Added general assessment fields. Severity: {enhanced['severity_level']}, Confidence: {enhanced['confidence_level']}")
    return enhanced


def add_minimal_fields(
    existing_data: Dict[str, Any],
    what_this_means: Optional[str] = None,
    immediate_actions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Add minimal fields for Quick Scan and Deep Dive responses.
    
    Args:
        existing_data: Current response data
        what_this_means: Plain English explanation
        immediate_actions: List of immediate actions
    
    Returns:
        Enhanced response with minimal new fields
    """
    enhanced = existing_data.copy()
    
    # Add what_this_means
    if what_this_means:
        enhanced["what_this_means"] = what_this_means
    elif "analysis" in existing_data:
        analysis = existing_data["analysis"]
        primary = analysis.get("primaryCondition", "")
        symptoms = analysis.get("symptoms", [])
        if primary:
            symptom_text = f"including {', '.join(symptoms[:2])}" if symptoms else ""
            enhanced["what_this_means"] = f"Your symptoms {symptom_text} suggest {primary}. This is a preliminary assessment based on the information provided."
        else:
            enhanced["what_this_means"] = "Based on your symptoms, further evaluation is recommended to determine the underlying cause."
    else:
        enhanced["what_this_means"] = "Your symptoms have been analyzed. Please review the recommendations below."
    
    # Add immediate_actions
    if immediate_actions:
        enhanced["immediate_actions"] = immediate_actions
    elif "analysis" in existing_data:
        # Try to use selfCare or recommendations
        analysis = existing_data["analysis"]
        if "selfCare" in analysis and analysis["selfCare"]:
            enhanced["immediate_actions"] = analysis["selfCare"][:3]
        elif "recommendations" in analysis and analysis["recommendations"]:
            enhanced["immediate_actions"] = analysis["recommendations"][:3]
        else:
            enhanced["immediate_actions"] = [
                "Monitor your symptoms closely",
                "Rest and maintain hydration",
                "Seek medical care if symptoms worsen"
            ]
    else:
        enhanced["immediate_actions"] = [
            "Monitor your symptoms",
            "Follow the recommendations provided",
            "Consult a healthcare provider if concerned"
        ]
    
    logger.info("Added minimal fields (what_this_means, immediate_actions)")
    return enhanced


def determine_severity_from_urgency(urgency: str) -> str:
    """Convert urgency to severity level."""
    mapping = {
        "low": "low",
        "medium": "moderate",
        "high": "high",
        "emergency": "urgent",
        "urgent": "urgent"
    }
    return mapping.get(urgency.lower(), "moderate")


def determine_confidence_from_score(confidence: float) -> str:
    """Convert confidence score to level."""
    if confidence >= 80:
        return "high"
    elif confidence >= 60:
        return "medium"
    else:
        return "low"


def enhance_general_assessment_prompt(base_prompt: str) -> str:
    """
    Enhance prompt for General Assessment to include new fields.
    """
    additional = """

IMPORTANT: Also provide these additional fields in your JSON response:

1. "severity_level": Assess overall severity as "low", "moderate", "high", or "urgent"
2. "confidence_level": Your confidence in the assessment as "low", "medium", or "high"
3. "what_this_means": A 2-3 sentence plain English explanation of what the symptoms indicate, avoiding medical jargon. Focus on helping the patient understand their situation.
4. "immediate_actions": List 3-5 specific, actionable steps the patient can take right now
5. "red_flags": List specific warning signs that would require immediate medical attention
6. "tracking_metrics": List 3-4 specific symptoms or measurements to monitor daily (include how to measure)
7. "follow_up_timeline": Object with two fields:
   - "check_progress": When to reassess (e.g., "3 days")
   - "see_doctor_if": Specific conditions for seeking medical care

Example for what_this_means:
- Good: "Your fatigue and difficulty concentrating suggest your body is dealing with stress, which is depleting your energy reserves. This pattern is common and usually responds well to lifestyle adjustments."
- Avoid: "You have chronic fatigue syndrome with cognitive dysfunction."
"""
    return base_prompt + additional


def enhance_quickscan_prompt(base_prompt: str) -> str:
    """
    Enhance Quick Scan prompt to include minimal new fields.
    """
    additional = """

Additionally include in your JSON response:
- "what_this_means": A clear, non-medical explanation of what the symptoms indicate (2-3 sentences)
- "immediate_actions": List 3-5 specific actions to take right now based on the symptoms

Make these patient-friendly and actionable."""
    return base_prompt + additional


def enhance_deepdive_prompt(base_prompt: str) -> str:
    """
    Enhance Deep Dive prompt to include minimal new fields.
    """
    additional = """

In your final analysis, also include:
- "what_this_means": A comprehensive but clear explanation of your findings based on the full Q&A session (2-3 sentences, avoid medical jargon)
- "immediate_actions": List 3-5 personalized actions based on the deep dive findings

These should reflect the detailed understanding gained from the diagnostic conversation."""
    return base_prompt + additional