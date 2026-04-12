import os
import asyncio
import random
import html  # ልዩ ምልክቶችን (እንደ & እና _) ለመቆጣጠር
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup # ለደረጃዎች
from aiogram.fsm.context import FSMContext        # ለደረጃዎች
from supabase import create_client, Client

# 1. Environment Variables (ያሉበት ይቀጥላሉ)
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BASE_URL = os.getenv("WEBHOOK_URL") 
ADMIN_ID = os.getenv("ADMIN_ID") 

# 2. Initialization
bot = Bot(token=TOKEN)
dp = Dispatcher() # FSM አብሮት ይሰራል
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

# --- የሎተሪ ሂደቱን በደረጃ ለመቆጣጠር (FSM States) ---
class LotteryStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_receipt = State()
    waiting_for_broadcast_msg = State() # አዲስ የተጨመረ - ብሮድካስት መልእክት ለመቀበል

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
    CHANNEL_ID = -1003866954136  # ያንተ የቻናል ID
    
    # --- 1. የቻናል ግዴታ (Member Check) ---
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["left", "kicked"]:
            # ቻናሉን ካልተቀላቀለ የሚመጣ መልእክት
            kb = InlineKeyboardBuilder()
            kb.row(types.InlineKeyboardButton(text="📢 ቻናሉን ተቀላቀል / Join Channel", url="https://t.me/ethiouh")) # የቻናልህን ሊንክ እዚህ ቀይረው
            kb.row(types.InlineKeyboardButton(text="🔄 ተቀላቅያለሁ / I joined", callback_data="check_join"))
            
            join_text = (
                "⚠️ **ይቅርታ!**\n\nቦቱን ለመጠቀም መጀመሪያ የቴሌግራም ቻናላችንን መቀላቀል አለብዎት። "
                "ይህም አሸናፊዎችን እና አዳዲስ መረጃዎችን በፍጥነት ለማግኘት ይረዳዎታል።"
            )
            await message.answer(join_text, reply_markup=kb.as_markup())
            return
    except Exception as e:
        print(f"Join check error: {e}")

    # --- 2. የግብዣ (Referral) ሲስተም ---
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id == user_id: referrer_id = None

    # --- 3. ዳታቤዝ ውስጥ መመዝገብ ---
    try:
        res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        
        if not res.data:
            user_lang = 'am'
            supabase.table("users").insert({
                "user_id": user_id, 
                "username": username, 
                "lang": 'am',
                "referred_by": referrer_id # ጋባዡ እዚህ ይመዘገባል
            }).execute()
            
            # ለጋባዡ መረጃ እንዲደርሰው (ከተፈለገ)
            if referrer_id:
                try: await bot.send_message(referrer_id, "🎉 አዲስ ሰው በእርስዎ ሊንክ ቦቱን ተቀላቅሏል!")
                except: pass
        else:
            user_lang = res.data[0].get('lang', 'am')
    except Exception as e:
        print(f"DB Error: {e}")
        user_lang = 'am'

    # --- 4. የዲዛይን ስራ (Welcome Message) ---
    if user_lang == "am":
        welcome_text = (
            f"👋 **ሰላም {message.from_user.first_name}!**\n"
            "ወደ ትኬት መቁረጫ ቦት በደህና መጡ።\n\n"
            "🎯 **እድለኛ ይሁኑ!** አሁኑኑ ትኬት በመቁረጥ የሽልማቱ ባለቤት ይሁኑ።"
        )
        menu_msg = "🎛 ከታች ካሉት አማራጮች አንዱን ይምረጡ፦"
    else:
        welcome_text = (
            f"👋 **Hello {message.from_user.first_name}!**\n"
            "Welcome to our Lottery Ticket Bot.\n\n"
            "🎯 **Good Luck!** Buy a ticket now and stand a chance to win big."
        )
        menu_msg = "🎛 Please choose an option from below:"

    await message.answer(welcome_text, reply_markup=get_start_inline(), parse_mode="Markdown")
    await message.answer(menu_msg, reply_markup=get_main_menu(user_lang))

# --- 5. የ 'Check Join' በተን ሲነካ ---
@dp.callback_query(F.data == "check_join")
async def check_join_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    await start_handler(callback.message) # ድጋሚ Start-ን እንዲያሄድ
    await callback.answer()
    
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
async def handle_receipt(message: types.Message):
    user_id = message.from_user.id
    
    # 1. መጀመሪያ ተጠቃሚው በትክክል ክፍያ እንዲልክ ተጠይቆ እንደሆነ ቼክ እናደርጋለን
    # በዳታቤዝ ውስጥ የተጠቃሚውን ቋንቋ ወይም ሁኔታ የምናይበትን ሰንጠረዥ እንጠቀማለን
    user_data = supabase.table("users").select("lang").eq("user_id", user_id).execute()
    
    if not user_data.data:
        # ተጠቃሚው ገና /start ካላላ አይፈቀድለትም
        return

    # 2. የፎቶውን Unique ID መውሰድ (ለማጭበርበር መከላከያ)
    photo_unique_id = message.photo[-1].file_unique_id
    photo_id = message.photo[-1].file_id

    # 3. ፎቶው ቀድሞ ጥቅም ላይ መዋሉን ቼክ ማድረግ
    dup_check = supabase.table("payments").select("file_id").eq("file_id", photo_unique_id).execute()
    if dup_check.data:
        await message.reply("⚠️ ይህ ደረሰኝ ቀድሞ ጥቅም ላይ ውሏል! እባክዎ ትክክለኛ ደረሰኝ ይላኩ።")
        return

    # 4. Username አቀራረብን ማስተካከል
    # username ካለው @ ጨምሮ ያመጣል፣ ከሌለው 'ስም የለውም' ይላል
    user_handle = f"@{message.from_user.username}" if message.from_user.username else "ስም የለውም (No Username)"
    full_name = message.from_user.full_name

    # 5. ለ Admin መላክ
    admin_caption = (
        "📩 **አዲስ የክፍያ ደረሰኝ ደርሷል**\n\n"
        f"👤 **ስም፦** {full_name}\n"
        f"🆔 **ዩዘር ስም፦** {user_handle}\n"
        f"🔢 **User ID፦** `{user_id}`\n"
        "--------------------------\n"
        "እባክዎ ባንክዎን አረጋግጠው ያጽድቁ።"
    )

    # አጽድቅ እና ሰርዝ በተኖችን ማዘጋጀት
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ አጽድቅ (Approve)", callback_data=f"approve_{user_id}")
    builder.button(text="❌ ሰርዝ (Reject)", callback_data=f"reject_{user_id}")
    builder.adjust(2)

    try:
        # ለ Admin መላክ
        await bot.send_photo(
            ADMIN_ID,
            photo_id,
            caption=admin_caption,
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        
        # የክፍያ ሙከራውን መመዝገብ
        supabase.table("payments").insert({
            "user_id": user_id,
            "file_id": photo_unique_id
        }).execute()

        await message.reply("✅ ደረሰኝዎ ለአስተዳዳሪው ተልኳል። ሲረጋገጥ የትኬት ቁጥር ይላክልዎታል።")
        
    except Exception as e:
        print(f"Error: {e}")
        await message.reply("ስህተት ተከስቷል። እባክዎ ቆይተው ይሞክሩ።")
        
            

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
        

# 3. አድሚኑ ሲያጸድቅ
@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    # አድሚን መሆኑን ማረጋገጥ
    if str(callback.from_user.id) != str(ADMIN_ID):
        await callback.answer("ያልተፈቀደ ሙከራ!", show_alert=True)
        return

    target_id = int(callback.data.split("_")[1])
    
    try:
        # 1. መጀመሪያ ተጠቃሚው ቀድሞ ትኬት ተቆርጦለት እንደሆነ ቼክ ማድረግ (ለጥንቃቄ)
        # ይህ አድሚኑ በተኑን ሁለት ጊዜ ቢጫነው እንዳይደገም ይረዳል
        check_res = supabase.table("tickets").select("*").eq("user_id", target_id).eq("status", "approved").execute()
        
        # 2. ልዩ (Unique) የትኬት ቁጥር በ While Loop መፍጠር
        ticket_no = ""
        while True:
            # 6 ዲጂት ያለው ቁጥር በመጠቀም የመሳሳት እድሉን መቀነስ
            random_num = random.randint(100000, 999999)
            ticket_no = f"LOT-{random_num}"
            
            # ይህ ቁጥር ዳታቤዝ ውስጥ መኖሩን ማረጋገጥ
            dup_check = supabase.table("tickets").select("ticket_number").eq("ticket_number", ticket_no).execute()
            
            if not dup_check.data: # ቁጥሩ ዳታቤዝ ውስጥ ከሌለ Loop-ን አቁም
                break
        
        # 3. ትኬቱን በዳታቤዝ ውስጥ መመዝገብ
        supabase.table("tickets").insert({
            "user_id": target_id, 
            "ticket_number": ticket_no, 
            "status": "approved"
        }).execute()
        
        # 4. ለተጠቃሚው በ Inbox ማሳወቅ
        success_msg = (
            "🎊 **እንኳን ደስ አለዎት!**\n\n"
            "የላኩት የክፍያ ደረሰኝ ተረጋግጧል።\n"
            f"🎫 የሎተሪ ቁጥርዎ፦ `{ticket_no}`\n\n"
            "እጣው ሲወጣ በቦቱ እና በቻናላችን እናሳውቃለን። መልካም እድል!"
        )
        
        try:
            await bot.send_message(target_id, success_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"ለተጠቃሚው መልእክት መላክ አልተቻለም (User blocked bot): {e}")

        # 5. ለአድሚኑ በተኑን ወደ "ጸድቋል" መቀየር
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n✅ **ጸድቋል!**\nቁጥር፦ `{ticket_no}`",
            reply_markup=None # በተኖቹን ያጠፋቸዋል
        )
        await callback.answer("ክፍያው ጸድቋል!")

    except Exception as e:
        print(f"Approve Error: {e}")
        await callback.answer(f"ስህተት ተከስቷል፦ {e}", show_alert=True)
        
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

# 1. አድሚኑ ብሮድካስት እንዲጀምር ትዕዛዝ መስጫ
@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID): return
    
    await state.set_state(LotteryStates.waiting_for_broadcast_msg)
    await message.answer("📣 ለመላክ የሚፈልጉትን መልእክት ይላኩ (ጽሁፍ ወይም ፎቶ ከነcaption ሊሆን ይችላል)፦\n\nለማቆም /cancel ይበሉ።")

# 2. መልእክቱን ተቀብሎ በከፊል (Pagination) መላኪያ
@dp.message(LotteryStates.waiting_for_broadcast_msg)
async def process_broadcast_step(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID): return
    
    # ሁሉንም ተጠቃሚዎች ማምጣት
    users_data = supabase.table("users").select("user_id").execute()
    users = users_data.data
    
    await message.answer(f"⏳ ለ {len(users)} ተጠቃሚዎች መላክ ተጀምሯል...")

    success = 0
    fail = 0
    
    # ለ Vercel Timeout ጥንቃቄ፡ እዚህ ጋር ለሙከራ የመጀመሪያዎቹን 50 ሰው ብቻ እንውሰድ
    # ብዙ ሰው ካለህ በከፊል መላክ (Pagination) መጠቀም አለብህ
    target_users = users[:50] 

    for user in target_users:
        try:
            # መልእክቱ ፎቶ ከሆነ
            if message.photo:
                await bot.send_photo(
                    chat_id=user['user_id'],
                    photo=message.photo[-1].file_id,
                    caption=html.escape(message.caption) if message.caption else None,
                    parse_mode="HTML"
                )
            # መልእክቱ ጽሁፍ ብቻ ከሆነ
            elif message.text:
                await bot.send_message(
                    chat_id=user['user_id'],
                    text=html.escape(message.text),
                    parse_mode="HTML"
                )
            success += 1
            await asyncio.sleep(0.05) # Flood Control
        except Exception:
            fail += 1

    await state.clear()
    report = (
        "📊 <b>የብሮድካስት ሪፖርት</b>\n\n"
        f"✅ በስኬት ተልኳል፦ {success}\n"
        f"❌ ያልተላከላቸው፦ {fail}\n"
        "💡 <i>ማሳሰቢያ፦ Vercel ላይ ስለሆኑ ለደህንነት ሲባል ለ 50 ሰው ብቻ ተልኳል።</i>"
    )
    await message.answer(report, parse_mode="HTML")

# ብሮድካስት ለማቆም
@dp.message(Command("cancel"), LotteryStates.waiting_for_broadcast_msg)
async def cancel_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ ብሮድካስት ተሰርዟል።")
    

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
                  
