#!/bin/bash

# Test Deep Dive Complete endpoint with curl
echo "Testing Deep Dive API endpoints..."
echo "================================="

# Replace with your actual session ID from the console logs
SESSION_ID="354eb91b-f454-46be-b5ed-e015ae622450"

# Test Deep Dive Complete
echo "Testing Deep Dive Complete..."
curl -X POST http://localhost:8000/api/deep-dive/complete \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"final_answer\": null,
    \"fallback_model\": \"google/gemini-2.5-pro\"
  }" | jq '.'

echo -e "\n\nTesting with different model..."
curl -X POST http://localhost:8000/api/deep-dive/complete \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"final_answer\": null,
    \"fallback_model\": \"deepseek/deepseek-chat\"
  }" | jq '.'