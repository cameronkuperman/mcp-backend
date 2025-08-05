"""Test orthopedic specialist report generation"""
import asyncio
import json
from datetime import datetime
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_orthopedic_report():
    """Test generating an orthopedic report for the ankle injury"""
    
    # First, we need to create a report analysis
    base_url = "http://localhost:8000"
    
    user_id = "45b61b67-175d-48a0-aca6-d0be57609383"
    deep_dive_id = "276125e5-b159-4c8f-b199-4744ad0ed6d5"
    
    print("Testing Orthopedic Report Generation")
    print("=" * 50)
    print(f"User ID: {user_id}")
    print(f"Deep Dive ID: {deep_dive_id}")
    print()
    
    # Step 1: Create a report analysis
    print("Step 1: Creating report analysis...")
    analysis_data = {
        "user_id": user_id,
        "purpose": "ankle injury assessment",
        "symptom_focus": "ankle sprain",
        "recommended_type": "specialist_focused",
        "report_config": {
            "time_range": {
                "start": "2025-07-20T00:00:00Z",
                "end": "2025-07-23T23:59:59Z"
            },
            "focus_areas": ["musculoskeletal"],
            "include_photos": False
        }
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Create analysis
            response = await client.post(
                f"{base_url}/api/report/analysis",
                json=analysis_data
            )
            if response.status_code != 200:
                print(f"Failed to create analysis: {response.status_code}")
                print(response.text)
                return
            
            analysis_result = response.json()
            analysis_id = analysis_result.get("analysis_id")
            print(f"Analysis created: {analysis_id}")
            
            # Step 2: Generate orthopedic report
            print("\nStep 2: Generating orthopedic report...")
            report_data = {
                "user_id": user_id,
                "analysis_id": analysis_id,
                "deep_dive_ids": [deep_dive_id],
                "specialty": "orthopedics"
            }
            
            response = await client.post(
                f"{base_url}/api/report/orthopedics",
                json=report_data
            )
            
            if response.status_code != 200:
                print(f"Failed to generate report: {response.status_code}")
                print(response.text)
                return
            
            report_result = response.json()
            report_id = report_result.get("report_id")
            print(f"Report generated: {report_id}")
            print(f"Status: {report_result.get('status')}")
            
            # Save the report data
            with open('orthopedic_report_output.json', 'w') as f:
                json.dump(report_result, f, indent=2)
            print("\nFull report saved to orthopedic_report_output.json")
            
            # Print key findings
            if report_result.get("report_data"):
                report = report_result["report_data"]
                if report.get("executive_summary"):
                    print("\n=== EXECUTIVE SUMMARY ===")
                    print(report["executive_summary"].get("one_page_summary", "N/A"))
                    
                if report.get("clinical_scales"):
                    print("\n=== CLINICAL SCALES ===")
                    for scale_name, scale_data in report.get("clinical_scales", {}).items():
                        print(f"\n{scale_name}:")
                        print(f"  Score: {scale_data.get('calculated', 'N/A')}")
                        print(f"  Confidence: {scale_data.get('confidence', 'N/A')}")
                        print(f"  Reasoning: {scale_data.get('reasoning', 'N/A')}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("Make sure the Oracle server is running on port 8000!")
    print("Press Enter to continue...")
    input()
    asyncio.run(test_orthopedic_report())