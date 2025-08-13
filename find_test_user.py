import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

# Find users with symptom tracking data
result = supabase.table('symptom_tracking').select('user_id').limit(10).execute()
if result.data:
    print('Users with symptom data:')
    users_seen = set()
    for r in result.data:
        if r['user_id'] and r['user_id'] not in users_seen:
            print(f'  {r["user_id"]}')
            users_seen.add(r['user_id'])
else:
    print('No users with symptom data')

# Find users with quick scans
result = supabase.table('quick_scans').select('user_id').limit(10).execute()
if result.data:
    print('\nUsers with quick scans:')
    users_seen = set()
    for r in result.data:
        if r['user_id'] and r['user_id'] not in users_seen:
            print(f'  {r["user_id"]}')
            users_seen.add(r['user_id'])
            if len(users_seen) >= 3:
                break