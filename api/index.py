import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from supabase import create_client, Client

# Configurations (ከ Vercel Environment Variables የሚነበቡ)
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

# --- Keyboards (አዝራሮች) ---

def get_main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ አዲስ ትኬት ቁረጥ")
    kb.button(text="👤 የእኔ መረጃ")
    kb.button(text="🎁 አሸናፊዎች")
    kb.button(text="👥 ጓደኛ ጋብዝ")
    kb.button(text="💡 እገዛ")
    kb.button(text="🌐 ቋንቋ")
    kb.adjust(1, 2, 2, 1) # አቀማመጡን በምስሉ መሰረት ያደርገዋል
    return kb.as_markup(resize_keyboard=True)

def get_start_inline():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🌐 Website", url="https://yourwebsite.com"))
    builder.row(types.InlineKeyboardButton(text="📺 YouTube", url="https://youtube.com/@yourchannel"))
    builder.row(types.InlineKeyboardButton(text="📞 Contact Us", url="https://t.me/your_admin_username"))
    return builder.as_markup()

# --- Handlers (ትዕዛዞች) ---

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"

    # 1. ተጠቃሚውን ዳታቤዝ ላይ መመዝገብ
    try:
        supabase.table("users").upsert({
            "user_id": user_id, 
            "username": username,
            "lang": "am" # Default ቋንቋ አማርኛ
        }).execute()
    except Exception as e:
        print(f"Database Error: {e}")

    # 2. GIF መላክ (እዚህ ጋር ያገኘኸውን File ID ተካው)
    # ማሳሰቢያ፡ IDው ከሌለህ ለጊዜው በሊንኩ መጠቀም ትችላለህ
    gif_to_send = "YOUR_GIF_FILE_ID_HERE" 
    if gif_to_send == "YOUR_GIF_FILE_ID_HERE":
        gif_to_send = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNHJueXN4bmZ3bmZ3bmZ3bmZ3bmZ3bmZ3bmZ3JmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/3o7TKMGpxxZES858DS/giphy.gif"
    
    caption = f"እንኳን ደህና መጡ {username} 👋\n\nበዚህ ቦት አማካኝነት የእጣ ቁጥር በመቁረጥ የሽልማት ባለቤት መሆን ይችላሉ።"
    
    await message.answer_animation(
        animation=gif_to_send,
        caption=caption,
        reply_markup=get_start_inline()
    )
    
    # 3. ዋናውን Reply Menu መላክ
    await message.answer("ከታች ያሉትን አማራጮች ይጠቀሙ፡", reply_markup=get_main_menu())

# --- የ GIF ID ማግኛ Handler (ለአንተ ብቻ እንዲጠቅም) ---
@dp.message(F.animation)
async def handle_gif(message: types.Message):
    gif_id = message.animation.file_id
    await message.answer(f"የዚህ GIF File ID: \n`{gif_id}`", parse_mode="Markdown")

# --- Webhook Endpoint ---

@app.post("/")
async def webhook(request: Request):
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(url=WEBHOOK_URL)
    
