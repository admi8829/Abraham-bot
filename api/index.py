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
    
@dp.message(F.text.in_({"👤 የእኔ መረጃ", "👤 My Info"}))
async def my_info_handler(message: types.Message):
    user_id = message.from_user.id
    
    try:
        # 1. የቋንቋ ምርጫውን ማወቅ
        res_lang = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        lang = res_lang.data[0].get('lang', 'am') if res_lang.data else 'am'

        # 2. የጸደቁ ቲኬቶችን ከዳታቤዝ ማምጣት
        res_tickets = supabase.table("tickets").select("ticket_number").eq("user_id", user_id).eq("status", "approved").execute()
        tickets = res_tickets.data

        if lang == "am":
            if not tickets:
                text = "🛡 **የእርስዎ መረጃ**\n\nእስካሁን ምንም የቆረጡት ትኬት የለም።"
            else:
                ticket_list = "\n• ".join([t['ticket_number'] for t in tickets])
                text = f"👤 **የእርስዎ መረጃ**\n\n🆔 ID: `{user_id}`\n🎫 **የቆረጧቸው ትኬቶች፦**\n• {ticket_list}"
        else:
            if not tickets:
                text = "🛡 **Your Info**\n\nYou haven't purchased any tickets yet."
            else:
                ticket_list = "\n• ".join([t['ticket_number'] for t in tickets])
                text = f"👤 **Your Info**\n\n🆔 ID: `{user_id}`\n🎫 **Your Tickets:**\n• {ticket_list}"

        await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        print(f"Error in My Info: {e}")
        await message.answer("ስህተት ተከስቷል፣ እባክዎ ቆይተው ይሞክሩ።")

@dp.message(F.text.in_({"🎁 አሸናፊዎች", "🎁 Winners"}))
async def show_winners(message: types.Message):
    try:
        # በቅርብ ጊዜ ያሸነፉ 5 ሰዎችን ማምጣት
        res = supabase.table("winners").select("ticket_number, draw_date, users(username)").order("draw_date", desc=True).limit(5).execute()
        winners_list = res.data

        if not winners_list:
            text = "🏆 **አሸናፊዎች**\n\nእስካሁን ምንም አሸናፊ አልተመዘገበም። ቀጣዩ አሸናፊ እርስዎ ይሁኑ!"
        else:
            text = "🏆 **የቅርብ ጊዜ አሸናፊዎች**\n\n"
            for w in winners_list:
                name = w['users']['username'] if w['users']['username'] else "ተጠቃሚ"
                # ቀኑን ለማሳመር (ከ timestamp ላይ ቀኑን ብቻ መውሰድ)
                date = w['draw_date'].split('T')[0] if 'T' in w['draw_date'] else ""
                text += f"⭐ @{name} — ቲኬት፦ `{w['ticket_number']}` ({date})\n"
        
        await message.answer(text)

    except Exception as e:
        print(f"Error fetching winners: {e}")
        await message.answer("አሸናፊዎችን ማግኘት አልተቻለም።")
        
                

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

@dp.message(Command("draw"))
async def pick_winner(message: types.Message):
    # አድሚን መሆንህን ያረጋግጣል
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    GROUP_CHAT_ID = "-1003878868241" 

    try:
        # 1. ክፍያቸው የተረጋገጠ ቲኬቶችን ማምጣት
        res = supabase.table("tickets").select("*").eq("status", "approved").execute()
        tickets = res.data

        if not tickets:
            await message.answer("ምንም የተሸጠ ቲኬት የለም።")
            return

        # 2. አሸናፊውን በዕድል መምረጥ
        winner_ticket = random.choice(tickets)
        winner_user_id = winner_ticket['user_id']
        winner_number = winner_ticket['ticket_number']

        # 3. የአሸናፊውን ስም ማግኘት
        user_res = supabase.table("users").select("username").eq("user_id", winner_user_id).execute()
        winner_name = user_res.data[0]['username'] if user_res.data else "ተጠቃሚ"

        # --- አዲሱ ክፍል፡ ወደ Winners Table መመዝገብ እና የቲኬቱን Status መቀየር ---
        try:
            # ወደ winners table መመዝገብ
            supabase.table("winners").insert({
                "user_id": winner_user_id,
                "ticket_number": winner_number
            }).execute()
            
            # በ tickets table ውስጥ የቲኬቱን ሁኔታ ወደ 'winner' መቀየር
            supabase.table("tickets").update({"status": "winner"}).eq("ticket_number", winner_number).execute()
        except Exception as db_err:
            print(f"Database recording error: {db_err}")
        # ------------------------------------------------------------

        # --- መልእክቶቹን ማዘጋጀት ---
        public_text = (
            "🎉 **እንኳን ደስ አላችሁ! የዛሬው አሸናፊ ተለይቷል!** 🎉\n\n"
            f"👤 አሸናፊ፦ @{winner_name}\n"
            f"🎫 የቲኬት ቁጥር፦ {winner_number}\n\n"
            "ቀጣዩ አሸናፊ እርስዎ ይሁኑ! አሁኑኑ ትኬት ይቁረጡ።"
        )
        
        private_text = (
            "🎊 **እንኳን ደስ አለዎት!** 🎊\n\n"
            f"በቆረጡት የሎተሪ ቲኬት ቁጥር **{winner_number}** አሸናፊ ሆነዋል። "
            "እባክዎ ሽልማትዎን ለመቀበል አስተዳዳሪውን ያነጋግሩ።"
        )

        # 4. ለአሸናፊው በግል (Inbox) መላክ
        try:
            await bot.send_message(winner_user_id, private_text)
        except Exception as e:
            print(f"ለአሸናፊው መላክ አልተቻለም: {e}")

        # 5. ወደ ቴሌግራም ግሩፕ/ቻናል መላክ
        try:
            await bot.send_message(GROUP_CHAT_ID, public_text)
        except Exception as e:
            print(f"ወደ ግሩፕ መላክ አልተቻለም: {e}")

        # 6. ለአድሚኑ ማረጋገጫ መስጠት
        await message.answer(f"✅ አሸናፊው ተለይቷል፦ @{winner_name}\nመረጃው በዳታቤዝ ተመዝግቧል።")

    except Exception as e:
        print(f"Error: {e}")
        await message.answer("ስህተት ተከስቷል።")
    
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
                  
