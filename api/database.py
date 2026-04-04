import os
from supabase import create_client, Client

# Vercel Settings ላይ እነዚህን መሙላት እንዳትረሳ
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(URL, KEY)

# ተማሪው መመዝገቡን ቼክ ለማድረግ
def check_user(user_id):
    res = supabase.table("users").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None

# አዲስ ተማሪ ለመመዝገብ
def add_user(user_id, name, phone, grade):
    data = {
        "user_id": user_id, 
        "full_name": name, 
        "phone": phone, 
        "grade": grade
    }
    return supabase.table("users").insert(data).execute()

# አዲስ ትኬት ለመመዝገብ
def add_ticket(user_id, ticket_no, tx_ref):
    data = {
        "user_id": user_id,
        "ticket_number": ticket_no,
        "tx_ref": tx_ref,
        "status": "pending"
    }
    return supabase.table("tickets").insert(data).execute()

