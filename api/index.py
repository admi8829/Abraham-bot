import os
import asyncio
import random
import html  # ለጸዳ የጽሁፍ አቀራረብ (Formatting)
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup 
from aiogram.fsm.context import FSMContext        
from supabase import create_client, Client

# --- 1. Environment Variables ---
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BASE_URL = os.getenv("WEBHOOK_URL") 
ADMIN_ID = os.getenv("ADMIN_ID") 
CHANNEL_ID = -1003866954136  

# --- 2. Initialization ---
bot = Bot(token=TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

# Webhook paths
WEBHOOK_PATH = f"/bot/{TOKEN}"
FINAL_WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

# --- 3. FSM States ---
class LotteryStates(StatesGroup):
    waiting_for_phone = State()          
    waiting_for_receipt = State()        
    waiting_for_broadcast_content = State() 
    waiting_for_broadcast_range = State()   

# --- 4. Helper Functions ---
async def is_member(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

# --- 5. Keyboards ---
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

# --- 6. Handlers ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    # የተጠቃሚውን ስም ከ HTML ስህተት ነፃ በሆነ መልኩ መያዝ
    user_full_name = html.escape(message.from_user.full_name)
    username = message.from_user.username or "User"
    
    # 1. የቻናል ግዴታ ቼክ (Mandatory Channel Join)
    if not await is_member(user_id):
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📢 Join Our Channel", url="https://t.me/ethiouh"))
        kb.row(types.InlineKeyboardButton(text="🔄 I have joined", callback_data="check_join"))
        
        join_text = (
            f"👋 <b>Welcome {user_full_name}!</b>\n\n"
            "⚠️ <b>Access Denied!</b>\n"
            "To use this bot and participate in our lottery, you must join our official channel first.\n\n"
            "<i>This helps you stay updated with winners and news!</i>"
        )
        await message.answer(join_text, reply_markup=kb.as_markup(), parse_mode="HTML")
        return

    # 2. Referral Logic (ከራሱ ሊንክ እንዳይገባ መከላከል)
    referrer_id = None
    if message.text and len(message.text.split()) > 1:
        ref_arg = message.text.split()[1]
        if ref_arg.isdigit():
            temp_referrer = int(ref_arg)
            if temp_referrer != user_id:
                referrer_id = temp_referrer

    # 3. Database Registration (Default: English)
    try:
        res = supabase.table("users").select("*").eq("user_id", user_id).execute()
        
        if not res.data:
            # አዲስ ተጠቃሚ ሲመዘገብ Default 'en' (English) እንዲሆን
            supabase.table("users").insert({
                "user_id": user_id, 
                "username": username,
                "full_name": user_full_name,
                "lang": 'en', # ተቀይሯል ወደ English
                "referred_by": referrer_id,
                "phone": None
            }).execute()
            
            user_lang = 'en'
            if referrer_id:
                try: 
                    await bot.send_message(referrer_id, f"🎉 <b>New Referral!</b>\n{user_full_name} has joined using your link.", parse_mode="HTML")
                except: pass
        else:
            user_lang = res.data[0].get('lang', 'en')
    except Exception as e:
        print(f"DB Error: {e}")
        user_lang = 'en'

    # 4. Welcome Message (ማራኪ እና ጽዱ ዲዛይን)
    if user_lang == "am":
        welcome_text = (
            f"✨ <b>ሰላም {user_full_name}!</b> ✨\n\n"
            f"እንኳን ወደ <b>E-Lottery</b> ትኬት መቁረጫ በደህና መጡ።\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>እድለኛ ይሁኑ!</b> አሁኑኑ ትኬት በመቁረጥ የሽልማቱ ባለቤት ይሁኑ።\n"
            f"መልካም ዕድል! 🍀"
        )
    else:
        welcome_text = (
            f"✨ <b>Hello {user_full_name}!</b> ✨\n\n"
            f"Welcome to <b>E-Lottery</b> Ticket Bot.\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>Good Luck!</b> Buy a ticket now and stand a chance to win big prizes.\n"
            f"Let the luck be with you! 🍀"
        )

    # አንድ መልእክት ብቻ ነው የሚላከው (ከ Main Menu ጋር)
    await message.answer(welcome_text, reply_markup=get_main_menu(user_lang), parse_mode="HTML")

@dp.callback_query(F.data == "check_join")
async def check_join_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await is_member(user_id):
        await callback.message.delete()
        # ለ start_handler አርቲፊሻል ሜሴጅ መፍጠር
        callback.message.text = "/start" 
        await start_handler(callback.message)
    else:
        await callback.answer("⚠️ You haven't joined the channel yet!", show_alert=True)
        
# 1. ትኬት ቁረጥ ሲባል የሚጀምረው ክፍል
@dp.message(F.text.in_({"➕ አዲስ ትኬት ቁረጥ", "➕ Buy New Ticket"}))
async def buy_ticket_step1(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # የተጠቃሚውን መረጃ ከዳታቤዝ ማምጣት
    try:
        res = supabase.table("users").select("lang", "phone").eq("user_id", user_id).execute()
        user_data = res.data[0] if res.data else {"lang": "am", "phone": None}
    except Exception as e:
        print(f"DB Error: {e}")
        user_data = {"lang": "am", "phone": None}

    lang = user_data.get('lang', 'am')
    phone = user_data.get('phone')

    # 2. ስልኩ ቀድሞ ካለ በቀጥታ ወደ ሽልማት ዝርዝር ማለፍ
    if phone:
        await show_prizes_and_pay(message, lang)
        return

    # 3. ስልኩ ከሌለ State ሴት እናደርጋለን (ቦቱ ስልክ እየጠበቀ መሆኑን እንዲያውቅ)
    await state.set_state(LotteryStates.waiting_for_phone)

    kb_builder = ReplyKeyboardBuilder()
    kb_builder.row(types.KeyboardButton(text="📲 ስልክ ቁጥርህን አጋራ / Share Contact", request_contact=True))
    
    if lang == "am":
        text = "🔐 <b>የደህንነት ማረጋገጫ</b>\n\nትኬት ለመቁረጥ መጀመሪያ ስልክ ቁጥርዎን ማጋራት አለብዎት። ይህ አሸናፊ ሲሆኑ በስልክ ለመደወል ይጠቅመናል።"
    else:
        text = "🔐 <b>Security Verification</b>\n\nPlease share your contact first to buy a ticket. This helps us call you if you win."
    
    await message.answer(text, reply_markup=kb_builder.as_markup(resize_keyboard=True, one_time_keyboard=True), parse_mode="HTML")

# 4. ተጠቃሚው ስልኩን ሲልክ የሚሰራው ክፍል
# --- 4. ተጠቃሚው ስልኩን ሲልክ የሚሰራው ክፍል (የተስተካከለ) ---
@dp.message(LotteryStates.waiting_for_phone, F.contact)
async def handle_contact(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    full_name = html.escape(message.from_user.full_name)
    username = message.from_user.username or "User"
    
    try:
        # 1. መጀመሪያ በ Update ለመሞከር (ተጠቃሚው ቀድሞ በ /start ተመዝግቦ ከሆነ)
        update_res = supabase.table("users").update({"phone": phone}).eq("user_id", user_id).execute()
        
        # 2. Update ካልሰራ (ተጠቃሚው በሆነ ምክንያት ዳታቤዝ ውስጥ ካልተገኘ) አዲስ እንመዘግባለን
        if not update_res.data:
            supabase.table("users").upsert({
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "phone": phone,
                "lang": 'am'
            }).execute()
        
        # 3. የቋንቋ ምርጫውን ከዳታቤዝ እናምጣ (ካልተገኘ 'am' እንጠቀማለን)
        lang_res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        lang = lang_res.data[0].get('lang', 'am') if lang_res.data else 'am'

        # 4. ለተጠቃሚው ማረጋገጫ መስጠት
        if lang == "am":
            success_msg = "✅ <b>ስልክዎ በትክክል ተመዝግቧል!</b>"
        else:
            success_msg = "✅ <b>Your phone has been registered!</b>"
            
        await message.answer(success_msg, reply_markup=get_main_menu(lang), parse_mode="HTML") 

        # 5. ስቴቱን ማጽዳት (ስልክ መቀበል ስለጨረስን)
        await state.clear()

        # 6. በቀጥታ ወደ ሽልማት እና ክፍያ ዝርዝር መውሰድ
        await show_prizes_and_pay(message, lang)
        
    except Exception as e:
        # ስህተት ካለ እዚህ ጋር ይታያል
        print(f"❌ Error in handle_contact: {e}")
        error_text = "⚠️ ይቅርታ፣ ስልክዎን መመዝገብ አልተቻለም። እባክዎ ትንሽ ቆይተው እንደገና ይሞክሩ።"
        await message.answer(error_text)
        
# ሽልማቶችን የሚያሳይ እና የክፍያ በተን የሚልክ ረዳት ፈንክሽን
async def show_prizes_and_pay(message: types.Message, lang: str):
    try:
        # 1. ሽልማቶችን ከዳታቤዝ ማምጣት (ከፎቶው መዋቅር ጋር የተሳሰረ)
        # ማሳሰቢያ፡ በዳታቤዝህ ላይ 'lang' የሚል ኮለም ካለ .eq("lang", lang) መጠቀም ትችላለህ
        # ካለበለዚያ ሁሉንም አምጥቶ በኮድ መለየት ይሻላል
        prizes_res = supabase.table("prizes").select("rank, amount").execute()
        prizes = prizes_res.data
        
        prize_list = ""
        # በደረጃቸው (Rank) ቅደም ተከተል እንዲቀመጡ
        for p in sorted(prizes, key=lambda x: x['rank']):
            r = p['rank']
            amt = p['amount']
            prize_list += f"🏆 <b>{r}</b> — {amt}\n"

        # 2. Button ማዘጋጀት
        inline_kb = InlineKeyboardBuilder()
        pay_btn_text = "💳 ክፍያ ፈጽም / Pay Now" # ለሁለቱም ቋንቋ እንዲሆን
        inline_kb.row(types.InlineKeyboardButton(text=pay_btn_text, callback_data="show_payment"))

        # 3. መልእክቱን በቋንቋ መለየት (HTML Style)
        if lang == "am":
            info_text = (
                "🎁 <b>የእለቱ የሽልማት ዝርዝር</b> 🎁\n"
                "━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{prize_list}\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "🎫 <b>የአንድ ትኬት ዋጋ:</b> <code>50 ETB</code>\n\n"
                "👉 <i>ለመቀጠል እና ትኬት ለመቁረጥ 'ክፍያ ፈጽም' የሚለውን ይጫኑ።</i>"
            )
        else:
            info_text = (
                "🎁 <b>Today's Prize List</b> 🎁\n"
                "━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{prize_list}\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "🎫 <b>Ticket Price:</b> <code>50 ETB</code>\n\n"
                "👉 <i>Click 'Pay Now' below to buy your ticket and participate.</i>"
            )

        # 4. መልእክቱን መላክ
        await message.answer(info_text, reply_markup=inline_kb.as_markup(), parse_mode="HTML")

    except Exception as e:
        print(f"Error showing prizes: {e}")
        error_msg = "❌ ስህተት ተከስቷል! / Error occurred!"
        await message.answer(error_msg)
            
# ሐ. የክፍያ መረጃ (Callback)
@dp.callback_query(F.data == "show_payment")
async def process_payment_info(callback: types.CallbackQuery):
    # 1. የተጠቃሚውን ቋንቋ ከዳታቤዝ ማግኘት
    try:
        res_lang = supabase.table("users").select("lang").eq("user_id", callback.from_user.id).execute()
        lang = res_lang.data[0].get('lang', 'en') if res_lang.data else 'en'
    except:
        lang = 'en'

    # ለመክፈያነት የሚውለው ስልክ ቁጥር (እዚህ ጋር ያንተን ቁጥር ተካው)
    PAYMENT_PHONE = "09XXXXXXXX"

    if lang == "am":
        payment_text = (
            "💳 <b>የክፍያ መመሪያ (Payment Steps)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>ደረጃ 1፦</b> በቴሌብር (Telebirr) <code>50 ETB</code> ይላኩ።\n\n"
            f"📍 <b>የመክፈያ ስልክ ቁጥር፦</b> <code>{PAYMENT_PHONE}</code>\n"
            "<i>(ቁጥሩን ለመገልበጥ ከላይ ያለውን ቁጥር ይጫኑት)</i>\n\n"
            "<b>ደረጃ 2፦</b> ክፍያውን እንደፈጸሙ የክፍያውን ማረጋገጫ <b>ደረሰኝ (Screenshot)</b> እዚህ ቦት ላይ ይላኩ።\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ <b>ማሳሰቢያ፦</b> ትክክለኛውን ደረሰኝ መላክዎን ያረጋግጡ። አድሚኖቻችን መረጃውን አረጋግጠው ትኬትዎን ይልካሉ።"
        )
    else:
        payment_text = (
            "💳 <b>Payment Instruction</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Step 1:</b> Send <code>50 ETB</code> via Telebirr.\n\n"
            f"📍 <b>Payment Phone Number:</b> <code>{PAYMENT_PHONE}</code>\n"
            "<i>(Tap the number above to copy it)</i>\n\n"
            "<b>Step 2:</b> After payment, send the <b>Confirmation Receipt (Screenshot)</b> directly here to this bot.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ <b>Notice:</b> Please ensure you send the correct screenshot. Our admins will verify and issue your ticket."
        )

    # 2. መልእክቱን መላክ (በ HTML)
    await callback.message.answer(payment_text, parse_mode="HTML")
    await callback.answer()
    
# 2. ስክሪንሻት መቀበያ (ለአድሚን መላኪያ)


@dp.message(F.photo)
async def handle_photos(message: types.Message):
    user_id = message.from_user.id
    # የተጠቃሚውን ስም ለዲዛይን ማዘጋጀት
    first_name = html.escape(message.from_user.first_name or "N/A")
    username = message.from_user.username
    user_display = f"@{username}" if username else "No Username"
    
    # የፎቶው መለያዎች
    photo_file_id = message.photo[-1].file_id
    file_unique_id = message.photo[-1].file_unique_id

    # --- 1. የብሮድካስት ተግባር (Admin Only) ---
    if str(user_id) == str(ADMIN_ID) and message.caption and message.caption.startswith("/broadcast"):
        content = message.caption.replace("/broadcast", "").strip()
        parts = content.split("|")
        msg_text = parts[0].strip()
        btn_text = parts[1].strip() if len(parts) > 1 else None
        btn_url = parts[2].strip() if len(parts) > 2 else None

        kb = None
        if btn_text and btn_url:
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(text=btn_text, url=btn_url))
            kb = builder.as_markup()

        try:
            users_res = supabase.table("users").select("user_id").execute()
            user_list = users_res.data
            status_msg = await message.answer(f"⏳ Sending to {len(user_list)} users...")
            
            sent_count = 0
            for user in user_list:
                try:
                    await bot.send_photo(
                        chat_id=user['user_id'], 
                        photo=photo_file_id, 
                        caption=msg_text, 
                        reply_markup=kb, 
                        parse_mode="HTML"
                    )
                    sent_count += 1
                    if sent_count % 25 == 0: await asyncio.sleep(1)
                except: continue
            await status_msg.edit_text(f"✅ Broadcast Complete! Sent to {sent_count} users.")
        except Exception as e:
            await message.answer(f"❌ Broadcast Error: {e}")
        return

    # --- 2. የደረሰኝ መቀበያ ተግባር (Users) ---
    else:
        try:
            # ሀ. የተጠቃሚውን ቋንቋ እና ስልክ ማግኘት
            res_user = supabase.table("users").select("lang", "phone").eq("user_id", user_id).execute()
            user_info = res_user.data[0] if res_user.data else {"lang": "en", "phone": "N/A"}
            lang = user_info.get('lang', 'en')
            phone = user_info.get('phone', 'N/A')

            # ለ. የደረሰኝ ድግግሞሽ መከላከያ (Duplicate Check)
            check_dup = supabase.table("payments").select("*").eq("file_unique_id", file_unique_id).execute()
            if check_dup.data:
                msg = "⚠️ <b>ይህ ደረሰኝ ቀድሞ ጥቅም ላይ ውሏል!</b>" if lang == 'am' else "⚠️ <b>This receipt has already been used!</b>"
                await message.answer(msg, parse_mode="HTML")
                return

            # ሐ. ክፍያውን በዳታቤዝ መመዝገብ
            # ማሳሰቢያ፡ 'file_unique_id' በዳታቤዝህ ላይ መኖሩን አረጋግጥ
            supabase.table("payments").insert({
                "user_id": user_id, 
                "file_id": photo_file_id, 
                "file_unique_id": file_unique_id, 
                "status": "pending"
            }).execute()

            # መ. ለአድሚን የሚላክ ማራኪ መልእክት (HTML)
            admin_text = (
                "📥 <b>[ NEW PAYMENT RECEIPT ]</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Name:</b> {first_name}\n"
                f"🔗 <b>Username:</b> {user_display}\n"
                f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
                f"📞 <b>Phone:</b> <code>{phone}</code>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ <b>Action:</b> Verify the payment and choose below:"
            )

            admin_kb = InlineKeyboardBuilder()
            admin_kb.row(
                types.InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{user_id}"),
                types.InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}")
            )

            await bot.send_photo(
                chat_id=int(ADMIN_ID),
                photo=photo_file_id,
                caption=admin_text,
                reply_markup=admin_kb.as_markup(),
                parse_mode="HTML"
            )

            # ሠ. ለተጠቃሚው የሚላክ ማረጋገጫ
            if lang == "am":
                conf_text = (
                    "✅ <b>ደረሰኙ ደርሶናል!</b>\n\n"
                    "ክፍያዎ በአድሚን ተረጋግጦ ሲያልቅ የሎተሪ ትኬት ቁጥርዎ ይላክልዎታል። እባክዎ በትዕግስት ይጠብቁ።"
                )
            else:
                conf_text = (
                    "✅ <b>Receipt Received!</b>\n\n"
                    "Your payment is being verified. Once approved, your lottery ticket will be sent to you."
                )
            
            await message.answer(conf_text, parse_mode="HTML")
            
        except Exception as e:
            # ስህተቱን በ Terminal ላይ ለማየት
            print(f"Detailed Error: {e}")
            await message.answer(f"❌ <b>Error processing photo:</b> <code>{e}</code>", parse_mode="HTML")


@dp.message(F.text.in_({"👤 የእኔ መረጃ", "👤 My Info"}))
async def my_info_handler(message: types.Message):
    user_id = message.from_user.id
    
    try:
        # 1. የተጠቃሚውን መረጃ ከዳታቤዝ ማምጣት
        res_user = supabase.table("users").select("*").eq("user_id", user_id).execute()
        if not res_user.data:
            return await message.answer("User not found in database.")
        
        user_data = res_user.data[0]
        lang = user_data.get('lang', 'en')
        full_name = html.escape(user_data.get('full_name', 'N/A'))
        username = f"@{user_data.get('username')}" if user_data.get('username') else "N/A"
        phone = user_data.get('phone') or ("ያልተመዘገበ" if lang == "am" else "Not Registered")

        # 2. ሁሉንም ትኬቶች እና የክፍያ ሁኔታዎች ማምጣት
        # የጸደቁ ትኬቶች
        res_approved = supabase.table("tickets").select("ticket_number").eq("user_id", user_id).eq("status", "approved").execute()
        # በመጠባበቅ ላይ ያሉ ክፍያዎች
        res_pending = supabase.table("payments").select("id").eq("user_id", user_id).eq("status", "pending").execute()
        # ውድቅ የተደረጉ ክፍያዎች
        res_rejected = supabase.table("payments").select("id").eq("user_id", user_id).eq("status", "rejected").execute()

        approved_tickets = res_approved.data
        pending_count = len(res_pending.data)
        rejected_count = len(res_rejected.data)

        # 3. መልእክቱን በቋንቋ ማዘጋጀት (HTML Style)
        if lang == "am":
            ticket_list = ""
            if not approved_tickets:
                ticket_list = "<i>እስካሁን ምንም የጸደቀ ትኬት የለም።</i>"
            else:
                ticket_list = "\n".join([f"• <code>{t['ticket_number']}</code> ✅" for t in approved_tickets])

            status_info = ""
            if pending_count > 0: status_info += f"\n⏳ <b>በመጠባበቅ ላይ፦</b> {pending_count} ክፍያ"
            if rejected_count > 0: status_info += f"\n❌ <b>ውድቅ የተደረጉ፦</b> {rejected_count} ደረሰኝ"

            text = (
                f"👤 <b>የእኔ መረጃ</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 <b>ስም፦</b> {full_name}\n"
                f"🔗 <b>Username፦</b> {username}\n"
                f"📞 <b>ስልክ፦</b> <code>{phone}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎫 <b>የእርስዎ ትኬቶች፦</b>\n"
                f"{ticket_list}\n"
                f"{status_info}\n\n"
                f"🍀 <b>መልካም እድል!</b>"
            )
        else:
            ticket_list = ""
            if not approved_tickets:
                ticket_list = "<i>No approved tickets yet.</i>"
            else:
                ticket_list = "\n".join([f"• <code>{t['ticket_number']}</code> ✅" for t in approved_tickets])

            status_info = ""
            if pending_count > 0: status_info += f"\n⏳ <b>Pending:</b> {pending_count} payments"
            if rejected_count > 0: status_info += f"\n❌ <b>Rejected:</b> {rejected_count} receipts"

            text = (
                f"👤 <b>My Info</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 <b>Name:</b> {full_name}\n"
                f"🔗 <b>Username:</b> {username}\n"
                f"📞 <b>Phone:</b> <code>{phone}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎫 <b>Your Tickets:</b>\n"
                f"{ticket_list}\n"
                f"{status_info}\n\n"
                f"🍀 <b>Good Luck!</b>"
            )

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        print(f"Error in My Info: {e}")
        error_msg = "❌ ስህተት ተከስቷል!" if lang == "am" else "❌ An error occurred!"
        await message.answer(error_msg)



@dp.message(F.text.in_({"🎁 አሸናፊዎች", "🎁 Winners"}))
async def show_winners(message: types.Message):
    user_id = message.from_user.id
    
    try:
        # 1. የተጠቃሚውን ቋንቋ ማወቅ
        res_user = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        lang = res_user.data[0].get('lang', 'en') if res_user.data else 'en'

        # 2. የቅርብ ጊዜ 10 አሸናፊዎችን ከነ ዙራቸው እና ከነ እጣ ደረጃቸው ማምጣት
        # ማሳሰቢያ፡ 'round_no' እና 'prize_rank' በቴብልህ ውስጥ መኖራቸውን አረጋግጥ
        res = supabase.table("winners").select(
            "ticket_number, draw_date, round_no, prize_rank, users(username, full_name)"
        ).order("draw_date", desc=True).limit(10).execute()
        
        winners_list = res.data

        if not winners_list:
            if lang == "am":
                text = (
                    "🏆 <b>አሸናፊዎች</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "እስካሁን ምንም አሸናፊ አልተመዘገበም።\n"
                    "ቀጣዩ ባለዕድል እርስዎ ይሁኑ! 🍀"
                )
            else:
                text = (
                    "🏆 <b>Winners List</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "No winners recorded yet.\n"
                    "Be the next lucky winner! 🍀"
                )
        else:
            header = "🏆 <b>የቅርብ ጊዜ አሸናፊዎች</b>\n" if lang == "am" else "🏆 <b>Recent Winners</b>\n"
            text = header + "━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for w in winners_list:
                # ስም እና ዩዘርኔም ማዘጋጀት
                user_info = w.get('users', {})
                username = f"@{user_info.get('username')}" if user_info.get('username') else "User"
                ticket = w['ticket_number']
                round_no = w.get('round_no', '1') # Default round 1
                rank = w.get('prize_rank', '1') # 1ኛ እጣ፣ 2ኛ እጣ...
                
                if lang == "am":
                    text += (
                        f"<b>ዙር {round_no} | {rank}ኛ ዕጣ</b>\n"
                        f"👤 {username}\n"
                        f"🎫 ትኬት፦ <code>{ticket}</code>\n"
                        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
                    )
                else:
                    text += (
                        f"<b>Round {round_no} | {rank}st Prize</b>\n"
                        f"👤 {username}\n"
                        f"🎫 Ticket: <code>{ticket}</code>\n"
                        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
                    )
            
            text += "\n🎉 <b>እንኳን ደስ አላችሁ!</b>" if lang == "am" else "\n🎉 <b>Congratulations!</b>"

        #await message.answer(text, parse_mode="HTML")

   # except Exception as e:
      #  print(f"Error fetching winners: {e}")
       # error_msg = "❌ አሸናፊዎችን ማግኘት አልተቻለም።" if lang == "am" else "❌ Could not fetch winners."
       # await message.answer(error_msg)
        
   except Exception as e:
        print(f"Detailed Winners Error: {e}")
        # ይህ ለተጠቃሚው ትክክለኛውን የሲስተም ስህተት ያሳያል
        await message.answer(f"❌ Error Detail: <code>{e}</code>", parse_mode="HTML")
    
        
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

# --- 1. ልዩ (Unique) የትኬት ቁጥር መፍጠሪያ Function ---
async def generate_unique_ticket():
    while True:
        # ባለ 6 ዲጂት ቁጥር መፍጠር
        random_num = random.randint(100000, 999999)
        ticket_no = f"LOT-{random_num}"
        
        # ዳታቤዝ ውስጥ መኖሩን ቼክ ማድረግ
        check = supabase.table("tickets").select("ticket_number").eq("ticket_number", ticket_no).execute()
        
        # ቁጥሩ ካልተያዘ ይመልሰዋል
        if not check.data:
            return ticket_no

# --- 2. አድሚኑ ሲያጸድቅ (Approve) ---
@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    
    try:
        # ሀ. የተጠቃሚውን ቋንቋ ማወቅ
        user_res = supabase.table("users").select("lang").eq("user_id", target_id).execute()
        lang = user_res.data[0]['lang'] if user_res.data else 'en'
        
        # ለ. ልዩ 6 ዲጂት ቁጥር ማመንጨት
        ticket_no = await generate_unique_ticket()
        
        # ሐ. በዳታቤዝ ውስጥ መመዝገብ
        supabase.table("tickets").insert({
            "user_id": target_id, 
            "ticket_number": ticket_no, 
            "status": "approved"
        }).execute()
        
        # መ. ለተጠቃሚው የሚላክ ማራኪ መልእክት (HTML)
        if lang == "am":
            user_msg = (
                "🎉 <b>እንኳን ደስ አለዎት! ክፍያዎ ጸድቋል።</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎫 <b>የሎተሪ ቁጥርዎ፦</b> <code>{ticket_no}</code>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ <i>ይህንን ቁጥር በጥንቃቄ ይያዙ። ዕጣው ሲወጣ አሸናፊ መሆንዎን በዚህ ያረጋግጣሉ።</i>\n"
                "<b>መልካም ዕድል! 🍀</b>"
            )
        else:
            user_msg = (
                "🎉 <b>Congratulations! Your payment is approved.</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎫 <b>Your Ticket Number:</b> <code>{ticket_no}</code>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ <i>Keep this number safely. Use it to check if you're a winner.</i>\n"
                "<b>Good Luck! 🍀</b>"
            )

        await bot.send_message(target_id, user_msg, parse_mode="HTML")
        
        # ሠ. አድሚኑ ላይ ያለውን ፎቶ Caption ማስተካከል
        await callback.message.edit_caption(
            caption=f"✅ <b>ጸድቋል! / Approved!</b>\n🎫 ቁጥር: <code>{ticket_no}</code>",
            parse_mode="HTML"
        )
        await callback.answer("Ticket Issued Successfully!")

    except Exception as e:
        print(f"Approve Error: {e}")
        await callback.answer("Error processing approval.", show_alert=True)

# --- 3. አድሚኑ ውድቅ ሲያደርግ (Reject) ---
@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: types.CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    
    try:
        # የተጠቃሚውን ቋንቋ ማወቅ
        user_res = supabase.table("users").select("lang").eq("user_id", target_id).execute()
        lang = user_res.data[0]['lang'] if user_res.data else 'en'

        if lang == "am":
            reject_msg = (
                "❌ <b>ይቅርታ፣ የላኩት ደረሰኝ ተቀባይነት አላገኘም።</b>\n\n"
                "እባክዎ ትክክለኛውን ደረሰኝ መላክዎን ያረጋግጡ ወይም ለበለጠ መረጃ አድሚኑን ያነጋግሩ።"
            )
        else:
            reject_msg = (
                "❌ <b>Sorry, your receipt has been rejected.</b>\n\n"
                "Please make sure to send the correct screenshot or contact support for help."
            )

        await bot.send_message(target_id, reject_msg, parse_mode="HTML")
        
        # አድሚኑ ላይ ያለውን ፎቶ Caption ማስተካከል
        await callback.message.edit_caption(caption="❌ <b>ውድቅ ተደርጓል! / Rejected!</b>", parse_mode="HTML")
        await callback.answer("Rejected Successfully!")

    except Exception as e:
        print(f"Reject Error: {e}")
        await callback.answer("Error processing rejection.")
        

# 5. ቋንቋ መቀየሪያ

# --- 1. የቋንቋ ምርጫ ማሳያ ---
@dp.message(F.text.in_({"🌐 ቋንቋ", "🌐 Language"}))
async def show_language_options(message: types.Message):
    builder = InlineKeyboardBuilder()
    # በተኖቹን በጎንና በጎን (Row) ለማድረግ
    builder.row(
        types.InlineKeyboardButton(text="አማርኛ 🇪🇹", callback_data="set_am"),
        types.InlineKeyboardButton(text="English 🇺🇸", callback_data="set_en")
    )
    
    welcome_text = (
        "🌐 <b>ቋንቋ ይምረጡ / Choose Language</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "እባክዎ የሚፈልጉትን ቋንቋ ከታች ካሉት አማራጮች ይምረጡ።\n"
        "Please select your preferred language from the options below."
    )
    
    await message.answer(welcome_text, reply_markup=builder.as_markup(), parse_mode="HTML")

# --- 2. ምርጫውን መቀበያ እና ዳታቤዝ ማዘመኛ ---
@dp.callback_query(F.data.startswith("set_"))
async def handle_language_choice(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    try:
        # በዳታቤዝ ውስጥ ማዘመን
        supabase.table("users").update({"lang": lang}).eq("user_id", user_id).execute()
        
        # የስኬት መልእክት በቋንቋው
        if lang == "am":
            success_msg = "✅ <b>ቋንቋው ወደ አማርኛ ተቀይሯል!</b>"
            alert_msg = "አማርኛ ተመርጧል"
        else:
            success_msg = "✅ <b>Language has been set to English!</b>"
            alert_msg = "English selected"

        # የቀድሞውን የቋንቋ መምረጫ መልእክት ማጥፋት (Clean UI)
        await callback.message.delete()
        
        # አዲሱን መልእክት ከአዲሱ ሜኑ ጋር መላክ
        await callback.message.answer(
            success_msg, 
            reply_markup=get_main_menu(lang), 
            parse_mode="HTML"
        )
        
        # በትንሿ Notification (Toast) ማሳየት
        await callback.answer(alert_msg)

    except Exception as e:
        print(f"Language Update Error: {e}")
        await callback.answer("Error updating language", show_alert=True)
        
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
async def professional_draw_handler(message: types.Message):
    # 1. የአድሚን ፍቃድ ቼክ (Security)
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    GROUP_CHAT_ID = "-1003878868241" 
    ADMIN_USERNAME = "your_admin_username" # ያንተ ዩዘር ኔም (ያለ @)

    try:
        # 2. ዳታዎችን ከዳታቤዝ ማምጣት
        ticket_res = supabase.table("tickets").select("*").eq("status", "approved").execute()
        prize_res = supabase.table("prizes").select("rank, amount").execute()
        
        all_tickets = ticket_res.data
        all_prizes = {p['rank']: p['amount'] for p in prize_res.data}

        if not all_tickets:
            await message.answer("⚠️ <b>ምንም የጸደቀ ትኬት የለም።</b>", parse_mode="HTML")
            return

        # 3. የእድል ብዛት ስሌት (Weighted Draw)
        all_candidates = [t['user_id'] for t in all_tickets]
        unique_users_count = len(set(all_candidates))

        if unique_users_count < 3:
            await message.answer(f"⚠️ <b>ቢያንስ 3 ተሳታፊ ያስፈልጋል።</b>", parse_mode="HTML")
            return

        # 4. የቆጠራ Animation (Countdown)
        status_msg = await bot.send_message(GROUP_CHAT_ID, "🎰 <b>የዕጣ ዝግጅት ተጀምሯል... / Draw Started...</b>", parse_mode="HTML")
        for anim in ["🕒 <b>3...</b>", "🕑 <b>2...</b>", "🕐 <b>1...</b>", "🚀 <b>እጣው እየወጣ ነው...</b>"]:
            await asyncio.sleep(1.5)
            await status_msg.edit_text(f"🎲 <b>ዕድለኛውን እየፈለግን ነው...</b>\n\n{anim}", parse_mode="HTML")
        
        # ቆጠራው ሲያልቅ የመግቢያ መልእክቱን ማጥፋት
        await bot.delete_message(GROUP_CHAT_ID, status_msg.message_id)

        # 5. 3 አሸናፊዎችን መምረጥ (ያለ መደጋገም)
        winner_uids = []
        temp_list = all_candidates.copy()
        while len(winner_uids) < 3:
            chosen = random.choice(temp_list)
            if chosen not in winner_uids:
                winner_uids.append(chosen)
                temp_list = [uid for uid in temp_list if uid != chosen]

        ranks_display = ["1ኛ 🥇", "2ኛ 🥈", "3ኛ 🥉"]
        db_ranks = ["1ኛ", "2ኛ", "3ኛ"] 

        for i, uid in enumerate(winner_uids):
            rank_label = ranks_display[i]
            rank_key = db_ranks[i]
            prize_amount = all_prizes.get(rank_key, "ሽልማት/Prize")

            # የተጠቃሚ መረጃ
            u_res = supabase.table("users").select("*").eq("user_id", uid).execute()
            user_data = u_res.data[0]
            u_name = html.escape(user_data['username'] or user_data['full_name'])
            u_lang = user_data.get('lang', 'am')

            # የዕድለኛውን ትኬት መምረጥ
            user_tickets = [t for t in all_tickets if t['user_id'] == uid]
            winner_ticket = random.choice(user_tickets)
            t_num = winner_ticket['ticket_number']

            # 6. ዳታቤዝ ማደስ (Record Winner)
            supabase.table("winners").insert({
                "user_id": uid, 
                "ticket_number": t_num, 
                "prize_name": f"{rank_key} - {prize_amount}"
            }).execute()
            supabase.table("tickets").update({"status": "winner"}).eq("ticket_number", t_num).execute()

            # 7. Button ማዘጋጀት (Contact & Buy)
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(text="📞 አድሚን / Contact", url=f"https://t.me/{ADMIN_USERNAME}"))
            builder.row(types.InlineKeyboardButton(text="🎫 ትኬት ቁረጥ / Buy Ticket", callback_data="buy_ticket"))

            # 8. መልእክቱን ማዘጋጀት (Inbox Style)
            # ለአሸናፊው Inbox የሚላክ
            if u_lang == 'am':
                msg_txt = (f"🎁 <b>እንኳን ደስ አለዎት!</b> 🎁\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"እርስዎ የ <b>{rank_label}</b> አሸናፊ ሆነዋል!\n\n"
                           f"💰 <b>ሽልማት:</b> {prize_amount}\n"
                           f"🎫 <b>ትኬት:</b> <code>{t_num}</code>\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"📢 <i>ሽልማትዎን ለመቀበል አድሚኑን ያነጋግሩ።</i>")
            else:
                msg_txt = (f"🎁 <b>Congratulations!</b> 🎁\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"You won the <b>{rank_label}</b> prize!\n\n"
                           f"💰 <b>Prize:</b> {prize_amount}\n"
                           f"🎫 <b>Ticket:</b> <code>{t_num}</code>\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"📢 <i>Contact admin to claim your prize.</i>")

            # ለግሩፕ የሚላክ (Amharic & English በአንድ ላይ)
            group_msg = (f"🎊 <b>የዕጣ አሸናፊ / DRAW WINNER</b> 🎊\n"
                         f"━━━━━━━━━━━━━━━━━━━━\n"
                         f"👤 <b>አሸናፊ:</b> @{u_name}\n"
                         f"🏅 <b>ደረጃ / Rank:</b> {rank_label}\n"
                         f"🎁 <b>ሽልማት / Prize:</b> {prize_amount}\n"
                         f"🎫 <b>ትኬት / Ticket:</b> <code>{t_num}</code>\n"
                         f"━━━━━━━━━━━━━━━━━━━━\n"
                         f"✨ <i>እንኳን ደስ አለዎት! / Congratulations!</i>")

            # 9. መልእክቶቹን መላክ
            # ወደ Inbox
            try:
                await bot.send_message(uid, msg_txt, reply_markup=builder.as_markup(), parse_mode="HTML")
            except:
                await message.answer(f"⚠️ <b>ማሳሰቢያ:</b> @{u_name} ቦቱን Block ስላደረገ Inbox አልደረሰውም።")
            
            # ወደ ግሩፕ
            await bot.send_message(GROUP_CHAT_ID, group_msg, reply_markup=builder.as_markup(), parse_mode="HTML")
            await asyncio.sleep(1) # በየመካከሉ ትንሽ እረፍት (ለማሳመር)

        # 10. የዙር ማጠናቀቂያ (Clean Up)
        supabase.table("tickets").update({"status": "expired"}).eq("status", "approved").execute()
        await message.answer("✅ <b>የዕጣ ማውጫው በስኬት ተጠናቋል።</b>", parse_mode="HTML")

    except Exception as e:
        print(f"Draw Error: {e}")
        await message.answer(f"❌ <b>Error:</b> <code>{e}</code>", parse_mode="HTML")

        
#--- Webhook ---
#@app.on_event("startup")
#async def on_startup():
    #await bot.set_webhook(url=FINAL_WEBHOOK_URL)

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update_data = await request.json()
    update = types.Update.model_validate(update_data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"status": "ok"}
                  
