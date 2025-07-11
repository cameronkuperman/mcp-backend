from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# Get from environment variables
url: str = os.getenv("SUPABASE_URL", "")
# Use service key to bypass RLS
key: str = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))

if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY/ANON_KEY must be set in .env file")

supabase: Client = create_client(url, key)
