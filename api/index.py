import os
import asyncio
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from supabase import create_client, Client

# 1. Environment Variables (ከVercel የሚነበቡ)
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BASE_URL = os.getenv("WEBHOOK_URL") 

# 2. Initialization
bot = Bot(token=TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

# Webhook paths
WEBHOOK_PATH = f"/bot/{TOKEN}"
FINAL_WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

# --- Keyboards (አዝራሮች) ---

def get_main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ አዲስ ትኬት ቁረጥ")
    kb.button(text="👤 የእኔ መረጃ")
    kb.button(text="🎁 አሸናፊዎች")
    kb.button(text="👥 ጓደኛ ጋብዝ")
    kb.button(text="💡 እገዛ")
    kb.button(text="🌐 ቋንቋ")
    kb.adjust(1, 2, 2, 1) # ምስሉ ላይ ባለው አቀማመጥ መሰረት
    return kb.as_markup(resize_keyboard=True)

def get_start_inline():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🌐 Website", url="https://yourwebsite.com"))
    builder.row(types.InlineKeyboardButton(text="📺 YouTube", url="https://youtube.com/@yourchannel"))
    builder.row(types.InlineKeyboardButton(text="📞 Contact Us", url="https://t.me/your_admin_username"))
    return builder.as_markup()

# --- Handlers (ትዕዛዞች) ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "ተጠቃሚ"

    # ተጠቃሚውን ዳታቤዝ ላይ መመዝገብ
    try:
        supabase.table("users").upsert({
            "user_id": user_id, 
            "username": username,
            "lang": "am"
        }).execute()
    except Exception as e:
        print(f"Database Error: {e}")

    # GIF ID (እዚህ ጋር ያገኘኸውን ID ተካው)
    # ማሳሰቢያ፡ ገና ID ካላገኘህ ለጊዜው ሊንኩን ተጠቀም
    gif_to_send = "BAACAgQAAxkBAAIDWWnUdyBug7o6VuYE0-LSiQE4_7ybAALfGwACtVqYUuzQrkNdaNKBOwQ"
    
    caption_text = (
        f"እንኳን ደህና መጡ {username} 👋\n\n"
        "በዚህ ቦት አማካኝነት የእጣ ቁጥር በመቁረጥ የሽልማት ባለቤት መሆን ይችላሉ።\n\n"
        "ለመጀመር 'አዲስ ትኬት ቁረጥ' የሚለውን ይጫኑ።"
    )

    try:
        await message.answer_animation(
            animation=gif_to_send,
            caption=caption_text,
            reply_markup=get_start_inline()
        )
    except:
        # GIF ካልሰራ በጽሁፍ ብቻ እንዲልክ
        await message.answer(caption_text, reply_markup=get_start_inline())
    
    await message.answer("ከታች ያሉትን አማራጮች ይጠቀሙ፡", reply_markup=get_main_menu())

# GIF ID ለማግኘት የሚረዳ Handler (ለአንተ ብቻ)
@dp.message(F.animation)
async def get_gif_id_handler(message: types.Message):
    await message.answer(f"የዚህ GIF File ID:\n`{message.animation.file_id}`", parse_mode="Markdown")

# ለቋንቋ መቀየሪያ
@dp.message(F.text == "🌐 ቋንቋ")
async def show_language_options(message: types.Message):
    builder = InlineKeyboardBuilder()
    # callback_data ተጠቃሚው ሲጫነው ወደ ቦቱ የሚላክ ድብቅ መረጃ ነው
    builder.add(types.InlineKeyboardButton(text="አማርኛ 🇪🇹", callback_data="set_lang_am"))
    builder.add(types.InlineKeyboardButton(text="English 🇺🇸", callback_data="set_lang_en"))
    
    await message.answer(
        "እባክዎ ቋንቋ ይምረጡ / Please choose a language:", 
        reply_markup=builder.as_markup()
    )
    


@dp.callback_query(F.data.startswith("set_"))
async def set_lang_callback(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    supabase.table("users").update({"lang": lang}).eq("user_id", callback.from_user.id).execute()
    
    text = "ቋንቋ ተቀይሯል!" if lang == "am" else "Language Updated!"
    await callback.message.edit_text(text)
    await callback.answer()

# --- Webhook Endpoint ---

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(url=FINAL_WEBHOOK_URL)

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update_data = await request.json()
    update = types.Update.model_validate(update_data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"status": "ok"}
    
