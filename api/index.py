import os
import asyncio
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from supabase import create_client, Client

# 1. Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BASE_URL = os.getenv("WEBHOOK_URL") 

# 2. Initialization
bot = Bot(token=TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

WEBHOOK_PATH = f"/bot/{TOKEN}"
FINAL_WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

# --- Keyboards (አዝራሮች) ---

def get_main_menu(lang="am"):
    kb = ReplyKeyboardBuilder()
    if lang == "en":
        buttons = ["➕ Buy New Ticket", "👤 My Info", "🎁 Winners", "👥 Invite Friends", "💡 Help", "🌐 Language"]
    else:
        buttons = ["➕ አዲስ ትኬት ቁረጥ", "👤 የእኔ መረጃ", "🎁 አሸናፊዎች", "👥 ጓደኛ ጋብዝ", "💡 እገዛ", "🌐 ቋንቋ"]
    
    for btn in buttons:
        kb.button(text=btn)
    kb.adjust(1, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True)

def get_start_inline():
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Channel", url="https://t.me/your_channel"))
    return builder.as_markup()

def get_phone_keyboard(lang="am"):
    kb = ReplyKeyboardBuilder()
    text = "📱 ስልክ ቁጥርህን ላክ" if lang == "am" else "📱 Send Phone Number"
    kb.row(types.KeyboardButton(text=text, request_contact=True))
    return kb.as_markup(resize_keyboard=True)

# --- Handlers (ትዕዛዞች) ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    try:
        res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        if res.data and len(res.data) > 0:
            user_lang = res.data[0].get('lang', 'am')
        else:
            user_lang = 'am'
            supabase.table("users").insert({"user_id": user_id, "username": username, "lang": user_lang}).execute()
    except:
        user_lang = 'am'

    if user_lang == "en":
        caption = f"Welcome {username}! Click 'Buy New Ticket' to start."
        menu_msg = "Use the options below:"
    else:
        caption = f"እንኳን ደህና መጡ {username}! ለመጀመር 'አዲስ ትኬት ቁረጥ' የሚለውን ይጫኑ።"
        menu_msg = "ከታች ያሉትን አማራጮች ይጠቀሙ፡"

    gif_id = "CgACAgQAAxkBAAIBmWnVKif0xiwbmWxyUfBzGneJthwZAAKxGQACnsipUjQrEigho6qBOwQ"
    try:
        await message.answer_animation(animation=gif_id, caption=caption, reply_markup=get_start_inline())
    except:
        await message.answer(caption, reply_markup=get_start_inline())
    
    await message.answer(menu_msg, reply_markup=get_main_menu(lang=user_lang))

# ቋንቋ መክፈቻ (ለአማርኛም ለእንግሊዝኛም እንዲሰራ)
@dp.message(F.text.in_({"🌐 ቋንቋ", "🌐 Language"}))
async def show_language_options(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="አማርኛ 🇪🇹", callback_data="set_am"))
    builder.add(types.InlineKeyboardButton(text="English 🇺🇸", callback_data="set_en"))
    await message.answer("እባክዎ ቋንቋ ይምረጡ / Please choose a language:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("set_"))
async def handle_language_choice(callback: types.CallbackQuery):
    selected_lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    try:
        supabase.table("users").update({"lang": selected_lang}).eq("user_id", user_id).execute()
        msg = "✅ ቋንቋ ተቀይሯል!" if selected_lang == "am" else "✅ Language updated!"
        await callback.message.edit_text(msg)
        await callback.message.answer(msg, reply_markup=get_main_menu(lang=selected_lang))
    except:
        await callback.answer("Error!")

# ትኬት መቁረጥ
@dp.message(F.text.in_({"➕ አዲስ ትኬት ቁረጥ", "➕ Buy New Ticket"}))
async def handle_buy_ticket(message: types.Message):
    user_id = message.from_user.id
    res = supabase.table("users").select("phone", "lang").eq("user_id", user_id).execute()
    user_data = res.data[0] if res.data else {"lang": "am", "phone": None}
    lang = user_data.get("lang", "am")
    
    if not user_data.get("phone"):
        msg = "ትኬት ለመግዛት መጀመሪያ ስልክዎን ያጋሩ።" if lang == "am" else "Share your phone first to buy a ticket."
        await message.answer(msg, reply_markup=get_phone_keyboard(lang))
        return

    if lang == "am":
        prize_msg = "🏆 የሽልማት ዝርዝር፡\n1ኛ እጣ: 100,000 ብር\n\n💵 ዋጋ: 50 ብር"
        pay_btn = "💳 ክፈል"
    else:
        prize_msg = "🏆 Prize List:\n1st: 100,000 ETB\n\n💵 Price: 50 ETB"
        pay_btn = "💳 Pay"

    pay_builder = InlineKeyboardBuilder()
    pay_builder.add(types.InlineKeyboardButton(text=pay_btn, callback_data="start_payment"))
    await message.answer(prize_msg, reply_markup=pay_builder.as_markup())

@dp.message(F.contact)
async def handle_contact(message: types.Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    supabase.table("users").update({"phone": phone}).eq("user_id", user_id).execute()
    
    res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
    lang = res.data[0].get("lang", "am") if res.data else "am"
    await message.answer("✅ ተመዝግቧል!", reply_markup=get_main_menu(lang))

# --- Webhook Setup ---
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(url=FINAL_WEBHOOK_URL)

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update_data = await request.json()
    update = types.Update.model_validate(update_data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"status": "ok"}
    
