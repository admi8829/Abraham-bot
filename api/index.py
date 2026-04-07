import os
import asyncio
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from supabase import create_client, Client

# 1. Environment Variables መጫን
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL") # ለምሳሌ https://your-app.vercel.app/

# 2. Initialization
bot = Bot(token=TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

# --- ቦት Logic ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    # ተጠቃሚውን በ Supabase ውስጥ መመዝገብ (ካለ አይደግመውም)
    try:
        data = supabase.table("users").upsert({
            "user_id": user_id, 
            "username": username
        }).execute()
        
        await message.answer(
            f"እንኳን ደህና መጣህ {username}! \nበእጣው ለመሳተፍ ተመዝግበሃል።"
        )
    except Exception as e:
        await message.answer("ይቅርታ፣ ምዝገባው ላይ ችግር አጋጥሟል።")

@dp.message(F.text == "የእኔ ቁጥር")
async def get_ticket(message: types.Message):
    # ከ Supabase ዳታ ለማንበብ ምሳሌ
    await message.answer("የእጣ ቁጥርህ በቅርቡ ይላክልሃል።")

# --- Webhook ኮንፊገሬሽን ---

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(url=WEBHOOK_URL)

@app.post("/")
async def webhook(request: Request):
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"status": "ok"}
