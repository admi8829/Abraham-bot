import os
import asyncio
import random
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from supabase import create_client, Client

# 1. Environment Variables & Setup
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BASE_URL = os.getenv("WEBHOOK_URL")

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
except:
    ADMIN_ID = 0
    CHANNEL_ID = 0

bot = Bot(token=TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

# --- Keyboards ---
def get_main_menu(lang):
    builder = ReplyKeyboardBuilder()
    if lang == "am":
        builder.row(KeyboardButton(text="➕ አዲስ ትኬት ቁረጥ"), KeyboardButton(text="🎁 አሸናፊዎች"))
        builder.row(KeyboardButton(text="👤 የእኔ መረጃ"), KeyboardButton(text="👥 ጓደኛ ጋብዝ"))
        builder.row(KeyboardButton(text="💡 እገዛ"), KeyboardButton(text="🌐 ቋንቋ / Language"))
    else:
        builder.row(KeyboardButton(text="➕ Buy Ticket"), KeyboardButton(text="🎁 Winners"))
        builder.row(KeyboardButton(text="👤 My Profile"), KeyboardButton(text="👥 Invite Friends"))
        builder.row(KeyboardButton(text="💡 Help"), KeyboardButton(text="🌐 ቋንቋ / Language"))
    return builder.as_markup(resize_keyboard=True)

def get_start_inline():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📢 Channel", url="https://t.me/ethiouh"))
    return builder.as_markup()

# --- Helper Functions ---
async def notify_ticket_purchase(first_name, ticket_number):
    """አዲስ ትኬት ሲቆረጥ ለቻናል የሚያሳውቅ"""
    text = (
        "🎫 **አዲስ ትኬት በይፋ ተቆርጧል!**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **እድለኛ:** `{first_name}`\n"
        f"🔢 **የእጣ ቁጥር:** `{ticket_number}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✨ ቀጣዩ እድለኛ እርስዎ ይሁኑ! አሁኑኑ ትኬት ይቁረጡ።"
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

    # 1. የቻናል ግዴታ ቼክ
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["left", "kicked", "null"]:
            kb = InlineKeyboardBuilder()
            kb.row(types.InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/ethiouh"))
            kb.row(types.InlineKeyboardButton(text="🔄 I Joined", callback_data="check_join"))
            await message.answer("⚠️ ቦቱን ለመጠቀም መጀመሪያ ቻናላችንን ይቀላቀሉ!", reply_markup=kb.as_markup())
            return
    except: pass

    # 2. ሪፈራል እና ምዝገባ
    args = message.text.split()
    ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    
    try:
        res = supabase.table("users").select("*").eq("user_id", user_id).execute()
        if not res.data:
            supabase.table("users").insert({
                "user_id": user_id, "username": username, "first_name": first_name,
                "referred_by": ref_id, "lang": "am"
            }).execute()
            if ref_id:
                try: await bot.send_message(ref_id, f"🎉 {first_name} በእርስዎ ሊንክ ገብቷል!")
                except: pass
        user_lang = res.data[0].get('lang', 'am') if res.data else "am"
    except: user_lang = "am"

    welcome = "👋 እንኳን ደህና መጡ!" if user_lang == "am" else "👋 Welcome!"
    await message.answer(welcome, reply_markup=get_main_menu(user_lang))

@dp.callback_query(F.data == "check_join")
async def check_join(callback: types.CallbackQuery):
    await callback.message.delete()
    await start_handler(callback.message)

@dp.message(F.photo)
async def handle_photos(message: types.Message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id

    # Admin Broadcast
    if user_id == ADMIN_ID and message.caption and message.caption.startswith("/broadcast"):
        msg_text = message.caption.replace("/broadcast", "").strip()
        users = supabase.table("users").select("user_id").execute().data
        for u in users:
            try: await bot.send_photo(u['user_id'], photo_id, caption=msg_text)
            except: continue
        await message.answer("✅ ተልኳል።")
        return

    # User Receipt
    try:
        user_data = supabase.table("users").select("lang", "phone").eq("user_id", user_id).execute().data[0]
        supabase.table("payments").insert({"user_id": user_id, "file_id": photo_id, "status": "pending"}).execute()
        
        admin_kb = InlineKeyboardBuilder()
        admin_kb.add(types.InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{user_id}"))
        admin_kb.add(types.InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}"))
        
        await bot.send_photo(ADMIN_ID, photo_id, caption=f"📥 ደረሰኝ ከ: {user_id}", reply_markup=admin_kb.as_markup())
        await message.answer("✅ ደረሰኝዎ ደርሶናል፤ እየታየ ነው...")
    except Exception as e:
        await message.answer(f"❌ ስህተት: {e}")

@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    ticket_number = f"LOT-{random.randint(10000, 99999)}"
    
    try:
        # 1. ትኬት መመዝገብ
        supabase.table("tickets").insert({"user_id": user_id, "ticket_number": ticket_number, "status": "approved"}).execute()
        # 2. የተጠቃሚ ስም ማግኘት
        u = supabase.table("users").select("first_name").eq("user_id", user_id).execute().data[0]
        
        await bot.send_message(user_id, f"🎉 ክፍያዎ ጸድቋል! ቁጥርዎ: `{ticket_number}`", parse_mode="Markdown")
        await notify_ticket_purchase(u['first_name'], ticket_number)
        
        await callback.message.edit_caption(caption=f"✅ ጸድቋል! ቁጥር: {ticket_number}", reply_markup=None)
    except Exception as e:
        await callback.answer(f"❌ DB Error: {e}", show_alert=True)

@dp.message(Command("draw"))
async def draw_winners(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    try:
        tickets = supabase.table("tickets").select("*").eq("status", "approved").execute().data
        if len(tickets) < 3:
            await message.answer("❌ በቂ ትኬት የለም (ቢያንስ 3 ያስፈልጋል)።")
            return

        winners = random.sample(tickets, 3)
        res_text = "🎊 **የዛሬው እድለኞች!** 🎊\n\n"
        ranks = ["1ኛ", "2ኛ", "3ኛ"]

        for i, w in enumerate(winners):
            u_id, t_num = w['user_id'], w['ticket_number']
            supabase.table("tickets").update({"status": "winner"}).eq("ticket_number", t_num).execute()
            res_text += f"⭐ {ranks[i]}: User ID {u_id} (ቁጥር: {t_num})\n"
            try: await bot.send_message(u_id, f"🎊 እንኳን ደስ አለዎት! የ{ranks[i]} አሸናፊ ሆነዋል።")
            except: pass

        await bot.send_message(CHANNEL_ID, res_text, parse_mode="Markdown")
        await message.answer("✅ እጣ ወጥቷል!")
    except Exception as e:
        await message.answer(f"Error: {e}")

# --- Webhook ---
@app.post(f"/bot/{TOKEN}")
async def bot_webhook(request: Request):
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(f"{BASE_URL}/bot/{TOKEN}")
