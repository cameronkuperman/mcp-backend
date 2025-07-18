#!/usr/bin/env python3
"""Debug script for testing photo analysis functionality"""
import asyncio
import os
import httpx
from dotenv import load_dotenv
from supabase import create_client
import base64

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
STORAGE_BUCKET = os.getenv('SUPABASE_STORAGE_BUCKET', 'medical-photos')

async def test_storage_connection():
    """Test Supabase storage connection"""
    print("=== Testing Storage Connection ===")
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ Missing Supabase credentials")
        return False
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        
        # List buckets
        buckets = supabase.storage.list_buckets()
        print(f"✅ Connected to Supabase storage")
        print(f"📦 Available buckets: {[b['name'] for b in buckets]}")
        
        # Check if medical-photos bucket exists
        bucket_exists = any(b['name'] == STORAGE_BUCKET for b in buckets)
        if bucket_exists:
            print(f"✅ Bucket '{STORAGE_BUCKET}' exists")
        else:
            print(f"❌ Bucket '{STORAGE_BUCKET}' not found")
            print(f"   Run the create_storage_bucket.sql migration in Supabase dashboard")
        
        return bucket_exists
        
    except Exception as e:
        print(f"❌ Storage connection error: {str(e)}")
        return False

async def test_photo_retrieval(photo_id: str = None):
    """Test retrieving a photo from storage"""
    print("\n=== Testing Photo Retrieval ===")
    
    if not photo_id:
        print("ℹ️  No photo_id provided, skipping retrieval test")
        return
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        
        # Get photo record
        photo_result = supabase.table('photo_uploads').select('*').eq('id', photo_id).single().execute()
        
        if not photo_result.data:
            print(f"❌ Photo {photo_id} not found in database")
            return
        
        photo = photo_result.data
        print(f"✅ Found photo record: {photo['storage_url']}")
        
        if not photo['storage_url']:
            print("❌ Photo has no storage_url")
            return
        
        # Try to download
        download_response = supabase.storage.from_(STORAGE_BUCKET).download(photo['storage_url'])
        
        # Debug response type
        print(f"📥 Download response type: {type(download_response)}")
        print(f"📥 Response attributes: {dir(download_response)}")
        
        # Try different ways to get the data
        file_data = None
        
        if hasattr(download_response, 'content'):
            file_data = download_response.content
            print("✅ Got file data from .content attribute")
        elif isinstance(download_response, bytes):
            file_data = download_response
            print("✅ Got file data as bytes")
        elif hasattr(download_response, 'read'):
            file_data = download_response.read()
            print("✅ Got file data from .read() method")
        else:
            print(f"❓ Unknown response type: {download_response}")
            # Try to print the actual response
            print(f"   Response: {download_response}")
        
        if file_data:
            print(f"✅ File size: {len(file_data)} bytes")
            
            # Try to encode as base64
            base64_data = base64.b64encode(file_data).decode('utf-8')
            print(f"✅ Base64 encoding successful, length: {len(base64_data)}")
        else:
            print("❌ Could not extract file data from response")
            
    except Exception as e:
        print(f"❌ Photo retrieval error: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_api_endpoints():
    """Test photo analysis API endpoints"""
    print("\n=== Testing API Endpoints ===")
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        try:
            response = await client.get(f"{base_url}/api/photo-analysis/health")
            print(f"✅ Health check: {response.json()}")
        except Exception as e:
            print(f"❌ Health check failed: {str(e)}")
        
        # Test debug storage endpoint
        try:
            response = await client.get(f"{base_url}/api/photo-analysis/debug/storage")
            print(f"✅ Storage debug: {response.json()}")
        except Exception as e:
            print(f"❌ Storage debug failed: {str(e)}")

async def main():
    """Run all tests"""
    print("🔍 Photo Analysis Debug Script")
    print("=" * 50)
    
    # Test storage connection
    storage_ok = await test_storage_connection()
    
    # Test photo retrieval if you have a photo ID
    # Replace with an actual photo ID from your database
    # await test_photo_retrieval("your-photo-id-here")
    
    # Test API endpoints (requires server running)
    # await test_api_endpoints()
    
    print("\n✅ Debug script completed")

if __name__ == "__main__":
    asyncio.run(main())