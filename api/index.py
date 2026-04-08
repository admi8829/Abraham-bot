import os
import asyncio
import random  # ይህ ለሎተሪ ቁጥር ማመንጫ እንዲረዳህ ተጨምሯል
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
ADMIN_ID = os.getenv("ADMIN_ID") # የአንተን ID ከVercel Dashboard ላይ መጨመርህን አትርሳ

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

# ... ከዚህ በፊት የነበሩት handlers እንዳሉ ይቆያሉ

# --- የፎቶ መቀበያ Handler ---
@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    # ADMIN_ID መኖሩን ማረጋገጥ
    if not ADMIN_ID:
        await message.answer("Admin is not configured. Please contact support.")
        return

    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    username = message.from_user.username or "N/A"

    try:
        # 1. መረጃውን በዳታቤዝ መመዝገብ
        supabase.table("payments").insert({
            "user_id": user_id,
            "file_id": photo_id
        }).execute()

        # 2. ለአስተዳዳሪው (Admin) መላክ
        admin_kb = InlineKeyboardBuilder()
        admin_kb.button(text="✅ አጽድቅ (Approve)", callback_data=f"approve_{user_id}")
        admin_kb.button(text="❌ ሰርዝ (Reject)", callback_data=f"reject_{user_id}")
        
        # ማሳሰቢያ፡ ADMIN_ID በ Vercel ላይ በቁጥር መቀመጥ አለበት
        await bot.send_photo(
            chat_id=int(ADMIN_ID), 
            photo=photo_id,
            caption=f"አዲስ የክፍያ ጥያቄ ከ፦ @{username}\nUser ID: {user_id}",
            reply_markup=admin_kb.as_markup()
        )
        
        await message.answer("ደረሰኙ ተልኳል። አስተዳዳሪው ሲያረጋግጥ የሎተሪ ቁጥር ይላክለታል።")
        
    except Exception as e:
        print(f"Error handling photo: {e}")
        await message.answer("ስህተት ተከስቷል፣ እባክዎ ድጋሚ ይሞክሩ።")

# ... ከዚህ በታች ቀጣዩ የ approve_payment handler ይገባል
# ... (የቋንቋ መቀየሪያ ኮድ)

# 1. መጀመሪያ የፎቶ መቀበያው ይግባ
@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    # ... (ቅድም የጻፍነው የፎቶ መቀበያ ኮድ)

# 2. ከእሱ በታች ይህ የማጽደቂያ ኮድ ይግባ
@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    
    # የሎተሪ ቁጥር መፍጠር
    lottery_number = f"LOT-{random.randint(10000, 99999)}"
    
    try:
        # በዳታቤዝ ውስጥ መመዝገብ
        supabase.table("tickets").insert({
            "user_id": target_user_id,
            "ticket_number": lottery_number,
            "status": "approved"
        }).execute()

        # ለተጠቃሚው የምስራች መላክ
        await bot.send_message(
            target_user_id,
            f"🎉 እንኳን ደስ አለዎት! ክፍያዎ ተረጋግጧል።\nየእርስዎ የሎተሪ ቁጥር፦ **{lottery_number}**"
        )
        
        await callback.answer("ትኬቱ ተልኳል!")
        # የአድሚኑ ጋር ያለውን መልእክት ምልክት ማድረግ (ለማስታወስ እንዲረዳ)
        await callback.message.edit_caption(caption=f"✅ ተረጋግጧል!\nቁጥር፦ {lottery_number}\nለተጠቃሚው ተልኳል።")
        
    except Exception as e:
        print(f"Error in approval: {e}")
        await callback.answer("ስህተት ተከስቷል! ደጋግመው ይሞክሩ።", show_alert=True)

# 3. (አማራጭ) የውድቅ ማድረጊያ (Reject) ኮድ እዚህ መጨመር ትችላለህ
@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: types.CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    await bot.send_message(target_user_id, "❌ ይቅርታ፣ የላኩት የክፍያ ማረጋገጫ ተቀባይነት አላገኘም። እባክዎ በትክክል መላክዎን ያረጋግጡ።")
    await callback.message.edit_caption(caption="❌ ክፍያው ውድቅ ተደርጓል።")
    await callback.answer("ውድቅ ተደርጓል")

# ... ከዚህ በኋላ Webhook endpoint ይከተላል

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
    # ... ከላይ የነበረው handle_language_choice ኮድ እዚህ ያበቃል

# --- እዚህ ጋር አዲሶቹን መቁረጫዎች ጀምር ---

@dp.message(F.text.in_({"➕ አዲስ ትኬት ቁረጥ", "➕ Buy New Ticket"}))
async def buy_ticket_info(message: types.Message):
    # (የሰጠሁህ ኮድ እዚህ ይገባል...)

@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    # (የፎቶ መቀበያው ኮድ እዚህ ይገባል...)

@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    # (የማጽደቂያው ኮድ እዚህ ይገባል...)  
    
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
    
