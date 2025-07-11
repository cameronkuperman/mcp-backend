#!/usr/bin/env python3
"""
Troubleshooting script for Oracle MCP Backend
"""
import subprocess
import requests
import sys
import time

def check_port(port=8000):
    """Check if port is in use"""
    result = subprocess.run(f"lsof -i:{port}", shell=True, capture_output=True, text=True)
    if result.stdout:
        print(f"❌ Port {port} is already in use:")
        print(result.stdout)
        return False
    print(f"✅ Port {port} is available")
    return True

def kill_port(port=8000):
    """Kill process using port"""
    print(f"Killing any process on port {port}...")
    subprocess.run(f"lsof -ti:{port} | xargs kill -9 2>/dev/null || true", shell=True)
    time.sleep(1)

def check_server_health(base_url="http://localhost:8000"):
    """Check if server is running"""
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Server is healthy: {response.json()}")
            return True
    except:
        pass
    print("❌ Server is not responding")
    return False

def test_chat_endpoint(base_url="http://localhost:8000"):
    """Test the chat endpoint"""
    print("\nTesting chat endpoint...")
    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "query": "Test message",
                "user_id": "test-user",
                "conversation_id": "test-conv",
                "category": "health-scan"
            },
            timeout=10
        )
        if response.status_code == 200:
            print("✅ Chat endpoint working!")
            print(f"Response preview: {response.json()['response'][:100]}...")
            return True
        else:
            print(f"❌ Chat endpoint error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Chat endpoint failed: {e}")
    return False

def main():
    print("🔍 Oracle MCP Backend Troubleshooter\n")
    
    # Check if server is already running
    if check_server_health():
        print("\n✅ Server is already running!")
        test_chat_endpoint()
        print("\nYour Next.js app can connect to: http://localhost:8000")
        return
    
    # Check port availability
    if not check_port():
        print("\nAttempting to free port 8000...")
        kill_port()
        if check_port():
            print("✅ Port freed successfully!")
        else:
            print("❌ Failed to free port. Try manually: lsof -ti:8000 | xargs kill -9")
            sys.exit(1)
    
    print("\n📝 To start the server, run:")
    print("   uv run python run_full_server.py")
    print("\n📱 For Next.js integration:")
    print("   - Set NEXT_PUBLIC_API_URL=http://localhost:8000")
    print("   - Use the /api/chat endpoint")
    print("   - Follow the integration guide in ORACLE_INTEGRATION_COMPLETE.md")

if __name__ == "__main__":
    main()