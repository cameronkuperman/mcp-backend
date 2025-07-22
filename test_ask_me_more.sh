#!/bin/bash

echo "Testing Ask Me More Fix..."
echo "========================="

# Use a real session ID from your logs
SESSION_ID="d8209e32-8e54-4a7d-abe1-284b3c258613"

# Test 1: Ask for more questions when confidence is low
echo -e "\n1. Testing Ask Me More (should return a question, not 'max reached'):"
curl -s -X POST http://localhost:8000/api/deep-dive/ask-more \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"current_confidence\": 70,
    \"target_confidence\": 90,
    \"max_questions\": 5
  }" | jq '.'

# Test 2: Test when already at target confidence
echo -e "\n2. Testing when already at target confidence:"
curl -s -X POST http://localhost:8000/api/deep-dive/ask-more \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"current_confidence\": 92,
    \"target_confidence\": 90,
    \"max_questions\": 5
  }" | jq '.'

# Test 3: Verify question structure
echo -e "\n3. Checking response structure:"
RESPONSE=$(curl -s -X POST http://localhost:8000/api/deep-dive/ask-more \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"current_confidence\": 75,
    \"target_confidence\": 95,
    \"max_questions\": 5
  }")

echo "$RESPONSE" | jq '{
  has_question: (.question != null),
  question_number: .question_number,
  confidence_gap: .confidence_gap,
  questions_remaining: .max_questions_remaining
}'