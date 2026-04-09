import os
import asyncio
import random
import logging
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

async def notify_ticket_purchase(first_name, ticket_number):
    text = (
        "🎫 **አዲስ ትኬት በይፋ ተቆርጧል!**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **እድለኛ:** `{first_name}`\n"
        f"🔢 **የእጣ ቁጥር:** `{ticket_number}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✨ ቀጣዩ እድለኛ እርስዎ ይሁኑ!"
    )
    try:
        if CHANNEL_ID != 0:
            await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Channel notify error: {e}")

# --- Handlers ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "User"
    
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["left", "kicked", "null"]:
            kb = InlineKeyboardBuilder()
            kb.row(types.InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/ethiouh"))
            kb.row(types.InlineKeyboardButton(text="🔄 I Joined", callback_data="check_join"))
            await message.answer("⚠️ ቦቱን ለመጠቀም መጀመሪያ ቻናላችንን ይቀላቀሉ!", reply_markup=kb.as_markup())
            return
    except: pass

    args = message.text.split()
    ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    
    try:
        res = supabase.table("users").select("*").eq("user_id", user_id).execute()
        if not res.data:
            supabase.table("users").insert({
                "user_id": user_id, "username": username, "first_name": first_name,
                "referred_by": ref_id, "lang": "am"
            }).execute()
        user_lang = res.data[0].get('lang', 'am') if res.data else "am"
    except: user_lang = "am"

    await message.answer(f"👋 እንኳን ደህና መጡ {first_name}!", reply_markup=get_main_menu(user_lang))

@dp.callback_query(F.data == "check_join")
async def check_join_callback(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except: pass
    await start_handler(callback.message)
    await callback.answer()

@dp.message(F.photo)
async def handle_photos(message: types.Message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    
    try:
        supabase.table("payments").insert({"user_id": user_id, "file_id": photo_id, "status": "pending"}).execute()
        
        admin_kb = InlineKeyboardBuilder()
        admin_kb.add(types.InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{user_id}"))
        admin_kb.add(types.InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}"))
        
        await bot.send_photo(ADMIN_ID, photo_id, caption=f"📥 አዲስ ክፍያ ከ: {user_id}", reply_markup=admin_kb.as_markup())
        await message.answer("✅ ደረሰኝዎ ደርሷል፤ አስተዳዳሪው እያረጋገጠው ነው...")
    except Exception as e:
        await message.answer(f"❌ ስህተት፦ {e}")

@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    ticket_number = f"LOT-{random.randint(10000, 99999)}"
    
    try:
        supabase.table("tickets").insert({"user_id": user_id, "ticket_number": ticket_number, "status": "approved"}).execute()
        u_info = supabase.table("users").select("first_name").eq("user_id", user_id).execute().data[0]
        
        await bot.send_message(user_id, f"🎉 ክፍያዎ ጸድቋል! የትኬት ቁጥርዎ: `{ticket_number}`", parse_mode="Markdown")
        await notify_ticket_purchase(u_info['first_name'], ticket_number)
        await callback.message.edit_caption(caption=f"✅ ጸድቋል! ቁጥር: {ticket_number}", reply_markup=None)
    except Exception as e:
        await callback.answer(f"❌ DB Error: {e}", show_alert=True)

# --- Webhook ---
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(url=FINAL_WEBHOOK_URL)

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update_data = await request.json()
    update = types.Update.model_validate(update_data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"status": "ok"}
