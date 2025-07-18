#!/usr/bin/env python3
"""Debug script to check report data in Supabase"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json
from datetime import datetime, timezone, timedelta

load_dotenv()

# Initialize Supabase client
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY/ANON_KEY must be set in .env file")
    exit(1)

supabase: Client = create_client(url, key)

def check_reports():
    """Check recent reports in the database"""
    print("Checking recent reports...\n")
    
    # Get reports from last 30 days
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    
    response = supabase.table("medical_reports")\
        .select("id, user_id, report_type, created_at, executive_summary")\
        .gte("created_at", cutoff_date)\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute()
    
    reports = response.data or []
    print(f"Found {len(reports)} recent reports\n")
    
    for i, report in enumerate(reports, 1):
        print(f"Report {i}:")
        print(f"  ID: {report['id']}")
        print(f"  Type: {report['report_type']}")
        print(f"  Created: {report['created_at']}")
        print(f"  Has Summary: {'Yes' if report.get('executive_summary') else 'No'}")
        
        # Get full report data
        full_report = supabase.table("medical_reports")\
            .select("report_data")\
            .eq("id", report['id'])\
            .execute()
        
        if full_report.data:
            report_data = full_report.data[0].get('report_data')
            if report_data:
                print(f"  Report Data Type: {type(report_data)}")
                print(f"  Report Data Keys: {list(report_data.keys()) if isinstance(report_data, dict) else 'Not a dict'}")
                
                # Check specific sections
                if isinstance(report_data, dict):
                    has_exec_summary = 'executive_summary' in report_data
                    has_patient_story = 'patient_story' in report_data
                    has_medical_analysis = 'medical_analysis' in report_data
                    has_action_plan = 'action_plan' in report_data
                    
                    print(f"  Sections Present:")
                    print(f"    - Executive Summary: {has_exec_summary}")
                    print(f"    - Patient Story: {has_patient_story}")
                    print(f"    - Medical Analysis: {has_medical_analysis}")
                    print(f"    - Action Plan: {has_action_plan}")
                    
                    # Show sample of executive summary if present
                    if has_exec_summary and isinstance(report_data['executive_summary'], dict):
                        summary = report_data['executive_summary'].get('one_page_summary', '')
                        print(f"    - Summary Preview: {summary[:100]}..." if len(summary) > 100 else f"    - Summary: {summary}")
            else:
                print(f"  Report Data: NULL or empty")
        
        print()

def check_specific_report(report_id: str):
    """Check a specific report by ID"""
    print(f"\nChecking specific report: {report_id}\n")
    
    response = supabase.table("medical_reports")\
        .select("*")\
        .eq("id", report_id)\
        .execute()
    
    if response.data:
        report = response.data[0]
        print("Report found!")
        print(f"Type: {report['report_type']}")
        print(f"Created: {report['created_at']}")
        print(f"Executive Summary: {report.get('executive_summary', 'None')[:200]}...")
        
        report_data = report.get('report_data')
        if report_data:
            print(f"\nReport Data Structure:")
            print(json.dumps(report_data, indent=2)[:1000] + "...")
        else:
            print("\nReport Data is NULL or empty!")
    else:
        print("Report not found!")

if __name__ == "__main__":
    check_reports()
    
    # Uncomment and add a specific report ID to debug
    # check_specific_report("your-report-id-here")