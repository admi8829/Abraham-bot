import os
import asyncio
import random
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
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
except (ValueError, TypeError):
    ADMIN_ID = 0
    
# 2. Initialization
bot = Bot(token=TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

WEBHOOK_PATH = f"/bot/{TOKEN}"
FINAL_WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

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
    builder.row(types.InlineKeyboardButton(text="📞 Contact Us", url="https://t.me/your_admin_username"))
    return builder.as_markup()
    
# --- Handlers ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    first_name = message.from_user.first_name or "User"

    # Referral Check
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    if referrer_id == user_id: referrer_id = None

    # Register User
    res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
    if not res.data:
        supabase.table("users").insert({
            "user_id": user_id, "username": username, "first_name": first_name,
            "lang": 'am', "referred_by": referrer_id
        }).execute()
        if referrer_id:
            try: await bot.send_message(referrer_id, "🎉 አዲስ ሰው በእርስዎ ሊንክ ቦቱን ተቀላቅሏል!")
            except: pass
            
    lang = res.data[0].get('lang', 'am') if res.data else 'am'
    welcome_text = "👋 ሰላም! ወደ ትኬት መቁረጫ ቦት በደህና መጡ።" if lang == "am" else "👋 Welcome to our Lottery Bot."
    await message.answer(welcome_text, reply_markup=get_start_inline())
    await message.answer("🎛 ከታች ካሉት አማራጮች ይምረጡ፦", reply_markup=get_main_menu(lang))

@dp.message(F.text.in_({"➕ አዲስ ትኬት ቁረጥ", "➕ Buy New Ticket"}))
async def buy_ticket_step1(message: types.Message):
    user_id = message.from_user.id
    res = supabase.table("users").select("lang", "phone").eq("user_id", user_id).execute()
    u_data = res.data[0] if res.data else {"lang": "am", "phone": None}
    
    if u_data.get('phone'):
        await show_prizes_and_pay(message, u_data.get('lang', 'am'))
        return

    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📲 ስልክ ቁጥርህን አጋራ", request_contact=True)]], resize_keyboard=True)
    await message.answer("🔐 ትኬት ለመቁረጥ ስልክ ቁጥርዎን ያጋሩ።", reply_markup=kb)

@dp.message(F.contact)
async def handle_contact(message: types.Message):
    supabase.table("users").update({"phone": message.contact.phone_number}).eq("user_id", message.from_user.id).execute()
    await show_prizes_and_pay(message, 'am')

async def show_prizes_and_pay(message: types.Message, lang: str):
    inline_kb = InlineKeyboardBuilder()
    inline_kb.button(text="💳 ክፍያ ፈጽም", callback_data="show_payment")
    await message.answer("✨ የሽልማት ዝርዝር... (ዋጋ: 50 ብር)", reply_markup=inline_kb.as_markup())

@dp.callback_query(F.data == "show_payment")
async def process_payment_info(callback: types.CallbackQuery):
    await callback.message.answer("💳 በ Telebirr (09XXXXXXXX) 50 ብር ይላኩና ደረሰኙን (Screenshot) እዚህ ይላኩ።")
    await callback.answer()

@dp.message(F.photo)
async def handle_photos(message: types.Message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    
    # Receipt to Admin
    admin_text = f"📥 [ አዲስ የክፍያ ደረሰኝ ]\n🆔 User ID: `{user_id}`"
    admin_kb = InlineKeyboardBuilder()
    admin_kb.add(types.InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{user_id}"))
    admin_kb.add(types.InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}"))
    
    await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_text, reply_markup=admin_kb.as_markup(), parse_mode="Markdown")
    await message.answer("✅ ደረሰኙ ለአስተዳዳሪው ደርሷል።")

@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    ticket_num = f"LOT-{random.randint(10000, 99999)}"
    supabase.table("tickets").insert({"user_id": user_id, "ticket_number": ticket_num, "status": "approved"}).execute()
    await bot.send_message(user_id, f"🎊 እንኳን ደስ አለዎት! የዕጣ ቁጥርዎ፦ `{ticket_num}`", parse_mode="Markdown")
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ ጸድቋል: `{ticket_num}`", reply_markup=None)

@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await bot.send_message(user_id, "❌ ደረሰኝዎ ውድቅ ተደርጓል።")
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ ውድቅ ተደርጓል", reply_markup=None)

@dp.message(Command("broadcast"))
async def broadcast_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    users = supabase.table("users").select("user_id").execute().data
    msg = message.text.replace("/broadcast", "").strip()
    for u in users:
        try: await bot.send_message(u['user_id'], msg)
        except: continue
    await message.answer("✅ ተልኳል።")

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(url=FINAL_WEBHOOK_URL)

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update_data = await request.json()
    await dp.feed_update(bot, types.Update.model_validate(update_data, context={"bot": bot}))
    return {"status": "ok"}
