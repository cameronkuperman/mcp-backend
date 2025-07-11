import requests
import json

# Test health endpoint
print("Testing health endpoint...")
health = requests.get("http://localhost:8000/health")
print(f"Health check: {health.json()}\n")

# Test chat endpoint
print("Testing chat endpoint...")
chat_data = {
    "query": "I have been feeling tired lately and having headaches",
    "user_id": "test-user-123",
    "conversation_id": "test-conversation-456",
    "category": "health-scan"
}

try:
    response = requests.post(
        "http://localhost:8000/chat",
        json=chat_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print("Chat Response:")
        print(f"- Message: {result['response'][:200]}...")
        print(f"- Model: {result['model']}")
        print(f"- Tokens used: {result['usage']}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"Error: {e}")