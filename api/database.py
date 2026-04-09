import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user_lang(user_id):
    res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
    return res.data[0].get('lang', 'am') if res.data else 'am'

def register_user(user_id, username, referrer_id):
    res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
    if not res.data:
        supabase.table("users").insert({
            "user_id": user_id, 
            "username": username, 
            "lang": 'am',
            "referred_by": referrer_id
        }).execute()
        return True
    return False

