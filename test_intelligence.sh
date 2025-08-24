#\!/bin/bash

# Test user ID - using a test UUID
USER_ID="550e8400-e29b-41d4-a716-446655440000"

echo "=== TESTING INTELLIGENCE ENDPOINTS ==="
echo ""

echo "1. Body Systems Health:"
curl -s -X GET "http://localhost:8000/api/intelligence/body-systems/${USER_ID}" | jq '.' | head -20
echo ""

echo "2. Health Velocity (30D):"
curl -s -X GET "http://localhost:8000/api/intelligence/health-velocity/${USER_ID}?time_range=30D" | jq '.' | head -20
echo ""

echo "3. Doctor Readiness:"
curl -s -X GET "http://localhost:8000/api/intelligence/doctor-readiness/${USER_ID}" | jq '.' | head -20
echo ""

echo "4. Timeline (30D):"
curl -s -X GET "http://localhost:8000/api/intelligence/timeline/${USER_ID}?time_range=30D" | jq '.' | head -20
echo ""

echo "5. Pattern Discovery:"
curl -s -X GET "http://localhost:8000/api/intelligence/patterns/${USER_ID}?limit=5" | jq '.' | head -20
echo ""

echo "6. Comparative Intelligence:"
curl -s -X GET "http://localhost:8000/api/intelligence/comparative/${USER_ID}" | jq '.' | head -20
echo ""

echo "7. Generate Weekly Brief:"
curl -s -X POST "http://localhost:8000/api/health-brief/generate" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"${USER_ID}\", \"force_regenerate\": true}" | jq '.' | head -20
echo ""

echo "8. Get Current Week Brief:"
curl -s -X GET "http://localhost:8000/api/health-brief/${USER_ID}/current" | jq '.' | head -20
echo ""

echo "=== ALL TESTS COMPLETE ==="
