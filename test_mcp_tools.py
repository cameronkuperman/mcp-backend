import requests
import json

# Base URL for MCP HTTP server
BASE_URL = "http://localhost:8000"

print("Testing MCP Tools via HTTP...\n")

# Test oracle_query tool
print("1. Testing oracle_query tool:")
oracle_request = {
    "method": "tools/call",
    "params": {
        "name": "oracle_query",
        "arguments": {
            "query": "I have been having headaches and feeling dizzy",
            "user_id": "test-user-123",
            "conversation_id": "test-conv-789"
        }
    }
}

response = requests.post(f"{BASE_URL}/message", json=oracle_request)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Response: {result.get('content', result)[:200]}...")
else:
    print(f"Error: {response.text}")

print("\n2. Testing API endpoints:")
# Test health endpoint
health = requests.get(f"{BASE_URL}/api/health")
print(f"Health check: {health.json()}")

print("\n3. Testing chat endpoint:")
# Test chat endpoint
chat_data = {
    "query": "What should I do about my headaches?",
    "user_id": "test-user-123",
    "conversation_id": "test-conv-789",
    "category": "health-scan"
}

chat_response = requests.post(f"{BASE_URL}/api/chat", json=chat_data)
if chat_response.status_code == 200:
    result = chat_response.json()
    print(f"Chat response: {result['response'][:200]}...")
else:
    print(f"Error: {chat_response.text}")