"""Test script to validate JSON parser with various AI responses"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.json_parser import extract_json_from_response

# Test cases that simulate various AI response formats
test_cases = [
    {
        "name": "Plain JSON",
        "input": '{"category": "medical_normal", "confidence": 0.95}',
        "expected": {"category": "medical_normal", "confidence": 0.95}
    },
    {
        "name": "JSON in code block",
        "input": '''Here's the analysis:
```json
{
  "primary_assessment": "Acne vulgaris",
  "confidence": 85,
  "visual_observations": ["Multiple papules", "Mild inflammation"]
}
```''',
        "expected": {
            "primary_assessment": "Acne vulgaris",
            "confidence": 85,
            "visual_observations": ["Multiple papules", "Mild inflammation"]
        }
    },
    {
        "name": "JSON with markdown wrapper and extra text",
        "input": '''I'll analyze this medical photo:

```json
{
  "category": "medical_normal",
  "confidence": 0.92,
  "subcategory": "dermatological_rash"
}
```

This appears to be a dermatological condition.''',
        "expected": {
            "category": "medical_normal",
            "confidence": 0.92,
            "subcategory": "dermatological_rash"
        }
    },
    {
        "name": "Truncated JSON in code block",
        "input": '''```json
{
  "primary_assessment": "Mole with irregular borders",
  "confidence": 75,
  "visual_observations": [
    "Asymmetric shape",
    "Color variation",
    "Diameter approximately 8mm"
  ],
  "recommendations": [
    "Monitor for changes",
    "Consider dermatologist evaluation"
  ],
  "red_flags": [
    "Irregular borders",
    "Multiple colors present"
  ],
  "trackable_metrics": [
    {
      "metric_name": "diameter",
      "current_value": 8,
      "unit": "mm",
      "suggested_tracking": "monthly"
    }
  ],
  "key_measurements": {
    "size_estimate_mm": 8,
    "size_reference": "larger than pencil eraser (6mm)",
    "primary_color": "dark brown",
    "secondary_colors": ["light brown", "reddish areas"],
    "texture_description": "slightly raised",
    "symmetry_observation": "asymmetric - left side differs from right",
    "elevation_observation": "slightly elevated above skin surface"
  },
  "condition_insights": {
    "most_important_features": [
      "Border irregularity",
      "Color variation",
      "Size (>6mm)"
    ],
    "progression_indicators": {
      "improvement_signs": [
        "No further growth",
        "Color becoming more uniform",
        "Borders becoming more regular"
      ],
      "worsening_signs": [
        "Rapid growth",
        "New colors appearing",
        "Increased asymmetry"
      ]''',  # Truncated JSON
        "expected": {
            "primary_assessment": "Mole with irregular borders",
            "confidence": 75,
            "visual_observations": [
                "Asymmetric shape",
                "Color variation",
                "Diameter approximately 8mm"
            ],
            "recommendations": [
                "Monitor for changes",
                "Consider dermatologist evaluation"
            ],
            "red_flags": [
                "Irregular borders",
                "Multiple colors present"
            ],
            "trackable_metrics": [
                {
                    "metric_name": "diameter",
                    "current_value": 8,
                    "unit": "mm",
                    "suggested_tracking": "monthly"
                }
            ],
            "key_measurements": {
                "size_estimate_mm": 8,
                "size_reference": "larger than pencil eraser (6mm)",
                "primary_color": "dark brown",
                "secondary_colors": ["light brown", "reddish areas"],
                "texture_description": "slightly raised",
                "symmetry_observation": "asymmetric - left side differs from right",
                "elevation_observation": "slightly elevated above skin surface"
            },
            "condition_insights": {
                "most_important_features": [
                    "Border irregularity",
                    "Color variation",
                    "Size (>6mm)"
                ],
                "progression_indicators": {
                    "improvement_signs": [
                        "No further growth",
                        "Color becoming more uniform",
                        "Borders becoming more regular"
                    ],
                    "worsening_signs": [
                        "Rapid growth",
                        "New colors appearing",
                        "Increased asymmetry"
                    ]
                }
            }
        }
    },
    {
        "name": "Already parsed dict",
        "input": {"test": "value", "number": 123},
        "expected": {"test": "value", "number": 123}
    },
    {
        "name": "JSON without code block",
        "input": '''The analysis results:
{
  "trend": "improving",
  "confidence": 90,
  "changes": {
    "size": "reduced by 20%",
    "color": "lighter"
  }
}
That's the complete analysis.''',
        "expected": {
            "trend": "improving",
            "confidence": 90,
            "changes": {
                "size": "reduced by 20%",
                "color": "lighter"
            }
        }
    },
    {
        "name": "Nested JSON with arrays",
        "input": '''```json
{
  "results": [
    {
      "id": 1,
      "status": "active",
      "metrics": [10, 20, 30]
    },
    {
      "id": 2,
      "status": "inactive",
      "metrics": [5, 15, 25]
    }
  ],
  "summary": {
    "total": 2,
    "active_count": 1
  }
}
```''',
        "expected": {
            "results": [
                {
                    "id": 1,
                    "status": "active",
                    "metrics": [10, 20, 30]
                },
                {
                    "id": 2,
                    "status": "inactive",
                    "metrics": [5, 15, 25]
                }
            ],
            "summary": {
                "total": 2,
                "active_count": 1
            }
        }
    },
    {
        "name": "Fallback to question format",
        "input": "Can you describe your symptoms in more detail? When did they first appear?",
        "expected": {
            "question": "Can you describe your symptoms in more detail? When did they first appear?",
            "question_type": "open_ended",
            "internal_analysis": {"extracted": True}
        }
    }
]

def test_json_parser():
    """Run all test cases"""
    print("Testing JSON Parser with various AI response formats...\n")
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases):
        print(f"Test {i+1}: {test['name']}")
        print(f"Input preview: {str(test['input'])[:100]}...")
        
        try:
            result = extract_json_from_response(test['input'])
            
            if result == test['expected']:
                print("✅ PASSED")
                passed += 1
            else:
                print("❌ FAILED - Output mismatch")
                print(f"Expected: {test['expected']}")
                print(f"Got: {result}")
                failed += 1
                
        except Exception as e:
            print(f"❌ FAILED - Exception: {e}")
            failed += 1
        
        print("-" * 60)
    
    print(f"\nTest Results: {passed} passed, {failed} failed")
    
    if failed > 0:
        print("\n⚠️  Some tests failed. The JSON parser may need improvements.")
    else:
        print("\n✅ All tests passed! The JSON parser is working correctly.")

if __name__ == "__main__":
    test_json_parser()