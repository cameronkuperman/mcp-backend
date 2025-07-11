from supabase import create_client, Client

# Replace with your actual URL and key
url: str = "https://your-project.supabase.co"
key: str = "your-supabase-api-key"

supabase: Client = create_client(url, key)
