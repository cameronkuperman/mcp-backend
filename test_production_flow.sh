#!/bin/bash
# Test the full production flow: specialty-triage -> specialist report

echo "=== TESTING PRODUCTION FLOW ==="
echo "Step 1: Specialty Triage"
echo "================================"

# Step 1: Call specialty-triage to determine which specialist
echo "Calling /api/report/specialty-triage..."
TRIAGE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/report/specialty-triage \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "45b61b67-175d-48a0-aca6-d0be57609383",
    "quick_scan_ids": ["f9c935f0-8140-40d9-9698-3abf2bbaa34b"],
    "deep_dive_ids": []
  }')

echo "Triage Response:"
echo "$TRIAGE_RESPONSE" | python -m json.tool

# Extract the recommended specialty from the response
SPECIALTY=$(echo "$TRIAGE_RESPONSE" | python -c "import sys, json; data = json.load(sys.stdin); print(data.get('primary_specialty', 'primary-care'))" 2>/dev/null || echo "primary-care")

echo -e "\n\nRecommended Specialty: $SPECIALTY"
echo "================================"
echo "Step 2: Generate Specialist Report"
echo "================================"

# Step 2: Call the specialist endpoint with the analysis_id
echo -e "\nCalling /api/report/$SPECIALTY..."
REPORT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/report/$SPECIALTY \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "cc70d30f-d16e-43f0-adfa-f48f9975c540",
    "user_id": "45b61b67-175d-48a0-aca6-d0be57609383",
    "specialty": "'"$SPECIALTY"'",
    "quick_scan_ids": ["f9c935f0-8140-40d9-9698-3abf2bbaa34b"],
    "deep_dive_ids": [],
    "photo_session_ids": [],
    "general_assessment_ids": [],
    "general_deep_dive_ids": [],
    "flash_assessment_ids": []
  }')

echo "Specialist Report Response:"
echo "$REPORT_RESPONSE" | python -m json.tool

echo -e "\n\n=== EXPECTED BEHAVIOR ==="
echo "1. Triage analyzes quick scan f9c935f0-8140-40d9-9698-3abf2bbaa34b"
echo "2. Triage recommends appropriate specialist (e.g., cardiology, primary-care)"
echo "3. Specialist endpoint creates analysis record cc70d30f-d16e-43f0-adfa-f48f9975c540"
echo "4. Specialist report uses ONLY the specified quick scan ID"
echo "5. Empty arrays should result in NO data loaded for those categories"
echo "6. Report includes 'specialty' field in response"