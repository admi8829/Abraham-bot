import os
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import database as db
from keyboards import get_main_menu, get_start_inline, get_language_keyboard

ADMIN_ID = os.getenv("ADMIN_ID")

async def start_handler(message: types.Message, bot):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    CHANNEL_ID = -1003866954136 
    
    # ቻናል Join ማድረጉን ቼክ ማድረግ
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["left", "kicked"]:
            kb = InlineKeyboardBuilder()
            kb.row(types.InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/ethiouh"))
            await message.answer("⚠️ ቦቱን ለመጠቀም መጀመሪያ ቻናላችንን ይቀላቀሉ።", reply_markup=kb.as_markup())
            return
    except: pass

    # መመዝገብ
    args = message.text.split()
    ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    db.register_user(user_id, username, ref_id)
    
    lang = db.get_user_lang(user_id)
    await message.answer("እንኳን መጡ!", reply_markup=get_main_menu(lang))

async def buy_ticket_step1(message: types.Message):
    user_id = message.from_user.id
    data = db.get_user_data(user_id)
    if data.get('phone'):
        await message.answer("እባክዎ የክፍያ ደረሰኝ (Screenshot) ይላኩ።")
    else:
        kb = ReplyKeyboardBuilder()
        kb.button(text="📲 ስልክ ቁጥር አጋራ", request_contact=True)
        await message.answer("ትኬት ለመቁረጥ ስልክ ቁጥርዎን ያጋሩ።", reply_markup=kb.as_markup(resize_keyboard=True))

async def handle_contact(message: types.Message):
    db.update_user_phone(message.from_user.id, message.contact.phone_number)
    await message.answer("✅ ቁጥርዎ ተመዝግቧል። አሁን ደረሰኝ መላክ ይችላሉ።")

async def handle_photos(message: types.Message, bot):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    
    if str(user_id) == str(ADMIN_ID):
        await message.answer("ይህ የአድሚን ፎቶ ነው።")
    else:
        db.register_payment(user_id, photo_id)
        # ለአድሚን ማሳወቅ
        await bot.send_photo(ADMIN_ID, photo=photo_id, caption=f"አዲስ ክፍያ ከ: {user_id}")
        await message.answer("✅ ደረሰኙ ለባለሙያ ተልኳል።")

async def my_info_handler(message: types.Message):
    data = db.get_user_data(message.from_user.id)
    await message.answer(f"👤 የእርስዎ መረጃ:\nስልክ: {data.get('phone')}\nቋንቋ: {data.get('lang')}")

async def show_winners(message: types.Message):
    winners = db.get_recent_winners()
    await message.answer(winners)

async def invite_friends_handler(message: types.Message, bot):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    await message.answer(f"ይህ የእርስዎ መጋበዣ ሊንክ ነው:\n{link}")

async def show_language_options(message: types.Message):
    await message.answer("ቋንቋ ይምረጡ:", reply_markup=get_language_keyboard())
    
