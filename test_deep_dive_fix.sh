#!/bin/bash

echo "Testing Deep Dive with improved JSON handling..."
echo "=============================================="

# Test 1: Start Deep Dive with DeepSeek V3
echo -e "\n1. Starting Deep Dive with DeepSeek V3 (default):"
START_RESPONSE=$(curl -s -X POST http://localhost:8000/api/deep-dive/start \
  -H "Content-Type: application/json" \
  -d '{
    "body_part": "Left Deltoid",
    "form_data": {
      "symptoms": "Sharp pain when lifting arm, worse at night, started 3 days ago"
    }
  }')

echo "$START_RESPONSE" | jq '.'
SESSION_ID=$(echo "$START_RESPONSE" | jq -r '.session_id')
echo "Session ID: $SESSION_ID"

# Test 2: Test Complete with DeepSeek (should get real analysis)
echo -e "\n2. Testing Complete with DeepSeek V3:"
curl -s -X POST http://localhost:8000/api/deep-dive/complete \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\"
  }" | jq '.'

# Test 3: Test with explicit Gemini (to see if JSON extraction works)
echo -e "\n3. Testing Complete with Gemini 2.5 Pro:"
curl -s -X POST http://localhost:8000/api/deep-dive/complete \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"fallback_model\": \"google/gemini-2.5-pro\"
  }" | jq '.'

# Test 4: Check response structure (no double parsing needed)
echo -e "\n4. Checking response structure (should be object, not string):"
RESPONSE=$(curl -s -X POST http://localhost:8000/api/deep-dive/complete \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"fallback_model\": \"deepseek/deepseek-chat\"
  }")

# Show that analysis is an object
echo "$RESPONSE" | jq '.analysis | type'
echo "Analysis confidence (should be number):"
echo "$RESPONSE" | jq '.analysis.confidence'
echo "Primary condition:"
echo "$RESPONSE" | jq '.analysis.primaryCondition'