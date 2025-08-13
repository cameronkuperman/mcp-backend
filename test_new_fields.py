#!/usr/bin/env python3
"""Test script to verify the new field implementations"""

import json
import logging
import sys
sys.path.append('.')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the formatter functions
from utils.assessment_formatter import (
    add_general_assessment_fields,
    add_minimal_fields,
    determine_severity_from_urgency,
    determine_confidence_from_score
)

def test_minimal_fields():
    """Test minimal field addition for Quick Scan and Deep Dive"""
    logger.info("Testing minimal field addition...")
    
    # Test data simulating Quick Scan response
    quick_scan_data = {
        "scan_id": "test-123",
        "analysis": {
            "confidence": 85,
            "primaryCondition": "Tension Headache",
            "symptoms": ["headache", "neck pain"],
            "recommendations": ["Rest", "Hydrate", "OTC pain relief"],
            "selfCare": ["Apply cold compress", "Reduce screen time", "Practice relaxation"],
            "urgency": "low"
        },
        "body_part": "head",
        "status": "success"
    }
    
    # Apply minimal fields
    enhanced = add_minimal_fields(quick_scan_data)
    
    # Check if new fields are added
    assert "what_this_means" in enhanced, "Missing what_this_means field"
    assert "immediate_actions" in enhanced, "Missing immediate_actions field"
    assert len(enhanced["immediate_actions"]) > 0, "immediate_actions should not be empty"
    
    logger.info(f"✅ Minimal fields test passed")
    logger.info(f"  - what_this_means: {enhanced['what_this_means'][:100]}...")
    logger.info(f"  - immediate_actions: {enhanced['immediate_actions']}")
    
    return enhanced

def test_general_assessment_fields():
    """Test full field addition for General Assessment"""
    logger.info("\nTesting general assessment field addition...")
    
    # Test data simulating General Assessment response
    assessment_data = {
        "assessment_id": "test-456",
        "analysis": {
            "primary_assessment": "Chronic stress affecting energy levels",
            "confidence": 75,
            "urgency": "medium",
            "recommendations": [
                "Establish regular sleep schedule",
                "Practice stress management",
                "Consider counseling"
            ]
        }
    }
    
    # Apply all general assessment fields
    enhanced = add_general_assessment_fields(assessment_data)
    
    # Check if all new fields are added
    required_fields = [
        "severity_level", "confidence_level", "what_this_means",
        "immediate_actions", "red_flags", "tracking_metrics", "follow_up_timeline"
    ]
    
    for field in required_fields:
        assert field in enhanced, f"Missing {field} field"
    
    # Check follow_up_timeline structure
    assert "check_progress" in enhanced["follow_up_timeline"], "Missing check_progress in timeline"
    assert "see_doctor_if" in enhanced["follow_up_timeline"], "Missing see_doctor_if in timeline"
    
    logger.info(f"✅ General assessment fields test passed")
    logger.info(f"  - severity_level: {enhanced['severity_level']}")
    logger.info(f"  - confidence_level: {enhanced['confidence_level']}")
    logger.info(f"  - what_this_means: {enhanced['what_this_means'][:100]}...")
    logger.info(f"  - immediate_actions: {enhanced['immediate_actions'][:2]}")
    logger.info(f"  - red_flags: {enhanced['red_flags'][:2]}")
    logger.info(f"  - tracking_metrics: {enhanced['tracking_metrics'][:2]}")
    logger.info(f"  - follow_up_timeline: {enhanced['follow_up_timeline']}")
    
    return enhanced

def test_helper_functions():
    """Test helper functions"""
    logger.info("\nTesting helper functions...")
    
    # Test severity determination
    assert determine_severity_from_urgency("low") == "low"
    assert determine_severity_from_urgency("medium") == "moderate"
    assert determine_severity_from_urgency("high") == "high"
    assert determine_severity_from_urgency("emergency") == "urgent"
    logger.info("✅ Severity determination test passed")
    
    # Test confidence determination
    assert determine_confidence_from_score(90) == "high"
    assert determine_confidence_from_score(70) == "medium"
    assert determine_confidence_from_score(40) == "low"
    logger.info("✅ Confidence determination test passed")

def test_llm_generated_fields():
    """Test with LLM-generated fields"""
    logger.info("\nTesting with LLM-generated fields...")
    
    # Simulate LLM response with new fields
    llm_response = {
        "primary_assessment": "Stress-related fatigue",
        "confidence": 82,
        "urgency": "medium",
        "severity_level": "moderate",
        "confidence_level": "high",
        "what_this_means": "Your symptoms indicate your body is experiencing fatigue from prolonged stress. This is a common pattern that typically improves with lifestyle adjustments.",
        "immediate_actions": [
            "Take a 20-minute rest break now",
            "Drink 2 glasses of water",
            "Practice 5 minutes of deep breathing",
            "Go to bed 30 minutes earlier tonight"
        ],
        "red_flags": [
            "Chest pain or heart palpitations",
            "Severe headache with vision changes",
            "Extreme fatigue preventing daily activities"
        ],
        "tracking_metrics": [
            "Energy level 1-10 (morning and evening)",
            "Hours of actual sleep each night",
            "Number of rest breaks taken during the day",
            "Stress level 1-10 before bed"
        ],
        "follow_up_timeline": {
            "check_progress": "3 days",
            "see_doctor_if": "No improvement after 1 week or symptoms worsen"
        }
    }
    
    # Apply formatter with LLM-generated data
    enhanced = add_general_assessment_fields({}, llm_generated=llm_response)
    
    # Verify LLM fields are used
    assert enhanced["what_this_means"] == llm_response["what_this_means"]
    assert enhanced["immediate_actions"] == llm_response["immediate_actions"]
    assert enhanced["severity_level"] == "moderate"
    assert enhanced["confidence_level"] == "high"
    
    logger.info("✅ LLM-generated fields test passed")
    logger.info(f"  - Used LLM's what_this_means: {enhanced['what_this_means'][:50]}...")
    logger.info(f"  - Used LLM's immediate_actions count: {len(enhanced['immediate_actions'])}")

def main():
    """Run all tests"""
    logger.info("="*60)
    logger.info("Starting New Fields Implementation Tests")
    logger.info("="*60)
    
    try:
        # Run tests
        test_minimal_fields()
        test_general_assessment_fields()
        test_helper_functions()
        test_llm_generated_fields()
        
        logger.info("\n" + "="*60)
        logger.info("✅ ALL TESTS PASSED SUCCESSFULLY!")
        logger.info("="*60)
        logger.info("\nSummary:")
        logger.info("- Minimal fields (Quick Scan/Deep Dive): Working ✅")
        logger.info("- General Assessment fields: Working ✅")
        logger.info("- Helper functions: Working ✅")
        logger.info("- LLM-generated field handling: Working ✅")
        logger.info("\nThe implementation is ready for production use.")
        
    except AssertionError as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()