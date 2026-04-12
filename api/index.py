import os
import asyncio
import random
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F # 'F' እዚህ ጋር ተጨምሯል
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from supabase import create_client, Client

# 1. Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BASE_URL = os.getenv("WEBHOOK_URL")

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    raw_channel_id = os.getenv("CHANNEL_ID", "0")
    CHANNEL_ID = int(raw_channel_id)
except (ValueError, TypeError):
    ADMIN_ID = 0
    CHANNEL_ID = 0
    
# 2. Initialization
bot = Bot(token=TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

WEBHOOK_PATH = f"/bot/{TOKEN}"
FINAL_WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

# --- Helpers ---
async def notify_ticket_purchase(first_name, ticket_number):
    """ትኬት ሲቆረጥ ለቻናል መረጃ መላኪያ"""
    try:
        text = f"🎫 **አዲስ ትኬት ተቆርጧል!**\n\n👤 ስም፦ {first_name}\n🔢 የትኬት ቁጥር፦ `{ticket_number}`\n\n🎯 ቀጣዩ እድለኛ እርስዎ ይሁኑ!"
        await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="Markdown")
    except Exception as e:
        print(f"Notification Error: {e}")

# --- Keyboards ---
def get_main_menu(lang="am"):
    kb = ReplyKeyboardBuilder()
    if lang == "en":
        kb.button(text="➕ Buy New Ticket")
        kb.button(text="👤 My Info")
        kb.button(text="🎁 Winners")
        kb.button(text="👥 Invite Friends")
        kb.button(text="💡 Help")
        kb.button(text="🌐 Language")
    else:
        kb.button(text="➕ አዲስ ትኬት ቁረጥ")
        kb.button(text="👤 የእኔ መረጃ")
        kb.button(text="🎁 አሸናፊዎች")
        kb.button(text="👥 ጓደኛ ጋብዝ")
        kb.button(text="💡 እገዛ")
        kb.button(text="🌐 ቋንቋ")
    kb.adjust(1, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True)

def get_start_inline():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🌐 Website", url="https://yourwebsite.com"))
    builder.row(types.InlineKeyboardButton(text="📺 YouTube", url="https://youtube.com/@yourchannel"))
    builder.row(types.InlineKeyboardButton(text="📞 Contact Us", url="https://t.me/your_admin_username"))
    return builder.as_markup()
    
# --- Handlers ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    first_name = message.from_user.first_name or "User"

    # የግብዣ (Referral) ሲስተም
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id == user_id: referrer_id = None

    # ዳታቤዝ ውስጥ መመዝገብ
    try:
        res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        
        if not res.data:
            user_lang = 'am'
            supabase.table("users").insert({
                "user_id": user_id, 
                "username": username, 
                "first_name": first_name,
                "lang": 'am',
                "referred_by": referrer_id
            }).execute()
            
            if referrer_id:
                try: await bot.send_message(referrer_id, "🎉 አዲስ ሰው በእርስዎ ሊንክ ቦቱን ተቀላቅሏል!")
                except: pass
        else:
            user_lang = res.data[0].get('lang', 'am')
    except Exception as e:
        print(f"DB Error: {e}")
        user_lang = 'am'

    if user_lang == "am":
        welcome_text = f"👋 **ሰላም {first_name}!**\nወደ ትኬት መቁረጫ ቦት በደህና መጡ።\n\n🎯 **እድለኛ ይሁኑ!**"
        menu_msg = "🎛 ከታች ካሉት አማራጮች አንዱን ይምረጡ፦"
    else:
        welcome_text = f"👋 **Hello {first_name}!**\nWelcome to our Lottery Ticket Bot."
        menu_msg = "🎛 Please choose an option:"

    await message.answer(welcome_text, reply_markup=get_start_inline(), parse_mode="Markdown")
    await message.answer(menu_msg, reply_markup=get_main_menu(user_lang))

@dp.message(F.text.in_({"➕ አዲስ ትኬት ቁረጥ", "➕ Buy New Ticket"}))
async def buy_ticket_step1(message: types.Message):
    user_id = message.from_user.id
    res = supabase.table("users").select("lang", "phone").eq("user_id", user_id).execute()
    user_data = res.data[0] if res.data else {"lang": "am", "phone": None}
    lang = user_data.get('lang', 'am')
    
    if user_data.get('phone'):
        await show_prizes_and_pay(message, lang)
        return

    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📲 ስልክ ቁጥርህን አጋራ / Share Contact", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
    text = "🔐 **የደህንነት ማረጋገጫ**\n\nትኬት ለመቁረጥ ስልክዎን ማጋራት አለብዎት።" if lang == "am" else "🔐 **Security Verification**\n\nPlease share your contact."
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.contact)
async def handle_contact(message: types.Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    supabase.table("users").update({"phone": phone}).eq("user_id", user_id).execute()
    
    res_lang = supabase.table("users").select("lang").eq("user_id", user_id).execute()
    lang = res_lang.data[0].get('lang', 'am') if res_lang.data else 'am'
    await message.answer("✅", reply_markup=get_main_menu(lang))
    await show_prizes_and_pay(message, lang)

async def show_prizes_and_pay(message: types.Message, lang: str):
    try:
        prizes_res = supabase.table("prizes").select("*").eq("lang", lang).execute()
        prizes = prizes_res.data
        prize_list = "".join([f"🏆 {p['rank']} እጣ: **{p['amount']}**\n" for p in prizes])

        inline_kb = InlineKeyboardBuilder()
        inline_kb.button(text="💳 ክፍያ ፈጽም (Pay Now)" if lang == "am" else "💳 Pay Now", callback_data="show_payment")

        text = f"✨ **የእለቱ የሽልማት ዝርዝር** ✨\n\n{prize_list}\n🎫 **የአንድ ትኬት ዋጋ: 50 ብር**" if lang == "am" else f"✨ **Today's Prizes** ✨\n\n{prize_list}\n🎫 **Ticket Price: 50 ETB**"
        await message.answer(text, reply_markup=inline_kb.as_markup(), parse_mode="Markdown")
    except:
        await message.answer("Error. Try again.")

@dp.callback_query(F.data == "show_payment")
async def process_payment_info(callback: types.CallbackQuery):
    text = "💳 **የክፍያ መመሪያ**\n\nበ Telebirr (09XXXXXXXX) 50 ብር ይላኩና ደረሰኙን (Screenshot) እዚህ ይላኩ።"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.message(F.photo)
async def handle_photos(message: types.Message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id

    # Broadcast Check
    if user_id == ADMIN_ID and message.caption and message.caption.startswith("/broadcast"):
        # (ብሮድካስት ሎጂክ እዚህ ይገባል - ከታች ካለው ኮድ ጋር ተመሳሳይ)
        return

    # Receipt Handling
    res_user = supabase.table("users").select("lang", "phone", "first_name").eq("user_id", user_id).execute()
    u_data = res_user.data[0] if res_user.data else {}
    
    admin_text = f"📥 **[ አዲስ የክፍያ ደረሰኝ ]**\n👤 ስም: `{u_data.get('first_name')}`\n📞 ስልክ: `{u_data.get('phone')}`\n🆔 ID: `{user_id}`"
    admin_kb = InlineKeyboardBuilder()
    admin_kb.add(types.InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{user_id}"))
    admin_kb.add(types.InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}"))
    
    await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_text, reply_markup=admin_kb.as_markup(), parse_mode="Markdown")
    await message.answer("✅ ደረሰኙ ደርሷል። ሲረጋገጥ ቁጥር ይላክለታል።")

@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    ticket_number = f"LOT-{random.randint(10000, 99999)}"
    
    supabase.table("tickets").insert({"user_id": user_id, "ticket_number": ticket_number, "status": "approved"}).execute()
    res = supabase.table("users").select("lang", "first_name").eq("user_id", user_id).execute()
    u_info = res.data[0] if res.data else {"lang": "am", "first_name": "User"}
    
    msg = f"🎊 እንኳን ደስ አለዎት! የዕጣ ቁጥርዎ፦ `{ticket_number}`" if u_info['lang'] == "am" else f"🎊 Congrats! Your ticket: `{ticket_number}`"
    await bot.send_message(user_id, msg, parse_mode="Markdown")
    await notify_ticket_purchase(u_info['first_name'], ticket_number)
    
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ ጸድቋል: `{ticket_number}`", reply_markup=None)

@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await bot.send_message(user_id, "❌ ደረሰኝዎ ውድቅ ተደርጓል።")
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ ውድቅ ተደርጓል", reply_markup=None)

@dp.message(F.text.in_({"👤 የእኔ መረጃ", "👤 My Info"}))
async def my_info_handler(message: types.Message):
    res = supabase.table("tickets").select("ticket_number").eq("user_id", message.from_user.id).eq("status", "approved").execute()
    tickets = [t['ticket_number'] for t in res.data]
    text = f"👤 **መረጃ**\n\nID: `{message.from_user.id}`\n🎫 ትኬቶች፦ " + (", ".join(tickets) if tickets else "የለም")
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("draw"))
async def draw_winners(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    res = supabase.table("tickets").select("*").eq("status", "approved").execute()
    all_t = res.data
    if len(all_t) < 1: return await message.answer("ትኬት የለም")
    
    winner = random.choice(all_t)
    text = f"🎊 የዛሬው አሸናፊ፦ `{winner['ticket_number']}` (ID: {winner['user_id']})"
    await bot.send_message(CHANNEL_ID, text)
    await message.answer(f"✅ ተጠናቀቀ። አሸናፊ፦ {winner['ticket_number']}")

@dp.message(Command("broadcast"))
async def broadcast_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    users = supabase.table("users").select("user_id").execute().data
    msg_text = message.text.replace("/broadcast", "").strip()
    for u in users:
        try: await bot.send_message(u['user_id'], msg_text)
        except: continue
    await message.answer("✅ ተልኳል።")

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(url=FINAL_WEBHOOK_URL)

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update_data = await request.json()
    update = types.Update.model_validate(update_data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"status": "ok"}
 
