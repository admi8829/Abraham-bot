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


def get_phone_keyboard(lang="am"):
    kb = ReplyKeyboardBuilder()
    # እንደ ቋንቋው ምርጫ የጽሁፍ መልዕክቱን ይቀይራል
    text = "📱 ስልክ ቁጥርህን ላክ" if lang == "am" else "📱 Send Phone Number"
    kb.row(types.KeyboardButton(text=text, request_contact=True)) # ስልክ ለመጠየቅ ወሳኙ መስመር
    return kb.as_markup(resize_keyboard=True)
    

# --- Handlers (ትዕዛዞች) ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "ተጠቃሚ"

    # 1. ተጠቃሚው ቀድሞ ካለ ቋንቋውን ከዳታቤዝ ማምጣት
    try:
        res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        
        if res.data and len(res.data) > 0:
            # ተጠቃሚው ቀድሞ ካለ ያለውን ቋንቋ ተጠቀም
            user_lang = res.data[0].get('lang', 'am')
        else:
            # አዲስ ተጠቃሚ ከሆነ መዝግብና በ 'am' ጀምር
            user_lang = 'am'
            supabase.table("users").insert({
                "user_id": user_id, 
                "username": username,
                "lang": user_lang
            }).execute()
            
    except Exception as e:
        print(f"Database Error: {e}")
        user_lang = 'am' # ስህተት ካለ በ default አማርኛ ይሁን

    # 2. በቋንቋው መሰረት ጽሁፎችን መምረጥ
    if user_lang == "en":
        caption_text = (
            f"Welcome {username} 👋\n\n"
            "With this bot, you can get lottery tickets and win prizes.\n\n"
            "Click 'Buy New Ticket' to start."
        )
        menu_text = "Use the options below:"
    else:
        caption_text = (
            f"እንኳን ደህና መጡ {username} 👋\n\n"
            "በዚህ ቦት አማካኝነት የእጣ ቁጥር በመቁረጥ የሽልማት ባለቤት መሆን ይችላሉ።\n\n"
            "ለመጀመር 'አዲስ ትኬት ቁረጥ' የሚለውን ይጫኑ።"
        )
        menu_text = "ከታች ያሉትን አማራጮች ይጠቀሙ፡"

    # 3. GIF መላክ (በሰጠኸው File ID መሰረት)
    gif_to_send = "CgACAgQAAxkBAAIBmWnVKif0xiwbmWxyUfBzGneJthwZAAKxGQACnsipUjQrEigho6qBOwQ"
    
    try:
        await message.answer_animation(
            animation=gif_to_send,
            caption=caption_text,
            reply_markup=get_start_inline()
        )
    except Exception as e:
        # GIF መላክ ካልተቻለ በጽሁፍ ብቻ እንዲልክ
        await message.answer(caption_text, reply_markup=get_start_inline())
    
    # 4. ዋናውን ሜኑ መላክ (የተመረጠውን ቋንቋ ለ get_main_menu እናስተላልፋለን)
    await message.answer(menu_text, reply_markup=get_main_menu(lang=user_lang))
            
# ለቋንቋ መቀየሪያ

# ለቋንቋ መቀየሪያ (በሁለቱም ቋንቋ እንዲሰራ)
@dp.message(F.text.in_({"🌐 ቋንቋ", "🌐 Language"}))
async def show_language_options(message: types.Message):
    builder = InlineKeyboardBuilder()
    # callback_data በትክክል መዘጋጀቱን አረጋግጥ
    builder.add(types.InlineKeyboardButton(text="አማርኛ 🇪🇹", callback_data="set_am"))
    builder.add(types.InlineKeyboardButton(text="English 🇺🇸", callback_data="set_en"))
    
    await message.answer(
        "እባክዎ ቋንቋ ይምረጡ / Please choose a language:", 
        reply_markup=builder.as_markup()
    )
    
 @dp.message(F.text.in_({"➕ አዲስ ትኬት ቁረጥ", "➕ Buy New Ticket"}))
async def handle_buy_ticket(message: types.Message):
    user_id = message.from_user.id
    
    # 1. መጀመሪያ ተጠቃሚው ስልክ ቁጥር እንዳለው ከዳታቤዝ ማረጋገጥ
    res = supabase.table("users").select("phone", "lang").eq("user_id", user_id).execute()
    user_data = res.data[0] if res.data else {"lang": "am", "phone": None}
    lang = user_data.get("lang", "am")
    
    # 2. ስልክ ቁጥር ከሌለው እንዲልክ መጠየቅ
    if not user_data.get("phone"):
        msg = "ትኬት ለመግዛት መጀመሪያ ስልክ ቁጥርዎን ማጋራት አለብዎት።" if lang == "am" else "You must share your phone number first to buy a ticket."
        await message.answer(msg, reply_markup=get_phone_keyboard(lang))
        return

    # 3. ስልክ ቁጥር ካለው የሽልማት ዝርዝር እና የክፍያ በተን ማሳየት
    if lang == "am":
        prize_msg = (
            "🏆 የሽልማት ዝርዝር፦\n"
            "1ኛ እጣ: 100,000 ብር\n"
            "2ኛ እጣ: 50,000 ብር\n\n"
            "💵 የትኬት ዋጋ: 50 ብር\n"
            "ለመቀጠል 'ክፈል' የሚለውን ይጫኑ።"
        )
        pay_btn = "💳 ክፈል"
    else:
        prize_msg = (
            "🏆 Prize List:\n"
            "1st Prize: 100,000 ETB\n"
            "2nd Prize: 50,000 ETB\n\n"
            "💵 Ticket Price: 50 ETB\n"
            "Click 'Pay' to continue."
        )
        pay_btn = "💳 Pay"

    # የክፍያ Inline Button
    pay_builder = InlineKeyboardBuilder()
    pay_builder.add(types.InlineKeyboardButton(text=pay_btn, callback_data="start_payment"))
    
    await message.answer(prize_msg, reply_markup=pay_builder.as_markup())



@dp.callback_query(F.data.startswith("set_"))
async def handle_language_choice(callback: types.CallbackQuery):
    # 'set_am' ከሆነ am ን ይወስዳል፣ 'set_en' ከሆነ en ን ይወስዳል
    selected_lang = callback.data.split("_")[1] 
    user_id = callback.from_user.id
    
    try:
        # በ Supabase ውስጥ ማዘመን
        supabase.table("users").update({"lang": selected_lang}).eq("user_id", user_id).execute()
        
        if selected_lang == "am":
            confirm_msg = "✅ ቋንቋ ወደ አማርኛ ተቀይሯል!"
            menu_msg = "ከታች ያሉትን አማራጮች ይጠቀሙ፡"
        else:
            confirm_msg = "✅ Language set to English!"
            menu_msg = "Use the options below:"

        await callback.message.edit_text(confirm_msg)
        await callback.answer(confirm_msg)

        # አዲሱን በተን (Reply Keyboard) መላክ
        await callback.message.answer(
            menu_msg, 
            reply_markup=get_main_menu(selected_lang) 
        )

    except Exception as e:
        print(f"Error: {e}")
        await callback.answer("Error occurred", show_alert=True)

@dp.message(F.contact)
async def handle_contact(message: types.Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number # የተላከው ስልክ ቁጥር
    
    try:
        # 1. ስልኩን ዳታቤዝ ላይ ማዘመን
        supabase.table("users").update({"phone": phone}).eq("user_id", user_id).execute()
        
        # 2. ቋንቋውን ማግኘት
        res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        lang = res.data[0].get("lang", "am") if res.data else "am"
        
        # 3. ስልኩ መመዝገቡን አረጋግጦ ወደ ዋናው ሜኑ መመለስ
        success_msg = "✅ ስልክዎ ተመዝግቧል! አሁን 'አዲስ ትኬት ቁረጥ' የሚለውን በመጫን መቀጠል ይችላሉ።" if lang == "am" else "✅ Phone registered! Now click 'Buy New Ticket' to continue."
        
        await message.answer(success_msg, reply_markup=get_main_menu(lang))
        
    except Exception as e:
        print(f"Error saving phone: {e}")
        await message.answer("ስህተት አጋጥሟል፣ እባክዎ ደግመው ይሞክሩ።")
        
        
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
    
