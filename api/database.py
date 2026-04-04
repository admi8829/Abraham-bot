import os
from supabase import create_client, Client

# --- 1. የ Supabase ግንኙነት ማረጋገጫ ---
# በ Vercel Environment Variables ላይ SUPABASE_URL እና SUPABASE_ANON_KEY መኖራቸውን አረጋግጥ
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

# --- 2. የተጠቃሚዎች አስተዳደር (User Management) ---

def get_user_lang(user_id):
    """የተጠቃሚውን ቋንቋ ከዳታቤዝ ያመጣል፣ ከሌለ 'en' ይመልሳል"""
    try:
        res = supabase.table("users").select("language").eq("user_id", user_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]['language']
    except Exception as e:
        print(f"Error getting language: {e}")
    return "en"

def register_user(user_id, name, lang):
    """አዲስ ተጠቃሚ መመዝገብ ወይም መረጃውን ማዘመን (ቋንቋውን ሳይቀይር)"""
    data = {
        "user_id": user_id,
        "full_name": name,
        "language": lang
    }
    # upsert: ካለ ያድሳል፣ ከሌለ አዲስ ይፈጥራል
    return supabase.table("users").upsert(data).execute()

def update_user_lang(user_id, lang):
    """ተጠቃሚው ቋንቋ ሲቀይር ዳታቤዝ ላይ ያዘምናል"""
    return supabase.table("users").update({"language": lang}).eq("user_id", user_id).execute()

def get_user_data(user_id):
    """ሁሉንም የተጠቃሚውን መረጃ (Balance, Name, etc.) ለማምጣት"""
    res = supabase.table("users").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None

# --- 3. የዕጣ እና ትኬት አስተዳደር (Lottery & Tickets) ---

def get_active_lotteries():
    """አሁን ላይ ክፍት የሆኑ የዕጣ አይነቶችን ዝርዝር ያመጣል"""
    return supabase.table("lotteries").select("*").eq("is_active", True).execute()

def save_new_ticket(user_id, lottery_id, ticket_num):
    """አዲስ የተቆረጠ ትኬት መረጃ በዳታቤዝ ያስቀምጣል"""
    data = {
        "user_id": user_id,
        "lottery_id": lottery_id,
        "ticket_number": ticket_num,
        "is_winner": False
    }
    return supabase.table("tickets").insert(data).execute()

def check_ticket_exists(ticket_num):
    """ትኬት ቁጥሩ በዳታቤዝ ውስጥ መኖሩን ይፈትሻል (ለ Unique ቁጥር አሰጣጥ)"""
    res = supabase.table("tickets").select("ticket_number").eq("ticket_number", ticket_num).execute()
    return len(res.data) > 0

# --- 4. የአሸናፊዎች አስተዳደር (Winners) ---

def record_winner(user_id, ticket_num, lottery_name, prize):
    """አሸናፊ ሲገኝ በ winners ሰንጠረዥ ላይ ይመዘግባል"""
    data = {
        "user_id": user_id,
        "ticket_number": ticket_num,
        "lottery_name": lottery_name,
        "prize_amount": prize
    }
    return supabase.table("winners").insert(data).execute()

def get_all_winners(limit=10):
    """የመጨረሻዎቹን አሸናፊዎች ከነ ስማቸው ያመጣል (ከ Users Table ጋር በማገናኘት)"""
    # ማሳሰቢያ፡ በ Supabase ላይ በ Winners እና በ Users መሃል Foreign Key መኖር አለበት
    try:
        return supabase.table("winners").select("*, users(full_name)").order("won_at", desc=True).limit(limit).execute()
    except Exception as e:
        print(f"Error fetching winners: {e}")
        # Foreign Key ካልሰራ ስሙን ሳይጨምር ዝርዝሩን ብቻ ያመጣል
        return supabase.table("winners").select("*").order("won_at", desc=True).limit(limit).execute()

# --- 5. የሪፈራል ሲስተም (Referral - ለወደፊት ካስፈለገ) ---

def add_referral_point(referrer_id, amount=1):
    """ሪፈራል ለሚያደርግ ሰው ነጥብ ወይም ብር ይጨምራል"""
    user = get_user_data(referrer_id)
    if user:
        new_balance = float(user.get('balance', 0)) + amount
        return supabase.table("users").update({"balance": new_balance}).eq("user_id", referrer_id).execute()
    
