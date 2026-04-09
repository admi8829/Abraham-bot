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

# ID-ዎቹን ወደ Integer (ቁጥር) መቀየር
try:
    # .strip() በመጠቀም በስህተት የሚገቡ ባዶ ቦታዎችን (Spaces) እናስወግዳለን
    admin_env = os.getenv("ADMIN_ID", "0").strip()
    channel_env = os.getenv("CHANNEL_ID", "0").strip()

    # ባዶ ካልሆኑ ወደ ቁጥር ይቀየራሉ፣ ካልሆነ 0 ይሆናሉ
    ADMIN_ID = int(admin_env) if admin_env else 0
    CHANNEL_ID = int(channel_env) if channel_env else 0

    # አስፈላጊ መረጃዎች አለመኖራቸውን ለማረጋገጥ
    if ADMIN_ID == 0 or CHANNEL_ID == 0:
        print("⚠️ ማስጠንቀቂያ፦ ADMIN_ID ወይም CHANNEL_ID አልተገለጸም (0 ነው)!")

except ValueError:
    print("❌ ስህተት፦ ADMIN_ID ወይም CHANNEL_ID ቁጥር መሆን አለባቸው! እባክዎ በ .env ፋይል ላይ ያስተካክሉ።")
    ADMIN_ID = 0
    CHANNEL_ID = 0
 
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
    first_name = message.from_user.first_name
    username = message.from_user.username or "User"
    
    # ⚠️ ማሳሰቢያ፦ CHANNEL_ID ከላይ በ Environment Variable መገለጹን አረጋግጥ
    # ካልተገለጸ እዚህ ጋር መጻፍ ትችላለህ፦ Global CHANNEL_ID

    # --- 1. የቻናል ግዴታ (Member Check) ---
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["left", "kicked", "null"]:
            # ቻናሉን ካልተቀላቀለ የሚመጣ ውብ መልእክት
            kb = InlineKeyboardBuilder()
            # ቻናል ሊንኩን በ Environment Variable ወይም በቀጥታ እዚህ ያስገቡ
            kb.row(types.InlineKeyboardButton(text="📢 ቻናሉን ተቀላቀል / Join Channel", url="https://t.me/ethiouh")) 
            kb.row(types.InlineKeyboardButton(text="🔄 ተቀላቅያለሁ / I joined", callback_data="check_join"))
            
            join_text = (
                f"👋 **ሰላም {first_name}!**\n\n"
                "⚠️ **ይቅርታ!** ቦቱን ለመጠቀም መጀመሪያ የቴሌግራም ቻናላችንን መቀላቀል አለብዎት።\n\n"
                "ይህም አሸናፊዎችን እና አዳዲስ መረጃዎችን በፍጥነት ለማግኘት ይረዳዎታል።"
            )
            await message.answer(join_text, reply_markup=kb.as_markup(), parse_mode="Markdown")
            return
    except Exception as e:
        print(f"Join check error: {e}")
        # ⚠️ ቦቱ አድሚን ካልሆነ ይህ ስህተት ሊሰጥ ይችላል። በዝምታ እንዲያልፍ ተደርጓል።

    # --- 2. የግብዣ (Referral) ሲስተም ---
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id == user_id: 
            referrer_id = None

    # --- 3. ዳታቤዝ ውስጥ መመዝገብ (ቻናሉን መቀላቀሉ ሲረጋገጥ) ---
    try:
        # መጀመሪያ ተጠቃሚው መኖሩን ቼክ ማድረግ
        res = supabase.table("users").select("*").eq("user_id", user_id).execute()
        
        if not res.data:
            user_lang = 'am' # Default ቋንቋ
            supabase.table("users").insert({
                "user_id": user_id, 
                "username": username, 
                "first_name": first_name,
                "lang": 'am',
                "referred_by": referrer_id,
                "is_active": True
            }).execute()
            
            # ለጋባዡ መረጃ እንዲደርሰው
            if referrer_id:
                try: 
                    await bot.send_message(
                        referrer_id, 
                        f"🎉 **አዲስ ግብዣ!**\n\n{first_name} በእርስዎ ሊንክ ቦቱን ተቀላቅሏል።",
                        parse_mode="Markdown"
                    )
                except: 
                    pass
        else:
            user_lang = res.data[0].get('lang', 'am')
            # ተጠቃሚው ቀድሞ ካለ is_active የሚለውን update ማድረግ ይቻላል
            supabase.table("users").update({"is_active": True}).eq("user_id", user_id).execute()

    except Exception as e:
        print(f"DB Registration Error: {e}")
        user_lang = 'am'

    # --- 4. የዲዛይን ስራ (Welcome Message) ---
    if user_lang == "am":
        welcome_text = (
            f"🎊 **እንኳን ደስ አለዎት {first_name}!** 🎊\n"
            "አባልነታችሁ ተረጋግጧል። አሁን ቦቱን መጠቀም ይችላሉ።\n\n"
            "🎯 **እድለኛ ይሁኑ!** አሁኑኑ ትኬት በመቁረጥ የሽልማቱ ባለቤት ይሁኑ።"
        )
        menu_msg = "🎛 **ከታች ካሉት አማራጮች አንዱን ይምረጡ፦**"
    else:
        welcome_text = (
            f"🎊 **Welcome {first_name}!** 🎊\n"
            "Your membership is verified. You can now use the bot.\n\n"
            "🎯 **Good Luck!** Buy a ticket now and stand a chance to win big."
        )
        menu_msg = "🎛 **Please choose an option from below:**"

    # መልእክቶቹን መላክ
    await message.answer(welcome_text, reply_markup=get_start_inline(), parse_mode="Markdown")
    await message.answer(menu_msg, reply_markup=get_main_menu(user_lang), parse_mode="Markdown")

# --- 5. የ 'Check Join' በተን ሲነካ ---
@dp.callback_query(F.data == "check_join")
async def check_join_callback(callback: types.CallbackQuery):
    # የቀድሞውን "Join Channel" የሚል መልእክት ያጠፋዋል
    try:
        await callback.message.delete()
    except:
        pass
    
    # ድጋሚ start_handler-ን በመጥራት አባልነቱን ቼክ ያደርጋል
    # አባል ከሆነ ይመዘግባል፣ ካልሆነ ደግሞ መልሶ Join በል ይለዋል
    await start_handler(callback.message) 
    await callback.answer("በመፈተሽ ላይ...")
     
    
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
    
# --- ፎቶ መቀበያ (ደረሰኝ ምዝገባን ጨምሮ) ---
@dp.message(F.photo)
async def handle_photos(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "N/A"
    username = message.from_user.username
    photo_id = message.photo[-1].file_id
    user_display = f"@{username}" if username else "No Username"

    # 1. የአድሚን ብሮድካስት ከሆነ
    if str(user_id) == str(ADMIN_ID) and message.caption and message.caption.startswith("/broadcast"):
        content = message.caption.replace("/broadcast", "").strip()
        parts = content.split("|")
        msg_text = parts[0].strip()
        
        kb = None
        if len(parts) > 2:
            btn_text = parts[1].strip()
            btn_url = parts[2].strip()
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(text=btn_text, url=btn_url))
            kb = builder.as_markup()

        try:
            users_res = supabase.table("users").select("user_id").execute()
            user_list = users_res.data
            status_msg = await message.answer(f"⏳ ለ {len(user_list)} ሰዎች መላክ ተጀምሯል...")
            
            sent_count = 0
            for user in user_list:
                try:
                    await bot.send_photo(chat_id=user['user_id'], photo=photo_id, caption=msg_text, reply_markup=kb, parse_mode="Markdown")
                    sent_count += 1
                    if sent_count % 25 == 0: await asyncio.sleep(1)
                except: continue
            await status_msg.edit_text(f"✅ ብሮድካስት ተጠናቋል። ለ {sent_count} ሰዎች ተልኳል።")
        except Exception as e:
            await message.answer(f"❌ ብሮድካስት ስህተት፦ {e}")
        return

    # 2. የተራ ተጠቃሚ የክፍያ ደረሰኝ ከሆነ
    else:
        try:
            # ሀ. የተጠቃሚውን መረጃ ማምጣት
            res_user = supabase.table("users").select("lang", "phone").eq("user_id", user_id).execute()
            user_data = res_user.data[0] if res_user.data else {"lang": "am", "phone": "N/A"}
            lang = user_data.get('lang', 'am')
            phone = user_data.get('phone', 'N/A')

            # ለ. *** አዲሱ ክፍል፦ ክፍያውን በ payments table መመዝገብ ***
            try:
                supabase.table("payments").insert({
                    "user_id": user_id,
                    "file_id": photo_id,
                    "status": "pending"
                }).execute()
            except Exception as db_err:
                print(f"Payments Table Insert Error: {db_err}")
                # ዳታቤዝ ምዝገባው ባይሳካ እንኳ ለአድሚኑ መላኩን እንዲቀጥል እናደርጋለን

            # ሐ. ለአድሚን የሚላክ መረጃ
            admin_text = (
                "📥 **[ አዲስ የክፍያ ደረሰኝ ]**\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **ስም:** `{first_name}`\n"
                f"🔗 **Username:** {user_display}\n"
                f"🆔 **User ID:** `{user_id}`\n"
                f"📞 **ስልክ:** `{phone}`\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ **መመሪያ:** እባክዎ ክፍያውን በባንክ አካውንትዎ አረጋግጠው ያጽድቁ።"
            )

            admin_kb = InlineKeyboardBuilder()
            admin_kb.add(types.InlineKeyboardButton(text="✅ አጽድቅ (Approve)", callback_data=f"approve_{user_id}"))
            admin_kb.add(types.InlineKeyboardButton(text="❌ ውድቅ አድርግ (Reject)", callback_data=f"reject_{user_id}"))
            admin_kb.adjust(2)

            await bot.send_photo(
                chat_id=int(ADMIN_ID),
                photo=photo_id,
                caption=admin_text,
                reply_markup=admin_kb.as_markup(),
                parse_mode="Markdown"
            )

            if lang == "am":
                confirm = "✅ **ደረሰኝዎ ለአስተዳዳሪው ተልኳል።**\nክፍያዎ ተረጋግጦ ሲያልቅ የሎተሪ ቁጥርዎ ይላክልዎታል።"
            else:
                confirm = "✅ **Receipt sent to Admin!**\nYour lottery number will be sent after verification."
            
            await message.answer(confirm, parse_mode="Markdown")

        except Exception as e:
            print(f"Error handling photo: {e}")
            await message.answer("❌ ስህተት ተከስቷል። እባክዎ ቆይተው ይሞክሩ።")
         

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
        
@dp.message(F.text.in_({"👥 ጓደኛ ጋብዝ", "👥 Invite Friends"}))
async def invite_friends_handler(message: types.Message):
    user_id = message.from_user.id
    bot_info = await bot.get_me()
    # የራሳቸው ልዩ የግብዣ ሊንክ
    invite_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    # ቋንቋውን ማወቅ
    res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
    lang = res.data[0].get('lang', 'am') if res.data else 'am'

    # ስንት ሰው እንደጋበዙ ከዳታቤዝ መቁጠር
    ref_count_res = supabase.table("users").select("user_id", count="exact").eq("referred_by", user_id).execute()
    count = ref_count_res.count if ref_count_res.count is not None else 0

    if lang == "am":
        text = (
            "👥 **ጓደኞችዎን ይጋብዙና ሽልማት ያግኙ!**\n\n"
            "የእርስዎን ልዩ የመጋበዣ ሊንክ ለጓደኞችዎ በመላክ ቦቱን እንዲጠቀሙ ይጋብዙ። "
            "ብዙ ሰው በጋበዙ ቁጥር የእድል ቁጥር የማግኘት እድልዎ ይጨምራል!\n\n"
            f"🔗 **የእርስዎ ሊንክ፦**\n`{invite_link}`\n\n"
            f"📊 **የጋበዙት ሰው ብዛት፦** `{count}` ሰዎች"
        )
        share_text = "🎁 እዚህ ቦት ላይ ትኬት ቁርጠው የ10,000 ብር አሸናፊ ይሁኑ! ለመጀመር ሊንኩን ይጫኑ፦"
        btn_msg = "📲 ለጓደኛ ላክ (Share)"
    else:
        text = (
            "👥 **Invite Friends & Win!**\n\n"
            "Share your unique link with friends and invite them to the bot. "
            "The more people you invite, the higher your chances of winning!\n\n"
            f"🔗 **Your Invite Link:**\n`{invite_link}`\n\n"
            f"📊 **Total Invited:** `{count}` people"
        )
        share_text = "🎁 Win 10,000 ETB by buying a lottery ticket! Click here to start:"
        btn_msg = "📲 Share Link"

    # በቀጥታ ለሰው እንዲልኩ (Share Button)
    share_url = f"https://t.me/share/url?url={invite_link}&text={share_text}"
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text=btn_msg, url=share_url))
    
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.message(F.text.in_({"💡 እገዛ", "💡 Help"}))
async def help_handler(message: types.Message):
    user_id = message.from_user.id
    
    # የቋንቋ ምርጫን ማወቅ
    try:
        res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        lang = res.data[0].get('lang', 'am') if res.data else 'am'
    except:
        lang = 'am'

    if lang == "am":
        help_text = (
            "❓ **እንዴት መሳተፍ እችላለሁ?**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ **ትኬት ለመቁረጥ፦**\n"
            "  '➕ አዲስ ትኬት ቁረጥ' የሚለውን ይጫኑ። ስልክዎን ካጋሩ በኋላ ክፍያ ይፈጽሙና ደረሰኝ ይላኩ።\n\n"
            "2️⃣ **ክፍያ ለማጽደቅ፦**\n"
            "  የባንክ ደረሰኝዎን (Screenshot) ሲልኩ አድሚኑ ያረጋግጥና የሎተሪ ቁጥርዎን ይልክልዎታል።\n\n"
            "3️⃣ **ጓደኛ ለመጋበዝ፦**\n"
            "  '👥 ጓደኛ ጋብዝ' የሚለውን ተጠቅመው የራስዎን ሊንክ ለሰዎች ይላኩ።\n\n"
            "4️⃣ **አሸናፊዎችን ለማየት፦**\n"
            "  '🎁 አሸናፊዎች' የሚለው ውስጥ የእለቱን እድለኞች ማግኘት ይችላሉ።\n\n"
            "📞 **ተጨማሪ ጥያቄ ካለዎት፦**\n"
            "  የቴሌግራም አድራሻችን፦ @your_admin_username\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        btn_text = "📞 አስተዳዳሪውን አነጋግር"
    else:
        help_text = (
            "❓ **How can I participate?**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ **To Buy a Ticket:**\n"
            "  Click '➕ Buy New Ticket'. Share your phone, pay the amount, and send the receipt.\n\n"
            "2️⃣ **Approval Process:**\n"
            "  Once you send the screenshot, the admin will verify it and send your lottery number.\n\n"
            "3️⃣ **Inviting Friends:**\n"
            "  Use '👥 Invite Friends' to get your link and invite others to win.\n\n"
            "4️⃣ **Winners List:**\n"
            "  Check '🎁 Winners' to see the daily lucky winners.\n\n"
            "📞 **Need More Help?**\n"
            "  Contact us: @your_admin_username\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        btn_text = "📞 Contact Admin"

    # የውስጥ በተን (Support Link)
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text=btn_text, url="https://t.me/your_admin_username"))
    
    await message.answer(help_text, reply_markup=kb.as_markup(), parse_mode="Markdown")
        

# 3. አድሚኑ ሲያጸድ# 2. Approve Handler
@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    
    # የዘፈቀደ ቁጥር (እንዳይደገም ቼክ ማድረግ ቢቻል ይመረጣል)
    ticket_number = f"LOT-{random.randint(10000, 99999)}"
    
    try:
        # ዳታቤዝ ምዝገባ
        supabase.table("tickets").insert({
            "user_id": user_id,
            "ticket_number": ticket_number,
            "status": "approved"
        }).execute()

        # የተጠቃሚ መረጃ ማምጣት
        res = supabase.table("users").select("lang", "first_name").eq("user_id", user_id).execute()
        user_data = res.data[0] if res.data else {"lang": "am", "first_name": "User"}
        lang = user_data.get('lang', 'am')
        first_name = user_data.get('first_name', 'User')

        # ለተጠቃሚው በ Inbox
        if lang == "am":
            msg = (
                "🎊 **እንኳን ደስ አለዎት!** 🎊\n\n"
                "የከፈሉት ክፍያ ተረጋግጦ ጸድቋል።\n"
                f"🎫 የእርስዎ የሎተሪ ቁጥር፦ `{ticket_number}`\n\n"
                "መልካም እድል!"
            )
        else:
            msg = (
                "🎊 **Congratulations!** 🎊\n\n"
                "Your payment has been verified.\n"
                f"🎫 Your Lottery Number: `{ticket_number}`\n\n"
                "Good Luck!"
            )
        
        await bot.send_message(user_id, msg, parse_mode="Markdown")

        # ለቻናል ማሳወቅ
        await notify_ticket_purchase(first_name, ticket_number)

        # አድሚኑ ላይ ያለውን ፎቶ Caption ማሳመር
        new_caption = (
            f"{callback.message.caption}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ **ሁኔታ፦ ጸድቋል (Approved)**\n"
            f"🎫 **የተሰጠ ቁጥር፦** `{ticket_number}`"
        )
        await callback.message.edit_caption(caption=new_caption, reply_markup=None, parse_mode="Markdown")
        await callback.answer("✅ ትኬቱ ጸድቋል!")

    except Exception as e:
        print(f"Approve Error: {e}")
        await callback.answer("❌ ስህተት፦ ዳታቤዝ ላይ ችግር አለ!")

# 3. Reject Handler
@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: types.CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    
    # የተጠቃሚውን ቋንቋ ማወቅ
    res = supabase.table("users").select("lang").eq("user_id", target_id).execute()
    lang = res.data[0].get('lang', 'am') if res.data else 'am'

    if lang == "am":
        rej_msg = "❌ **ይቅርታ፣ የላኩት ደረሰኝ ተቀባይነት አላገኘም።**\nእባክዎ ትክክለኛውን የክፍያ ማረጋገጫ በድጋሚ ይላኩ ወይም አስተዳዳሪውን ያነጋግሩ።"
    else:
        rej_msg = "❌ **Sorry, your receipt has been rejected.**\nPlease send a valid proof of payment or contact support."

    try:
        await bot.send_message(target_id, rej_msg, parse_mode="Markdown")
        
        new_caption = (
            f"{callback.message.caption}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "❌ **ሁኔታ፦ ውድቅ ተደርጓል (Rejected)**"
        )
        await callback.message.edit_caption(caption=new_caption, reply_markup=None, parse_mode="Markdown")
        await callback.answer("❌ ውድቅ ተደርጓል")
    except Exception as e:
        print(f"Reject Error: {e}")
        await callback.answer("ስህተት ተከስቷል!")
    
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
async def draw_winners(message: types.Message):
    # 1. አድሚን መሆኑን ማረጋገጥ
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    try:
        # 2. 'approved' የሆኑ እና ገና ያላሸነፉ ትኬቶችን ብቻ ማምጣት
        res = supabase.table("tickets").select("*").eq("status", "approved").execute()
        all_tickets = res.data

        if len(all_tickets) < 3:
            await message.answer(f"❌ ስህተት፦ በቂ ትኬት አልተሸጠም። (ቢያንስ 3 ያስፈልጋል፣ በአሁኑ ሰዓት ያለው፦ {len(all_tickets)})")
            return

        # 3. 3 አሸናፊዎችን በዕድል መምረጥ (እንዳይደገገሙ)
        winners = random.sample(all_tickets, k=3)
        ranks = ["1ኛ (1st)", "2ኛ (2nd)", "3ኛ (3rd)"]
        
        public_announcement = "🎊 **የዛሬው የዕጣ አሸናፊዎች ዝርዝር!** 🎊\n"
        public_announcement += "━━━━━━━━━━━━━━━━━━━━\n\n"

        for i, ticket in enumerate(winners):
            u_id = ticket['user_id']
            t_num = ticket['ticket_number']
            rank_label = ranks[i]

            # የተጠቃሚውን መረጃ ማምጣት
            user_res = supabase.table("users").select("username", "lang", "first_name").eq("user_id", u_id).execute()
            user_info = user_res.data[0] if user_res.data else {"username": "User", "lang": "am", "first_name": "User"}
            
            u_name = f"@{user_info['username']}" if user_info['username'] != "N/A" else user_info['first_name']
            u_lang = user_info['lang']

            # ዳታቤዝ ማደስ (ቲኬቱ አሸናፊ ተብሎ እንዲመዘገብ)
            supabase.table("tickets").update({"status": "winner"}).eq("ticket_number", t_num).execute()
            supabase.table("winners").insert({"user_id": u_id, "ticket_number": t_num, "rank": rank_label}).execute()

            # ቻናል ላይ የሚለጠፍ ጽሁፍ
            public_announcement += f"{i+1}️⃣ **{rank_label} አሸናፊ**\n"
            public_announcement += f"👤 ስም፦ {u_name}\n"
            public_announcement += f"🎫 ቁጥር፦ `{t_num}`\n"
            public_announcement += "--------------------\n"

            # 4. ለእድለኛው በ inbox መላክ (በቋንቋው)
            if u_lang == "am":
                p_text = f"🎊 **እንኳን ደስ አለዎት!** 🎊\n\nእርስዎ የ**{rank_label}** አሸናፊ ሆነዋል። የዕጣ ቁጥርዎ፦ **{t_num}**\n\nሽልማትዎን ለመቀበል አስተዳዳሪውን ያነጋግሩ።"
            else:
                p_text = f"🎊 **Congratulations!** 🎊\n\nYou are the **{rank_label}** winner! Your ticket number: **{t_num}**\n\nPlease contact the admin to claim your prize."
            
            try:
                await bot.send_message(u_id, p_text, parse_mode="Markdown")
            except:
                pass # Block ካደረገ ዝም ብሎ ያልፋል

        public_announcement += "\n🎯 ቀጣዩ አሸናፊ እርስዎ ይሁኑ! አሁኑኑ ትኬት ይቁረጡ።"

        # 5. ወደ ቻናል መላክ
        await bot.send_message(chat_id=CHANNEL_ID, text=public_announcement, parse_mode="Markdown")
        
        # 6. ለአድሚኑ ማረጋገጫ
        await message.answer("✅ ዕጣው በስኬት ወጥቷል! አሸናፊዎቹ በቻናል እና በግል መልእክት ደርሷቸዋል።")

    except Exception as e:
        print(f"Draw Error: {e}")
        await message.answer(f"❌ እጣ በማውጣት ላይ ስህተት ተከስቷል፦ {e}")
        
            
    
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
                  
