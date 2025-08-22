"""Database connection management for photo analysis"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def get_supabase():
    """Get initialized Supabase client"""
    supabase = None
    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    elif SUPABASE_URL and SUPABASE_ANON_KEY:
        # Fallback to anon key if service key not available
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print("Warning: Using ANON key for photo analysis. Some operations may be limited.")
    return supabase