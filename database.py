import os
from supabase import create_client, Client

# 1. Configuration (Environment Variables)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Supabase Client መፍጠር
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. የተጠቃሚ ቋንቋን ለማወቅ
def get_user_lang(user_id):
    try:
        res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        if res.data:
            return res.data[0].get('lang', 'am')
        return 'am'
    except Exception as e:
        print(f"Error fetching lang: {e}")
        return 'am'

# 3. አዲስ ተጠቃሚ ለመመዝገብ
def register_user(user_id, username, referrer_id):
    try:
        # ተጠቃሚው ቀድሞ መኖሩን ማረጋገጥ
        res = supabase.table("users").select("user_id").eq("user_id", user_id).execute()
        
        if not res.data:
            supabase.table("users").insert({
                "user_id": user_id, 
                "username": username, 
                "lang": 'am',
                "referred_by": referrer_id
            }).execute()
            return True
        return False
    except Exception as e:
        print(f"Error registering user: {e}")
        return False

# 4. የስልክ ቁጥር ለማደስ
def update_user_phone(user_id, phone):
    try:
        supabase.table("users").update({"phone": phone}).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"Error updating phone: {e}")
        return False

# 5. የተሟላ የተጠቃሚ መረጃ ለማግኘት (phone እና lang ጨምሮ)
def get_user_data(user_id):
    try:
        res = supabase.table("users").select("lang", "phone").eq("user_id", user_id).execute()
        return res.data[0] if res.data else {"lang": "am", "phone": None}
    except Exception as e:
        print(f"Error fetching user data: {e}")
        return {"lang": "am", "phone": None}

# 6. የክፍያ ደረሰኝ ለመመዝገብ
def register_payment(user_id, file_id):
    try:
        supabase.table("payments").insert({"user_id": user_id, "file_id": file_id}).execute()
        return True
    except Exception as e:
        print(f"Error registering payment: {e}")
        return False

# 7. አሸናፊዎችን ለማምጣት
def get_recent_winners():
    try:
        res = supabase.table("winners").select("ticket_number, draw_date, users(username)").order("draw_date", desc=True).limit(5).execute()
        if not res.data:
            return "እስካሁን ምንም አሸናፊ የለም።"
        
        winners_text = ""
        for w in res.data:
            name = w['users']['username'] if w['users']['username'] else "ተጠቃሚ"
            winners_text += f"⭐ @{name} — ቲኬት፦ {w['ticket_number']}\n"
        return winners_text
    except Exception as e:
        print(f"Error fetching winners: {e}")
        return "መረጃ ማግኘት አልተቻለም።"
                
