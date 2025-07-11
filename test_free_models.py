#!/usr/bin/env python3
"""Test OpenRouter with various free models"""
import requests
import os
from dotenv import load_dotenv
import dns.resolver

load_dotenv()

# List of free models from OpenRouter
FREE_MODELS = [
    "meta-llama/llama-3.2-1b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "cognitivecomputations/dolphin-3.0-mistral-24b:free",
    "cognitivecomputations/dolphin-3.0-r1-mistral-24b:free",
    "arliai/qwq-32b-arliai-rpr-v1:free",
    "gryphe/mythomax-l2-13b:free",
    "google/gemini-2.0-flash-thinking-exp-1219:free",
    "liquid/lfm-40b:free",
    "microsoft/phi-3.5-mini-128k-instruct:free"
]

def test_dns():
    """Test if we can resolve OpenRouter API"""
    print("Testing DNS resolution...")
    try:
        # Try to resolve using Google's DNS
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['8.8.8.8', '8.8.4.4']
        
        answers = resolver.resolve('api.openrouter.ai', 'A')
        for rdata in answers:
            print(f"✅ DNS resolved to: {rdata}")
        return True
    except Exception as e:
        print(f"❌ DNS resolution failed: {e}")
        try:
            # Try with requests to see the actual error
            import socket
            ip = socket.gethostbyname('api.openrouter.ai')
            print(f"✅ Socket resolved to: {ip}")
            return True
        except Exception as e2:
            print(f"❌ Socket resolution also failed: {e2}")
            return False

def test_model(model_name):
    """Test a specific model"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Medical Chat Test"
    }
    
    data = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": "Say 'Hello, Oracle is working!' in exactly 5 words."}
        ],
        "temperature": 0.1,
        "max_tokens": 50
    }
    
    try:
        print(f"\nTesting model: {model_name}")
        response = requests.post(
            "https://api.openrouter.ai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ Success! Response: {content}")
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: Cannot reach api.openrouter.ai")
        return False
    except Exception as e:
        print(f"❌ Exception: {type(e).__name__}: {e}")
        return False

def main():
    print("🔍 OpenRouter Free Models Test")
    print("=" * 50)
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ No API key found in .env!")
        return
    
    print(f"✅ API Key found: {api_key[:20]}...")
    
    # Test DNS first
    if not test_dns():
        print("\n⚠️  DNS issues detected. Trying alternative solutions...")
        
        # Try using IP directly
        print("\nAttempting direct IP connection...")
        # OpenRouter IPs from Cloudflare
        for ip in ["104.18.8.49", "104.18.9.49"]:
            try:
                print(f"Testing IP: {ip}")
                response = requests.get(f"https://{ip}/", 
                                      headers={"Host": "api.openrouter.ai"},
                                      timeout=5)
                print(f"IP {ip} reachable: {response.status_code}")
            except:
                print(f"IP {ip} not reachable")
        
        print("\n💡 To fix DNS issues:")
        print("1. Try: sudo dscacheutil -flushcache")
        print("2. Check if VPN is blocking")
        print("3. Try different network")
        print("4. Add to /etc/hosts: 104.18.8.49 api.openrouter.ai")
        return
    
    # Test each free model
    working_models = []
    for model in FREE_MODELS[:3]:  # Test first 3 to save time
        if test_model(model):
            working_models.append(model)
    
    print("\n" + "=" * 50)
    print("📊 Results:")
    print(f"Working models: {len(working_models)}/{len(FREE_MODELS[:3])}")
    if working_models:
        print("\n✅ Working free models:")
        for model in working_models:
            print(f"  - {model}")
        
        print(f"\n🎯 Recommended model: {working_models[0]}")
        print("\nUpdate your business_logic.py with:")
        print(f'return "{working_models[0]}"')
    else:
        print("\n❌ No models worked. Check your API key or network.")

if __name__ == "__main__":
    # Install dnspython if needed
    try:
        import dns.resolver
    except ImportError:
        print("Installing dnspython...")
        import subprocess
        subprocess.check_call(["pip", "install", "dnspython"])
        import dns.resolver
    
    main()