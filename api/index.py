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

# --- Handlers (ትዕዛዞች) ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "ተጠቃሚ"

    # 1. ተጠቃሚው ቀድሞ ካለ ቋንቋውን ከዳታቤዝ ማምጣት
    try:
        res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        
        if res.data:
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
            "Click 'Add New Ticket' to start."
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
    gif_to_send = "BAACAgQAAxkBAAIDWWnUdyBug7o6VuYE0-LSiQE4_7ybAALfGwACtVqYUuzQrkNdaNKBOwQ"
    
    try:
        await message.answer_animation(
            animation=gif_to_send,
            caption=caption_text,
            reply_markup=get_start_inline()
        )
    except Exception as e:
        # GIF መላክ ካልተቻለ በጽሁፍ ብቻ
        await message.answer(caption_text, reply_markup=get_start_inline())
    
    # 4. ዋናውን ሜኑ መላክ
    await message.answer(menu_text, reply_markup=get_main_menu())
    



# ለቋንቋ መቀየሪያ
@dp.message(F.text == "🌐 ቋንቋ" or F.text == "🌐 Language")
async def show_language_options(message: types.Message):
    builder = InlineKeyboardBuilder()
    # callback_data ላይ set_am እና set_en ብቻ አድርገው
    builder.add(types.InlineKeyboardButton(text="አማርኛ 🇪🇹", callback_data="set_am"))
    builder.add(types.InlineKeyboardButton(text="English 🇺🇸", callback_data="set_en"))
    
    await message.answer(
        "እባክዎ ቋንቋ ይምረጡ / Please choose a language:", 
        reply_markup=builder.as_markup()
)


@dp.callback_query(F.data.startswith("set_"))
async def handle_language_choice(callback: types.CallbackQuery):
    # 1. ቋንቋውን መለየት
    selected_lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    try:
        # 2. በ Supabase ውስጥ ቋንቋውን ማዘመን
        supabase.table("users").update({"lang": selected_lang}).eq("user_id", user_id).execute()
        
        # 3. ለተጠቃሚው ማረጋገጫ ማዘጋጀት
        if selected_lang == "am":
            confirm_msg = "✅ ቋንቋ ወደ አማርኛ ተቀይሯል!"
            menu_msg = "ከታች ያሉትን አማራጮች ይጠቀሙ፡"
        else:
            confirm_msg = "✅ Language set to English!"
            menu_msg = "Use the options below:"

        # 4. የነበረውን የቋንቋ መምረጫ Inline Button በጽሁፍ መተካት
        await callback.message.edit_text(confirm_msg)
        
        # 5. ቲክ ምልክት (Notification Alert) ማሳየት
        await callback.answer(confirm_msg)

        # 6. ዋናውን ሜኑ በአዲሱ ቋንቋ መላክ (ይህ መስመር መግባት ያለበት እዚህ try ውስጥ ነው)
        await callback.message.answer(
            menu_msg, 
            reply_markup=get_main_menu(selected_lang) 
        )

    except Exception as e:
        print(f"Error updating language: {e}")
        await callback.answer("ስህተት አጋጥሟል / Error occurred", show_alert=True)
    

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
    
