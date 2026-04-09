import os
import asyncio
import random
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
        # የተጠቃሚውን ቋንቋ መፈተሽ
        res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        
        if not res.data:
            # አዲስ ተጠቃሚ ከሆነ መመዝገብ
            user_lang = 'am'
            supabase.table("users").insert({
                "user_id": user_id, 
                "username": username, 
                "lang": 'am'
            }).execute()
        else:
            user_lang = res.data[0].get('lang', 'am')
    except Exception as e:
        print(f"Database error: {e}")
        user_lang = 'am'

    # መልእክቱን ማዘጋጀት (ያለ GIF)
    if user_lang == "am":
        text = "👋 **እንኳን ደህና መጡ!**\n\nለመጀመር '➕ አዲስ ትኬት ቁረጥ' የሚለውን ቁልፍ ይጫኑ።"
        menu_text = "ምርጫዎን ይምረጡ፦"
    else:
        text = "👋 **Welcome!**\n\nClick '➕ Buy New Ticket' to start."
        menu_text = "Choose an option:"

    # 1. መጀመሪያ ኢንላይን በተኑን (Website/YouTube) መላክ
    await message.answer(text, reply_markup=get_start_inline(), parse_mode="Markdown")
    
    # 2. በመቀጠል ዋናውን ሜኑ (Reply Buttons) መላክ
    await message.answer(menu_text, reply_markup=get_main_menu(user_lang))

@dp.message(F.text.in_({"➕ አዲስ ትኬት ቁረጥ", "➕ Buy New Ticket"}))
async def buy_ticket_step1(message: types.Message):
    user_id = message.from_user.id
    
    # 1. የተጠቃሚውን መረጃ ከዳታቤዝ ማምጣት
    res = supabase.table("users").select("lang", "phone").eq("user_id", user_id).execute()
    user_data = res.data[0] if res.data else {"lang": "am", "phone": None}
    lang = user_data.get('lang', 'am')
    phone = user_data.get('phone')

    # 2. ስልኩ ቀድሞ ካለ በቀጥታ ወደ ሽልማት ዝርዝር ማለፍ
    if phone:
        await show_prizes_and_pay(message, lang)
        return

    # 3. ስልኩ ከሌለ እንዲያጋራ መጠየቅ
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📲 ስልክ ቁጥርህን አጋራ / Share Contact", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    if lang == "am":
        text = "🔐 **የደህንነት ማረጋገጫ**\n\nትኬት ለመቁረጥ መጀመሪያ ስልክ ቁጥርዎን ማጋራት አለብዎት። ይህ አሸናፊ ሲሆኑ በስልክ ለመደወል ይጠቅመናል።"
    else:
        text = "🔐 **Security Verification**\n\nPlease share your contact first to buy a ticket. This helps us call you if you win."
    
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.contact)
async def handle_contact(message: types.Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    
    # ስልኩን መመዝገብ
    supabase.table("users").update({"phone": phone}).eq("user_id", user_id).execute()
    
    res_lang = supabase.table("users").select("lang").eq("user_id", user_id).execute()
    lang = res_lang.data[0].get('lang', 'am') if res_lang.data else 'am'

    await message.answer("✅", reply_markup=get_main_menu(lang)) # ዋናው ሜኑ እንዲመለስ
    await show_prizes_and_pay(message, lang)

# ሽልማቶችን የሚያሳይ እና የክፍያ በተን የሚልክ ረዳት ፈንክሽን
async def show_prizes_and_pay(message: types.Message, lang: str):
    try:
        # ሽልማቶችን ከዳታቤዝ ማምጣት
        prizes_res = supabase.table("prizes").select("*").eq("lang", lang).execute()
        prizes = prizes_res.data
        
        prize_list = ""
        for p in prizes:
            prize_list += f"🏆 {p['rank']} እጣ: **{p['amount']}**\n" if lang == "am" else f"🏆 {p['rank']} Prize: **{p['amount']}**\n"

        inline_kb = InlineKeyboardBuilder()
        pay_btn_text = "💳 ክፍያ ፈጽም (Pay Now)" if lang == "am" else "💳 Pay Now"
        inline_kb.button(text=pay_btn_text, callback_data="show_payment")

        if lang == "am":
            info_text = (
                "✨ **የእለቱ የሽልማት ዝርዝር** ✨\n\n"
                f"{prize_list}\n"
                "🎫 **የአንድ ትኬት ዋጋ: 50 ብር**\n\n"
                "ለመቀጠል ከታች ያለውን የክፍያ ቁልፍ ይጫኑ፦"
            )
        else:
            info_text = (
                "✨ **Today's Prize List** ✨\n\n"
                f"{prize_list}\n"
                "🎫 **Ticket Price: 50 ETB**\n\n"
                "Click the button below to proceed to payment:"
            )

        await message.answer(info_text, reply_markup=inline_kb.as_markup(), parse_mode="Markdown")
    except Exception as e:
        print(f"Error showing prizes: {e}")
        error_msg = "ስህተት ተከስቷል፣ እባክዎ በድጋሚ ይሞክሩ።" if lang == "am" else "An error occurred, please try again."
        await message.answer(error_msg)

# ሐ. የክፍያ መረጃ (Callback)
@dp.callback_query(F.data == "show_payment")
async def process_payment_info(callback: types.CallbackQuery):
    res_lang = supabase.table("users").select("lang").eq("user_id", callback.from_user.id).execute()
    lang = res_lang.data[0].get('lang', 'am') if res_lang.data else 'am'

    if lang == "am":
        text = "💳 **የክፍያ መመሪያ**\n\nበ Telebirr (09XXXXXXXX) 50 ብር ይላኩ።\nከከፈሉ በኋላ ደረሰኙን (Screenshot) እዚህ ይላኩ።"
    else:
        text = "💳 **Payment Instruction**\n\nPay 50 ETB via Telebirr (09XXXXXXXX).\nAfter payment, send the Screenshot here."
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()
    

# 2. ስክሪንሻት መቀበያ (ለአድሚን መላኪያ)
@dp.message(F.photo)
async def handle_photos(message: types.Message):
    user_id = message.from_user.id
    
    # --- ሀ. ፎቶው የብሮድካስት ከሆነ (ከአድሚን የመጣና /broadcast የሚል ጽሁፍ ካለው) ---
    if str(user_id) == str(ADMIN_ID) and message.caption and message.caption.startswith("/broadcast"):
        # የብሮድካስት ኮድህን እዚህ ጋር አስገባ
        content = message.caption.replace("/broadcast", "").strip()
        
        # (እዚህ ጋር ቅድም የሰጠሁህ የብሮድካስት መላኪያ ሉፕ ይገባል...)
        await message.answer("የፎቶ ብሮድካስት ተጀምሯል...")
        # ... መላኪያ ኮድ ...
        return # ብሮድካስት ከሆነ እዚህ ጋር ይቁም፣ ወደ ደረሰኝ መቀበያው አይለፍ

    # --- ለ. ፎቶው የደረሰኝ ስክሪንሻት ከሆነ (ከተራ ተጠቃሚ የመጣ) ---
    else:
        # ይህ የድሮው የ handle_screenshot ኮድህ ነው
        photo_id = message.photo[-1].file_id
        username = message.from_user.username or "N/A"

        # ለዳታቤዝ መመዝገብ
        supabase.table("payments").insert({"user_id": user_id, "file_id": photo_id}).execute()

        # ለአድሚን (ለአንተ) መላክ
        admin_kb = InlineKeyboardBuilder()
        admin_kb.button(text="✅ አጽድቅ (Approve)", callback_data=f"approve_{user_id}")
        admin_kb.button(text="❌ ሰርዝ (Reject)", callback_data=f"reject_{user_id}")
        
        await bot.send_photo(
            chat_id=int(ADMIN_ID),
            photo=photo_id,
            caption=f"አዲስ የክፍያ ጥያቄ ከ፦ @{username}\nUser ID: {user_id}",
            reply_markup=admin_kb.as_markup()
        )
                # የቋንቋ ምርጫውን ከላይ ካለው 'lang' ተለዋዋጭ በመጠቀም
        if lang == "am":
            confirmation_text = "✅ ደረሰኙ ተልኳል። አስተዳዳሪው ሲያረጋግጥ የሎተሪ ቁጥር ይላክልዎታል።"
        else:
            confirmation_text = "✅ Receipt sent! You will receive your lottery number once the admin verifies it."
            
        await message.answer(confirmation_text)
        
        
    
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

@dp.message(Command("broadcast"))
async def enhanced_broadcast(message: types.Message):
    # 1. አድሚን መሆንህን ያረጋግጣል
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    # መመሪያ ለአድሚኑ፡ ፎቶ ከሆነ ከፎቶው ስር ጽሁፍ ይጻፋል፣ ጽሁፍ ብቻ ከሆነ ደግሞ በኮማንድ ይላካል
    # አጠቃቀም፡ /broadcast ጽሁፍ | ሊንክ_ስም | ሊንክ_URL
    
    content = message.caption if message.photo else message.text.replace("/broadcast", "").strip()
    
    if not content:
        await message.answer(
            "⚠️ **እንዴት እንደሚጠቀሙ፦**\n\n"
            "**ለጽሁፍ ብቻ፦** `/broadcast መልእክት | ሊንክ ስም | https://link.com` \n"
            "**ለፎቶ፦** ፎቶውን ይላኩና ከስሩ መልእክቱን በተመሳሳይ ቅርጽ ይጻፉ።",
            parse_mode="Markdown"
        )
        return

    # መልእክቱን፣ የሊንክ ስሙን እና URLውን መለየት (| ምልክትን በመጠቀም)
    parts = content.split("|")
    msg_text = parts[0].strip()
    btn_text = parts[1].strip() if len(parts) > 1 else None
    btn_url = parts[2].strip() if len(parts) > 2 else None

    # አዝራር (Button) ካለ ማዘጋጀት
    kb = None
    if btn_text and btn_url:
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text=btn_text, url=btn_url))
        kb = builder.as_markup()

    # 2. ሁሉንም ተጠቃሚዎች ማምጣት
    try:
        res = supabase.table("users").select("user_id").execute()
        user_list = res.data
    except Exception as e:
        await message.answer(f"❌ ስህተት፦ {e}")
        return

    sent_count = 0
    blocked_count = 0
    status_msg = await message.answer(f"⏳ ለ {len(user_list)} ሰዎች መላክ ተጀምሯል...")

    # 3. መላክ መጀመር
    for user in user_list:
        try:
            if message.photo:
                # ፎቶ ካለ በፎቶ ይልካል
                await bot.send_photo(
                    chat_id=user['user_id'],
                    photo=message.photo[-1].file_id,
                    caption=msg_text,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
            else:
                # ጽሁፍ ብቻ ከሆነ
                await bot.send_message(
                    chat_id=user['user_id'],
                    text=msg_text,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
            
            sent_count += 1
            if sent_count % 25 == 0:
                await asyncio.sleep(1) # ፍጥነት መገደቢያ

        except Exception:
            blocked_count += 1

    await status_msg.edit_text(
        f"✅ **ብሮድካስት ተጠናቋል!**\n\n"
        f"📤 የተላከላቸው፦ {sent_count}\n"
        f"🚫 የዘጉ (Blocked)፦ {blocked_count}\n"
        f"👥 ጠቅላላ ተጠቃሚ፦ {len(user_list)}"
    )
    


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
                  
