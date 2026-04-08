import os
import asyncio
import random
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
ADMIN_ID = os.getenv("ADMIN_ID") 

# 2. Initialization
bot = Bot(token=TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

# Webhook paths
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
    builder.row(types.InlineKeyboardButton(text="📺 YouTube", url="https://youtube.com/@yourchannel"))
    builder.row(types.InlineKeyboardButton(text="📞 Contact Us", url="https://t.me/your_admin_username"))
    return builder.as_markup()

# --- Handlers ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    try:
        res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        user_lang = res.data[0].get('lang', 'am') if res.data else 'am'
        if not res.data:
            supabase.table("users").insert({"user_id": user_id, "username": username, "lang": 'am'}).execute()
    except Exception: user_lang = 'am'

    caption = "እንኳን ደህና መጡ! ለመጀመር 'አዲስ ትኬት ቁረጥ' የሚለውን ይጫኑ።" if user_lang == "am" else "Welcome! Click 'Buy New Ticket' to start."
    gif_id = "CgACAgQAAxkBAAIBmWnVKif0xiwbmWxyUfBzGneJthwZAAKxGQACnsipUjQrEigho6qBOwQ"
    
    try: await message.answer_animation(animation=gif_id, caption=caption, reply_markup=get_start_inline())
    except: await message.answer(caption, reply_markup=get_start_inline())
    
    await message.answer("ምርጫዎን ይምረጡ / Choose option:", reply_markup=get_main_menu(user_lang))

# 1. የቲኬት መግዣ መረጃ
@dp.message(F.text.in_({"➕ አዲስ ትኬት ቁረጥ", "➕ Buy New Ticket"}))
async def buy_ticket_info(message: types.Message):
    res = supabase.table("users").select("lang").eq("user_id", message.from_user.id).execute()
    lang = res.data[0].get('lang', 'am') if res.data else 'am'
    
    if lang == "am":
        text = "🏆 **የዕጣ ዝርዝር**\n1ኛ: 10,000 ETB | 2ኛ: 5,000 ETB\n\n🎫 **ዋጋ: 50 ብር**\n\nበ Telebirr (09XXXXXXXX) ከፈሉ በኋላ ደረሰኙን (Screenshot) እዚህ ይላኩ።"
    else:
        text = "🏆 **Prize List**\n1st: 10,000 ETB | 2nd: 5,000 ETB\n\n🎫 **Price: 50 ETB**\n\nPay via Telebirr (09XXXXXXXX) and send the Screenshot here."
    await message.answer(text)

# 2. ስክሪንሻት መቀበያ (ለአድሚን መላኪያ)
@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    if not ADMIN_ID: return await message.answer("Admin ID not set.")
    
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    
    supabase.table("payments").insert({"user_id": user_id, "file_id": photo_id}).execute()
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Approve", callback_data=f"approve_{user_id}")
    kb.button(text="❌ Reject", callback_data=f"reject_{user_id}")
    
    await bot.send_photo(chat_id=int(ADMIN_ID), photo=photo_id, caption=f"ክፍያ ከ: {user_id}", reply_markup=kb.as_markup())
    await message.answer("ደረሰኙ ተልኳል። አስተዳዳሪው ሲያረጋግጥ ቁጥር ይላክለታል።")

# 3. አድሚኑ ሲያጸድቅ
@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    ticket_no = f"LOT-{random.randint(10000, 99999)}"
    
    supabase.table("tickets").insert({"user_id": target_id, "ticket_number": ticket_no, "status": "approved"}).execute()
    
    await bot.send_message(target_id, f"🎉 ክፍያዎ ጸድቋል! የሎተሪ ቁጥርዎ: {ticket_no}")
    await callback.message.edit_caption(caption=f"✅ ጸድቋል! ቁጥር: {ticket_no}")
    await callback.answer("Approved!")

# 4. አድሚኑ ውድቅ ሲያደርግ
@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: types.CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    await bot.send_message(target_id, "❌ ይቅርታ፣ የላኩት ደረሰኝ ተቀባይነት አላገኘም።")
    await callback.message.edit_caption(caption="❌ ውድቅ ተደርጓል።")
    await callback.answer("Rejected")

# 5. ቋንቋ መቀየሪያ
@dp.message(F.text.in_({"🌐 ቋንቋ", "🌐 Language"}))
async def show_language_options(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="አማርኛ 🇪🇹", callback_data="set_am"))
    builder.add(types.InlineKeyboardButton(text="English 🇺🇸", callback_data="set_en"))
    await message.answer("ቋንቋ ይምረጡ / Choose language:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("set_"))
async def handle_language_choice(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    supabase.table("users").update({"lang": lang}).eq("user_id", callback.from_user.id).execute()
    msg = "✅ ቋንቋ ተቀይሯል!" if lang == "am" else "✅ Language Updated!"
    await callback.message.edit_text(msg)
    await callback.message.answer(msg, reply_markup=get_main_menu(lang))

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
                  
