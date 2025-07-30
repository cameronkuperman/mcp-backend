#!/usr/bin/env python3
"""Test all new AI prediction endpoints"""
import asyncio
import httpx
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import print as rprint

# Configuration
BASE_URL = "http://localhost:8000"
USER_ID = "45b61b67-175d-48a0-aca6-d0be57609383"

console = Console()

async def test_endpoint(client: httpx.AsyncClient, name: str, endpoint: str, expected_fields: list = None):
    """Test a single endpoint and display results"""
    console.print(f"\n[bold cyan]Testing {name}...[/bold cyan]")
    console.print(f"Endpoint: {endpoint}")
    
    try:
        start_time = datetime.now()
        response = await client.get(endpoint)
        duration = (datetime.now() - start_time).total_seconds()
        
        console.print(f"Status: [green]{response.status_code}[/green]")
        console.print(f"Response time: {duration:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            
            # Pretty print the response structure
            console.print("\n[bold]Response Structure:[/bold]")
            print_json_structure(data, indent=2)
            
            # Validate expected fields if provided
            if expected_fields:
                console.print("\n[bold]Field Validation:[/bold]")
                for field in expected_fields:
                    if field in data:
                        console.print(f"✅ {field}: [green]Present[/green]")
                    else:
                        console.print(f"❌ {field}: [red]Missing[/red]")
            
            return True, data
        else:
            console.print(f"[red]Error: {response.text}[/red]")
            return False, None
            
    except Exception as e:
        console.print(f"[red]Exception: {str(e)}[/red]")
        return False, None


def print_json_structure(obj, indent=0):
    """Pretty print JSON structure with indentation"""
    prefix = " " * indent
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                if isinstance(value, dict):
                    console.print(f"{prefix}{key}: {'{}'}")
                    print_json_structure(value, indent + 2)
                elif isinstance(value, list):
                    console.print(f"{prefix}{key}: [{len(value)} items]")
                    if value and len(value) > 0:
                        console.print(f"{prefix}  Sample item:")
                        print_json_structure(value[0], indent + 4)
            else:
                # Truncate long strings
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                console.print(f"{prefix}{key}: {value}")
    elif isinstance(obj, list):
        if obj:
            console.print(f"{prefix}[{len(obj)} items]")
    else:
        console.print(f"{prefix}{obj}")


async def test_all_endpoints():
    """Test all AI prediction endpoints"""
    console.print(f"\n[bold yellow]🧪 Testing AI Predictions API[/bold yellow]")
    console.print(f"Base URL: {BASE_URL}")
    console.print(f"User ID: {USER_ID}")
    console.print(f"Timestamp: {datetime.now().isoformat()}")
    console.print("=" * 80)
    
    # Create results table
    results_table = Table(title="Test Results Summary")
    results_table.add_column("Endpoint", style="cyan", no_wrap=True)
    results_table.add_column("Status", style="green")
    results_table.add_column("Key Data", style="yellow")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Test each endpoint
        endpoints = [
            {
                "name": "Dashboard Alert",
                "endpoint": f"{BASE_URL}/api/ai/dashboard-alert/{USER_ID}",
                "expected_fields": ["alert"]
            },
            {
                "name": "Immediate Predictions",
                "endpoint": f"{BASE_URL}/api/ai/predictions/immediate/{USER_ID}",
                "expected_fields": ["predictions", "data_quality_score", "generated_at"]
            },
            {
                "name": "Seasonal Predictions",
                "endpoint": f"{BASE_URL}/api/ai/predictions/seasonal/{USER_ID}",
                "expected_fields": ["predictions", "current_season"]
            },
            {
                "name": "Long-term Trajectory",
                "endpoint": f"{BASE_URL}/api/ai/predictions/longterm/{USER_ID}",
                "expected_fields": ["assessments", "overall_health_trajectory"]
            },
            {
                "name": "Body Patterns",
                "endpoint": f"{BASE_URL}/api/ai/patterns/{USER_ID}",
                "expected_fields": ["tendencies", "positive_responses", "pattern_metadata"]
            },
            {
                "name": "Pattern Questions",
                "endpoint": f"{BASE_URL}/api/ai/questions/{USER_ID}",
                "expected_fields": ["questions", "total_questions", "categories_covered"]
            },
            {
                "name": "Weekly Predictions",
                "endpoint": f"{BASE_URL}/api/ai/weekly/{USER_ID}",
                "expected_fields": ["status", "predictions"]
            }
        ]
        
        for ep in endpoints:
            success, data = await test_endpoint(
                client, 
                ep["name"], 
                ep["endpoint"], 
                ep.get("expected_fields")
            )
            
            # Add to results table
            if success:
                key_info = extract_key_info(ep["name"], data)
                results_table.add_row(
                    ep["name"],
                    "[green]✅ Success[/green]",
                    key_info
                )
            else:
                results_table.add_row(
                    ep["name"],
                    "[red]❌ Failed[/red]",
                    "No data"
                )
        
        # Test weekly generation endpoint
        console.print(f"\n[bold cyan]Testing Weekly Generation Trigger...[/bold cyan]")
        try:
            gen_response = await client.post(f"{BASE_URL}/api/ai/generate-weekly/{USER_ID}")
            if gen_response.status_code == 200:
                gen_data = gen_response.json()
                console.print(f"[green]Generation started![/green]")
                console.print(f"Prediction ID: {gen_data.get('prediction_id')}")
                results_table.add_row(
                    "Weekly Generation",
                    "[green]✅ Success[/green]",
                    f"ID: {gen_data.get('prediction_id', 'N/A')[:8]}..."
                )
                
                # Wait a bit and check status
                console.print("\nWaiting 5 seconds for generation to complete...")
                await asyncio.sleep(5)
                
                # Check if predictions were generated
                check_response = await client.get(f"{BASE_URL}/api/ai/weekly/{USER_ID}")
                if check_response.status_code == 200:
                    check_data = check_response.json()
                    if check_data.get("status") == "success":
                        console.print("[green]Predictions generated successfully![/green]")
                    else:
                        console.print("[yellow]Predictions still generating or not found[/yellow]")
            else:
                results_table.add_row(
                    "Weekly Generation",
                    "[red]❌ Failed[/red]",
                    gen_response.text[:50]
                )
        except Exception as e:
            console.print(f"[red]Generation test failed: {str(e)}[/red]")
    
    # Display results summary
    console.print("\n")
    console.print(results_table)


def extract_key_info(endpoint_name: str, data: dict) -> str:
    """Extract key information from response data"""
    if not data:
        return "No data"
    
    if endpoint_name == "Dashboard Alert":
        alert = data.get("alert")
        if alert:
            return f"{alert.get('severity', 'N/A')} - {alert.get('title', 'N/A')[:30]}..."
        return "No alert"
    
    elif endpoint_name == "Immediate Predictions":
        predictions = data.get("predictions", [])
        quality = data.get("data_quality_score", 0)
        return f"{len(predictions)} predictions, Quality: {quality}%"
    
    elif endpoint_name == "Seasonal Predictions":
        predictions = data.get("predictions", [])
        season = data.get("current_season", "unknown")
        return f"{len(predictions)} predictions, Season: {season}"
    
    elif endpoint_name == "Long-term Trajectory":
        assessments = data.get("assessments", [])
        trajectory = data.get("overall_health_trajectory", "unknown")
        return f"{len(assessments)} assessments, Trajectory: {trajectory}"
    
    elif endpoint_name == "Body Patterns":
        tendencies = data.get("tendencies", [])
        positive = data.get("positive_responses", [])
        return f"{len(tendencies)} tendencies, {len(positive)} positive"
    
    elif endpoint_name == "Pattern Questions":
        questions = data.get("questions", [])
        total = data.get("total_questions", 0)
        return f"{len(questions)} questions generated"
    
    elif endpoint_name == "Weekly Predictions":
        status = data.get("status", "unknown")
        if status == "success" and data.get("predictions"):
            pred = data["predictions"]
            return f"Generated: {pred.get('generated_at', 'N/A')[:10]}"
        return status
    
    return "Data received"


async def detailed_prediction_test(user_id: str):
    """Test a specific prediction in detail"""
    console.print(f"\n[bold yellow]📊 Detailed Prediction Test[/bold yellow]")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Get immediate predictions
        response = await client.get(f"{BASE_URL}/api/ai/predictions/immediate/{user_id}")
        
        if response.status_code == 200:
            data = response.json()
            predictions = data.get("predictions", [])
            
            if predictions:
                console.print(f"\n[bold]First Prediction Details:[/bold]")
                pred = predictions[0]
                
                # Display prediction details
                table = Table(show_header=False)
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="white")
                
                for key, value in pred.items():
                    if isinstance(value, list):
                        value = "\n".join(f"• {item}" for item in value)
                    elif isinstance(value, dict):
                        value = json.dumps(value, indent=2)
                    table.add_row(key, str(value))
                
                console.print(table)
            else:
                console.print("[yellow]No predictions generated[/yellow]")
        else:
            console.print(f"[red]Failed to get predictions: {response.status_code}[/red]")


if __name__ == "__main__":
    console.print("[bold magenta]AI Predictions API Test Suite[/bold magenta]")
    
    # Run all tests
    asyncio.run(test_all_endpoints())
    
    # Run detailed test
    asyncio.run(detailed_prediction_test(USER_ID))
    
    console.print("\n[bold green]✨ All tests completed![/bold green]")