import os
import asyncio
import random
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from supabase import create_client, Client

# --- Configurations ---
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
except:
    ADMIN_ID = CHANNEL_ID = 0

bot = Bot(token=TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

# --- Keyboards ---
def get_main_menu(lang="am"):
    kb = ReplyKeyboardBuilder()
    buttons = [
        "➕ አዲስ ትኬት ቁረጥ", "👤 የእኔ መረጃ", "🎁 አሸናፊዎች",
        "👥 ጓደኛ ጋብዝ", "💡 እገዛ", "🌐 ቋንቋ"
    ] if lang == "am" else [
        "➕ Buy New Ticket", "👤 My Info", "🎁 Winners",
        "👥 Invite Friends", "💡 Help", "🌐 Language"
    ]
    for btn in buttons:
        kb.button(text=btn)
    kb.adjust(1, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True)

# --- Handlers ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    # ቻናል መቀላቀሉን ቼክ ማድረግ (አማራጭ)
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["left", "kicked"]:
            kb = InlineKeyboardBuilder()
            kb.button(text="📢 Join Channel", url=f"https://t.me/ethiouh")
            return await message.answer("⚠️ መጀመሪያ ቻናሉን ይቀላቀሉ!", reply_markup=kb.as_markup())
    except: pass
    
    await message.answer(f"👋 እንኳን ደህና መጡ {message.from_user.first_name}!", reply_markup=get_main_menu())

@dp.message(F.photo)
async def handle_payment(message: types.Message):
    photo_id = message.photo[-1].file_id
    admin_kb = InlineKeyboardBuilder()
    admin_kb.button(text="✅ Approve", callback_data=f"app_{message.from_user.id}")
    await bot.send_photo(ADMIN_ID, photo_id, caption=f"ክፍያ ከ: {message.from_user.id}", reply_markup=admin_kb.as_markup())
    await message.answer("✅ ደረሰኙ ለባለሙያ ተልኳል...")

@dp.callback_query(F.data.startswith("app_"))
async def approve(callback: types.CallbackQuery):
    u_id = int(callback.data.split("_")[1])
    ticket = f"LOT-{random.randint(1000, 9999)}"
    await bot.send_message(u_id, f"🎉 ጸድቋል! ትኬት: {ticket}")
    await callback.message.edit_caption(caption=f"✅ ጸድቋል: {ticket}")

# --- Vercel Webhook Endpoint ---
@app.post("/webhook")
async def webhook_handler(request: Request):
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.get("/")
async def index():
    return {"status": "Bot is running"}
