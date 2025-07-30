#!/bin/bash

# AI Predictions API Test Script
# Usage: ./test_ai_endpoints.sh [USER_ID]

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${API_URL:-http://localhost:8000}"
USER_ID="${1:-test-user-123}"

echo -e "${YELLOW}🚀 Testing AI Predictions API${NC}"
echo "Base URL: $BASE_URL"
echo "User ID: $USER_ID"
echo "----------------------------------------"

# Test Dashboard Alert
echo -e "\n${GREEN}1. Testing Dashboard Alert${NC}"
echo "GET /api/ai/dashboard-alert/$USER_ID"
curl -s -X GET "$BASE_URL/api/ai/dashboard-alert/$USER_ID" | jq '.'

# Test Predictions
echo -e "\n${GREEN}2. Testing AI Predictions${NC}"
echo "GET /api/ai/predictions/$USER_ID"
curl -s -X GET "$BASE_URL/api/ai/predictions/$USER_ID" | jq '.'

# Test Pattern Questions
echo -e "\n${GREEN}3. Testing Pattern Questions${NC}"
echo "GET /api/ai/pattern-questions/$USER_ID"
curl -s -X GET "$BASE_URL/api/ai/pattern-questions/$USER_ID" | jq '.'

# Test Body Patterns
echo -e "\n${GREEN}4. Testing Body Patterns${NC}"
echo "GET /api/ai/body-patterns/$USER_ID"
curl -s -X GET "$BASE_URL/api/ai/body-patterns/$USER_ID" | jq '.'

echo -e "\n${YELLOW}✨ All tests completed!${NC}"
echo -e "\nTip: If you see empty results, create some test data first:"
echo -e "python test_ai_predictions.py --create-data"