import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from supabase import create_client, Client

# Configurations
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

# --- Keyboards ---

def get_main_menu():
    kb = ReplyKeyboardBuilder()
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
    builder.row(types.InlineKeyboardButton(text="🌐 Website", url="https://example.com"))
    builder.row(types.InlineKeyboardButton(text="📺 YouTube", url="https://youtube.com/@yourchannel"))
    builder.row(types.InlineKeyboardButton(text="📞 Contact Us", url="https://t.me/your_username"))
    return builder.as_markup()

# --- Handlers ---

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"

    # Register user in Supabase
    supabase.table("users").upsert({"user_id": user_id, "username": username}).execute()

    # GIF URL (እዚህ ጋር የራስህን የ GIF ሊንክ ተካው)
    gif_url = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNHJueXN4bmZ3bmZ3bmZ3bmZ3bmZ3bmZ3bmZ3JmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/3o7TKMGpxxZES858DS/giphy.gif"
    
    caption = f"እንኳን ደህና መጡ {username} 👋\n\nበዚህ ቦት አማካኝነት የእጣ ቁጥር በመቁረጥ የሽልማት ባለቤት መሆን ይችላሉ።"
    
    await message.answer_animation(
        animation=gif_url,
        caption=caption,
        reply_markup=get_start_inline()
    )
    # ዋናውን ሜኑ ላክ
    await message.answer("ከታች ያሉትን አማራጮች ይጠቀሙ፡", reply_markup=get_main_menu())

@dp.message(F.text == "🌐 ቋንቋ")
async def lang_setting(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="አማርኛ 🇪🇹", callback_data="set_am"))
    builder.add(types.InlineKeyboardButton(text="English 🇺🇸", callback_data="set_en"))
    await message.answer("እባክዎ ቋንቋ ይምረጡ / Please choose a language:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("set_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    supabase.table("users").update({"lang": lang}).eq("user_id", user_id).execute()
    
    msg = "ቋንቋ ወደ አማርኛ ተቀይሯል።" if lang == "am" else "Language changed to English."
    await callback.message.edit_text(msg)
    await callback.answer()

# --- Webhook ---

@app.post("/")
async def webhook(request: Request):
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"status": "ok"}
    
