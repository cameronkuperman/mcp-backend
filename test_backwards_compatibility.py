"""Test JSON parser backwards compatibility"""
from utils.json_parser import extract_json_from_response

# Test cases
tests = [
    ("Plain JSON", '{"category": "medical_normal", "confidence": 0.95}'),
    ("Dict input", {"test": "value", "number": 123}),
    ("JSON no wrapper", '{"trend": "improving", "confidence": 90}'),
    ("Markdown wrapped", '```json\n{"category": "medical_normal", "confidence": 0.95}\n```')
]

print("Testing backwards compatibility...\n")
all_pass = True

for name, test_input in tests:
    try:
        result = extract_json_from_response(test_input)
        if result:
            print(f"✅ {name}: PASSED")
        else:
            print(f"❌ {name}: FAILED - returned None")
            all_pass = False
    except Exception as e:
        print(f"❌ {name}: ERROR - {e}")
        all_pass = False

print(f"\n{'✅ All tests passed - safe to use!' if all_pass else '⚠️  Some tests failed'}")

# Test that prompts are correct
print("\nChecking prompts...")
import os
if os.path.exists("api/photo_analysis.py"):
    with open("api/photo_analysis.py", "r") as f:
        content = f.read()
        if "CRITICAL: Output ONLY valid JSON" in content:
            print("✅ Prompts already tell AI to output only JSON")
        else:
            print("❌ Prompts need updating")