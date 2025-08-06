#!/bin/bash
# Test primary-care endpoint with exact request structure

echo "Testing primary-care endpoint with specific IDs..."
echo "================================================"

curl -X POST http://localhost:8000/api/report/primary-care \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "cc70d30f-d16e-43f0-adfa-f48f9975c540",
    "user_id": "45b61b67-175d-48a0-aca6-d0be57609383",
    "specialty": "primary-care",
    "quick_scan_ids": [
      "f9c935f0-8140-40d9-9698-3abf2bbaa34b"
    ],
    "deep_dive_ids": [],
    "photo_session_ids": [],
    "general_assessment_ids": [],
    "general_deep_dive_ids": [],
    "flash_assessment_ids": []
  }' | python -m json.tool

echo -e "\n\nExpected behavior:"
echo "1. Backend creates analysis record with ID: cc70d30f-d16e-43f0-adfa-f48f9975c540"
echo "2. Backend loads ONLY quick scan: f9c935f0-8140-40d9-9698-3abf2bbaa34b"
echo "3. Backend returns report with specialty: primary-care"
echo "4. NO other data should be loaded (empty arrays mean NO data)"