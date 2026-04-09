import asyncio
import random
from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import database as db  # Supabase ስራዎች እዚህ ውስጥ እንዳሉ እናስባለን
from keyboards import get_main_menu, get_start_inline

# 1. Start Handler
async def start_handler(message: types.Message, bot):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    CHANNEL_ID = -1003866954136  # ያንተ የቻናል ID
    
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["left", "kicked"]:
            kb = InlineKeyboardBuilder()
            kb.row(types.InlineKeyboardButton(text="📢 ቻናሉን ተቀላቀል / Join Channel", url="https://t.me/ethiouh"))
            kb.row(types.InlineKeyboardButton(text="🔄 ተቀላቅያለሁ / I joined", callback_data="check_join"))
            await message.answer("⚠️ ቦቱን ለመጠቀም መጀመሪያ የቴሌግራም ቻናላችንን መቀላቀል አለብዎት።", reply_markup=kb.as_markup())
            return
    except Exception as e:
        print(f"Join check error: {e}")

    # Referral & DB Registration (ከ database.py ጋር መገናኘት አለበት)
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    db.register_user(user_id, username, referrer_id)
    
    lang = db.get_user_lang(user_id)
    welcome_text = "👋 ሰላም! ወደ ትኬት መቁረጫ ቦት በደህና መጡ።" if lang == "am" else "👋 Welcome to our Lottery Bot."
    await message.answer(welcome_text, reply_markup=get_start_inline())
    await message.answer("🎛 ምርጫዎን ይምረጡ፦", reply_markup=get_main_menu(lang))

# 2. Buy Ticket Step 1
async def buy_ticket_step1(message: types.Message):
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id) # phone እና lang የያዘ
    lang = user_data.get('lang', 'am')
    
    if user_data.get('phone'):
        await show_prizes_and_pay(message, lang)
        return

    kb = ReplyKeyboardBuilder()
    kb.button(text="📲 ስልክ ቁጥርህን አጋራ / Share Contact", request_contact=True)
    text = "🔐 ትኬት ለመቁረጥ መጀመሪያ ስልክ ቁጥርዎን ማጋራት አለብዎት።" if lang == "am" else "🔐 Please share your contact first."
    await message.answer(text, reply_markup=kb.as_markup(resize_keyboard=True))

# 3. Handle Contact
async def handle_contact(message: types.Message):
    user_id = message.from_user.id
    db.update_user_phone(user_id, message.contact.phone_number)
    lang = db.get_user_lang(user_id)
    await message.answer("✅", reply_markup=get_main_menu(lang))
    await show_prizes_and_pay(message, lang)

# 4. Handle Photos (ይህ ነው ስህተት የፈጠረው!)
async def handle_photos(message: types.Message, bot, admin_id):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    
    # ለሁለቱም (ለአድሚን ብሮድካስት እና ለተጠቃሚ ደረሰኝ) ስራ ይውላል
    if str(user_id) == str(admin_id):
        # የአድሚን ብሮድካስት logic እዚህ ይገባል...
        pass
    else:
        db.register_payment(user_id, photo_id)
        admin_kb = InlineKeyboardBuilder()
        admin_kb.add(types.InlineKeyboardButton(text="✅ አጽድቅ", callback_data=f"approve_{user_id}"))
        admin_kb.add(types.InlineKeyboardButton(text="❌ ሰርዝ", callback_data=f"reject_{user_id}"))
        await bot.send_photo(chat_id=admin_id, photo=photo_id, caption=f"📥 አዲስ ክፍያ ከ {user_id}", reply_markup=admin_kb.as_markup())
        await message.answer("✅ ደረሰኙ ተልኳል።")

# 5. My Info, Winners, Invite
async def my_info_handler(message: types.Message):
    user_id = message.from_user.id
    info = db.get_user_info(user_id)
    await message.answer(f"👤 የእርስዎ መረጃ፦\n{info}")

async def show_winners(message: types.Message):
    winners = db.get_recent_winners()
    await message.answer(f"🏆 የቅርብ ጊዜ አሸናፊዎች፦\n{winners}")

async def invite_friends_handler(message: types.Message, bot_username):
    invite_link = f"https://t.me/{bot_username}?start={message.from_user.id}"
    await message.answer(f"👥 ጓደኛ ይጋብዙ፦\n{invite_link}")

async def show_language_options(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="አማርኛ 🇪🇹", callback_data="set_am"))
    builder.add(types.InlineKeyboardButton(text="English 🇺🇸", callback_data="set_en"))
    await message.answer("ቋንቋ ይምረጡ / Choose language:", reply_markup=builder.as_markup())

# ረዳት Function
async def show_prizes_and_pay(message, lang):
    # የሽልማት ዝርዝር የሚያሳይ ኮድ
    pass
    
