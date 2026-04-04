import os
from supabase import create_client, Client

# Vercel Settings ላይ SUPABASE_URL እና SUPABASE_ANON_KEY መኖራቸውን አረጋግጥ
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

# --- 1. ተጠቃሚ መመዝገብ (User Management) ---
def register_user(user_id, name, lang='en'):
    """አዲስ ተጠቃሚ መመዝገብ ወይም መረጃውን ማዘመን"""
    data = {
        "user_id": user_id,
        "full_name": name,
        "language": lang
    }
    # upsert ካለ ያድሳል ከሌለ አዲስ ይፈጥራል
    return supabase.table("users").upsert(data).execute()

def get_user_data(user_id):
    """የአንድን ተጠቃሚ ሙሉ መረጃ ለማግኘት"""
    res = supabase.table("users").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None

# --- 2. የቋንቋ ምርጫ (Language Management) ---
def update_user_lang(user_id, lang):
    """ተጠቃሚው የመረጠውን ቋንቋ ዳታቤዝ ላይ መቀየር"""
    return supabase.table("users").update({"language": lang}).eq("user_id", user_id).execute()

def get_user_lang(user_id):
    """የተጠቃሚውን ቋንቋ ለይቶ ማምጣት"""
    res = supabase.table("users").select("language").eq("user_id", user_id).execute()
    return res.data[0]['language'] if res.data else "en"

# --- 3. የዕጣ አይነቶች (Lottery Management) ---
def get_active_lotteries():
    """አሁን ላይ የሚሰሩ የዕጣ አይነቶችን ዝርዝር ያመጣል"""
    return supabase.table("lotteries").select("*").eq("is_active", True).execute()

# --- 4. የትኬት ሽያጭ (Ticket System) ---
def check_if_bought(user_id, lottery_id):
    """አንድ ሰው ቀድሞ ትኬት መቁረጡን ያረጋግጣል (ለአንድ ሰው አንድ እጣ ብቻ ከሆነ)"""
    res = supabase.table("tickets").select("*").eq("user_id", user_id).eq("lottery_id", lottery_id).execute()
    return len(res.data) > 0

def save_new_ticket(user_id, lottery_id, ticket_num):
    """አዲስ የተቆረጠ ትኬት መመዝገብ"""
    data = {
        "user_id": user_id,
        "lottery_id": lottery_id,
        "ticket_number": ticket_num,
        "is_winner": False
    }
    return supabase.table("tickets").insert(data).execute()

# --- 5. የአሸናፊዎች ታሪክ (Winners Gallery) ---
def record_winner(user_id, ticket_num, lottery_name, prize):
    """አዲስ አሸናፊ ሲኖር በ winners table ላይ መመዝገብ"""
    data = {
        "user_id": user_id,
        "ticket_number": ticket_num,
        "lottery_name": lottery_name,
        "prize_amount": prize
    }
    return supabase.table("winners").insert(data).execute()

def get_all_winners(limit=10):
    """የመጨረሻዎቹን አሸናፊዎች ከነ ስማቸው ያመጣል"""
    # ሪሌሽንሺፑ እንዲሰራ በ users table ላይ 'user_id' Foreign Key መሆን አለበት
    return supabase.table("winners").select("*, users(full_name)").order("won_at", desc=True).limit(limit).execute()
    
