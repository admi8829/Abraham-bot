import os
import asyncio
import random
import html  # ለጸዳ የጽሁፍ አቀራረብ (Formatting)
from aiogram.enums import ChatAction # ይህ ከላይ ከ import ጋር ይግባ
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
DEVELOPER_ID = os.getenv("DEVELOPER_ID")
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
# --- 4. Helper Functions ---
async def is_member(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False
async def check_channel_membership(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if await is_member(user_id):
        # ዳታቤዝ ውስጥ የተጠቃሚውን ስም እና ቋንቋ መፈለግ
        res = supabase.table("users").select("lang", "full_name").eq("user_id", user_id).execute()
        lang = res.data[0]['lang'] if res.data else 'am'
        name = res.data[0]['full_name'] if res.data else message.from_user.full_name
        
        # ወደ ዋናው ሜኑ መውሰድ
        await send_welcome_msg(message, name, lang)
    else:
        # ቻናል እንዲገባ መጠየቅ
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📢 Join Our Channel", url="https://t.me/ethiouh"))
        kb.row(types.InlineKeyboardButton(text="🔄 አረጋግጥ / Verify", callback_data="check_join"))
        await message.answer("⚠️ ለመቀጠል እባክዎ ቻናላችንን ይቀላቀሉ!", reply_markup=kb.as_markup())
        
        
        
        
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
    

@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    try:
        # በቅድሚያ ተጠቃሚውን መፈለግ
        res = supabase.table("users").select("phone").eq("user_id", user_id).execute()
        
        # ተጠቃሚው ካለ እና ስልክ ካለው በቀጥታ ወደ ቻናል ቼክ
        if res.data and res.data[0].get('phone'):
            return await check_channel_membership(message, state)

        # አዲስ ተጠቃሚ ከሆነ ሪፈራል መያዝ
        if message.text and len(message.text.split()) > 1:
            ref_arg = message.text.split()[1]
            if ref_arg.isdigit() and int(ref_arg) != user_id:
                await state.update_data(referred_by=int(ref_arg))

        # ስልክ ቁጥር መጠየቅ
        await state.set_state(LotteryStates.waiting_for_phone)
        kb = ReplyKeyboardBuilder()
        kb.row(types.KeyboardButton(text="📲 ስልክ ቁጥርዎን ያጋሩ / Share Contact", request_contact=True))
        
        await message.answer(
            f"👋 ሰላም {html.escape(message.from_user.full_name)}!\nለመቀጠል እባክዎ ስልክ ቁጥርዎን ያጋሩ።",
            reply_markup=kb.as_markup(resize_keyboard=True, one_time_keyboard=True)
        )

    except Exception as e:
        print(f"Start Logic Error: {e}")
        # ዳታቤዝ ቢጠፋ እንኳ ስልክ እንዲጠይቅ ማድረግ (Fallback)
        await state.set_state(LotteryStates.waiting_for_phone)
        await message.answer("ለመቀጠል እባክዎ ስልክ ቁጥርዎን ያጋሩ።")
        
# 1. ትኬት ቁረጥ ሲባል የሚጀምረው ክፍል
# 1. ትኬት ቁረጥ ሲባል የሚጀምረው ክፍል
@dp.message(F.text.in_({"➕ አዲስ ትኬት ቁረጥ", "➕ Buy New Ticket"}))
async def buy_ticket_step1(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # 1. ቻናል ውስጥ መኖሩን ቼክ ማድረግ
    if not await is_member(user_id):
        # ካልሆነ ወደ verify መልዕክት መላክ
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📢 Join Our Channel", url="https://t.me/ethiouh"))
        kb.row(types.InlineKeyboardButton(text="🔄 አረጋግጥ / Verify", callback_data="check_join"))
        return await message.answer("⚠️ ትኬት ለመቁረጥ መጀመሪያ ቻናላችንን መቀላቀል አለብዎት!", reply_markup=kb.as_markup())

    # 2. ዳታቤዝ ውስጥ መኖሩን ቼክ ማድረግ
    res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
    if not res.data:
        return await message.answer("⚠️ እባክዎ መጀመሪያ /start ብለው ይመዝገቡ።")

    lang = res.data[0]['lang']
    # 3. ወደ ክፍያ ሂደት ማለፍ
    await show_prizes_and_pay(message, lang)
    
# --- 4. ተጠቃሚው ስልኩን ሲልክ የሚሰራው ክፍል ---
# --- 4. ተጠቃሚው ስልኩን ሲልክ የሚሰራው ክፍል ---
@dp.message(LotteryStates.waiting_for_phone, F.contact)
async def register_and_check_channel(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    
    # የራስን ስልክ መላኩን ማረጋገጥ
    if message.contact.user_id != user_id:
        return await message.answer("⚠️ እባክዎ የራስዎን ስልክ ቁጥር ያጋሩ!")

    data = await state.get_data()
    referrer_id = data.get("referred_by")

    try:
        # መጀመሪያ ተጠቃሚው መኖሩን ማረጋገጥ
        user_exists = supabase.table("users").select("user_id").eq("user_id", user_id).execute()
        
        user_info = {
            "user_id": user_id,
            "username": message.from_user.username,
            "full_name": html.escape(message.from_user.full_name),
            "phone": phone,
            "lang": "am"
        }

        if user_exists.data:
            # ካለ ስልኩን ብቻ እናድሳለን
            supabase.table("users").update({"phone": phone}).eq("user_id", user_id).execute()
        else:
            # ከሌለ አዲስ እንመዘግባለን
            user_info["referred_by"] = referrer_id
            supabase.table("users").insert(user_info).execute()
        
        await state.clear()
        
        # ቻናል ውስጥ መኖሩን ቼክ ማድረግ
        if await is_member(user_id):
            # ቻናል ውስጥ ካለ ዋናው ሜኑ ይከፈትለታል
            await message.answer("✅ ምዝገባዎ ተጠናቅቋል። እንኳን ደህና መጡ!", reply_markup=types.ReplyKeyboardRemove())
            # እዚህ ጋር ዋናውን ሜኑ የሚከፍተውን ፈንክሽን ጥራ (ለምሳሌ send_welcome_msg)
        else:
            # ቻናል ውስጥ ካልሆነ እንዲገባ ይጠየቅ
            kb = InlineKeyboardBuilder()
            kb.row(types.InlineKeyboardButton(text="📢 ቻናላችንን ይቀላቀሉ", url="https://t.me/ethiouh"))
            kb.row(types.InlineKeyboardButton(text="🔄 አረጋግጥ / Verify", callback_data="check_join"))
            await message.answer("⚠️ ለመቀጠል እባክዎ ቻናላችንን ይቀላቀሉ!", reply_markup=kb.as_markup())

    except Exception as e:
        print(f"Error: {e}")
        await message.answer("❌ ስህተት ተፈጥሯል። እባክዎ በሌላ ጊዜ ይሞክሩ።")

@dp.callback_query(F.data == "check_join")
async def verify_membership(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    # አባልነቱን በ is_member ፈንክሽን ቼክ ማድረግ
    if await is_member(user_id):
        # 1. ዳታቤዝ ውስጥ ቋንቋውን እና ስሙን መፈለግ
        res = supabase.table("users").select("lang", "full_name").eq("user_id", user_id).execute()
        lang = res.data[0]['lang'] if res.data else 'am'
        name = res.data[0]['full_name'] if res.data else callback.from_user.full_name
        
        # 2. የእንኳን ደህና መጡ መልዕክት እና ዋና ሜኑ
        await callback.answer("✅ ተረጋግጧል! እንኳን ደህና መጡ።", show_alert=False)
        await callback.message.delete() # የነበረውን የ "Join Channel" መልዕክት ለማጥፋት
        
        await send_welcome_msg(callback.message, name, lang)
    else:
        # አባል ካልሆነ የሚመጣ ማስጠንቀቂያ
        await callback.answer("⚠️ አሁንም ቻናሉን አልተቀላቀሉም። እባክዎ መጀመሪያ ይቀላቀሉ!", show_alert=True)
        
    
# --- 1. ሽልማቶችን የሚያሳይ ፈንክሽን ---
async def show_prizes_and_pay(message: types.Message, lang: str):
    try:
        # የዳታቤዝ ጥሪ (Optimization: የምንፈልገውን ብቻ)
        prizes_res = supabase.table("prizes").select("rank, amount").execute()
        prizes = prizes_res.data or []
        
        prize_list = ""
        if not prizes:
            prize_list = "⏳ <i>Prizes will be announced soon!</i>" if lang == "en" else "⏳ <i>ሽልማቶች በቅርቡ ይፋ ይሆናሉ!</i>"
        else:
            # ሽልማቶችን በደረጃ (Rank) አስተካክሎ ማሳየት
            for p in sorted(prizes, key=lambda x: x['rank']):
                rank_icon = "🥇" if p['rank'] == 1 else "🥈" if p['rank'] == 2 else "🥉" if p['rank'] == 3 else "🏆"
                prize_list += f"{rank_icon} <b>{p['rank']}ኛ ደረጃ:</b> <code>{p['amount']}</code>\n"

        # ማራኪ UI ዲዛይን
        if lang == "am":
            info_text = (
                "🎁 <b>ልዩ የሽልማት ዝርዝር</b> 🎁\n"
                "━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{prize_list}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "🎫 <b>የአንድ ትኬት ዋጋ:</b> <code>50 ETB</code>\n\n"
                "✨ <i>አሁኑኑ በመሳተፍ የዕድሉ ባለቤት ይሁኑ!</i>"
            )
            pay_btn_text = "💳 ክፍያ ፈጽም"
        else:
            info_text = (
                "🎁 <b>Exclusive Prize List</b> 🎁\n"
                "━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{prize_list}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "🎫 <b>Ticket Price:</b> <code>50 ETB</code>\n\n"
                "✨ <i>Join now and be our next winner!</i>"
            )
            pay_btn_text = "💳 Pay Now"

        inline_kb = InlineKeyboardBuilder()
        inline_kb.row(types.InlineKeyboardButton(text=pay_btn_text, callback_data="show_payment"))
        
        await message.answer(info_text, reply_markup=inline_kb.as_markup(), parse_mode="HTML")

    except Exception as e:
        print(f"Prizes View Error: {e}")
        await message.answer("❌ <b>Error:</b> Unable to load prizes.")

# --- 2. የክፍያ መመሪያ (Callback) ---
@dp.callback_query(F.data == "show_payment")
async def process_payment_info(callback: types.CallbackQuery, state: FSMContext):
    # 1. ፈጣን ምላሽ (Loading እንዳይሽከረከር)
    await callback.answer()
    
    user_id = callback.from_user.id
    
    # 2. የተጠቃሚውን ቋንቋ ማረጋገጥ
    try:
        res = supabase.table("users").select("lang").eq("user_id", user_id).execute()
        lang = res.data[0].get('lang', 'en') if res.data else 'en'
    except:
        lang = 'en'

    # 3. ቦቱን "ደረሰኝ ጠባቂ" ስቴት ላይ ማድረግ
    await state.set_state(LotteryStates.waiting_for_receipt)

    PAYMENT_PHONE = "09XXXXXXXX" # ⚠️ እዚህ ጋር የራስህን ቁጥር ተካ

    if lang == "am":
        payment_text = (
            "🚀 <b>የመጨረሻው ደረጃ!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "ትኬትዎን ለመቁረጥ የሚከተሉትን ደረጃዎች ይከተሉ፦\n\n"
            f"1️⃣ በቴሌብር (Telebirr) <code>50 ETB</code> ይላኩ።\n"
            f"📍 ስልክ፦ <code>{PAYMENT_PHONE}</code> (ቁጥሩን ለመገልበጥ ይንኩት)\n\n"
            "2️⃣ ክፍያውን እንደፈጸሙ የደረሰኙን <b>ስክሪንሻት (Screenshot)</b> እዚህ ይላኩ።\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📢 <b>ማሳሰቢያ፦</b> አድሚኖቻችን ደረሰኙን እንዳረጋገጡ ትኬትዎን ወዲያውኑ ይልካሉ።\n\n"
            "<i>ዕድል ለደፋሮች ናት! መልካም ዕድል! 🍀</i>"
        )
    else:
        payment_text = (
            "🚀 <b>Final Step!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Follow these steps to get your ticket:\n\n"
            f"1️⃣ Send <code>50 ETB</code> via Telebirr.\n"
            f"📍 Phone: <code>{PAYMENT_PHONE}</code> (Tap to copy)\n\n"
            "2️⃣ Send the <b>Payment Screenshot</b> right here.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📢 <b>Note:</b> Your ticket will be issued once our admins verify the receipt.\n\n"
            "<i>Fortune favors the bold! Good Luck! 🍀</i>"
        )

    await callback.message.answer(payment_text, parse_mode="HTML")
        


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

        # 2. አሸናፊዎችን ከነ ተጠቃሚ መረጃቸው መሳብ
        # እዚህ ጋር Relationship ችግር ካለ 'Detailed Winners Error' ውስጥ ያሳየሃል
        res = supabase.table("winners").select(
            "ticket_number, round_no, prize_rank, user_id, users(username)"
        ).order("created_at", desc=True).limit(10).execute()
        
        winners_list = res.data

        if not winners_list:
            text = (
                "🏆 <b>አሸናፊዎች / Winners</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n\n"
                "እስካሁን ምንም አሸናፊ አልተመዘገበም።\n"
                "No winners recorded yet. 🍀"
            )
        else:
            header = "🏆 <b>የቅርብ ጊዜ አሸናፊዎች</b>\n" if lang == "am" else "🏆 <b>Recent Winners</b>\n"
            text = header + "━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for w in winners_list:
                user_info = w.get('users')
                username = f"@{user_info.get('username')}" if user_info and user_info.get('username') else "User"
                
                ticket = w.get('ticket_number', 'N/A')
                round_no = w.get('round_no', '1')
                rank = w.get('prize_rank', '1')
                
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

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        # ስህተቱ በሚፈጠርበት ጊዜ ለተጠቃሚውም ለአንተም ግልጽ እንዲሆን
        error_msg = (
            "⚠️ <b>የሲስተም ስህተት አጋጥሟል!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 <b>Error Detail:</b>\n<code>{html.escape(str(e))}</code>\n\n"
            "<i>እባክዎ ይህንን ስክሪንሻት ለአድሚኑ ይላኩ።</i>"
        )
        await message.answer(error_msg, parse_mode="HTML")
        print(f"DEBUG ERROR: {e}") # ለ Vercel Log እንዲመች


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

    GROUP_CHAT_ID = "-1003878868241" # የግሩፕህ ID
    ADMIN_USERNAME = "your_admin_username" # ያንተ ዩዘር ኔም (ያለ @)

    try:
        # 2. ዳታዎችን ከዳታቤዝ ማምጣት
        ticket_res = supabase.table("tickets").select("*").eq("status", "approved").execute()
        # የዙር ቁጥርን ለማወቅ (ከዚህ በፊት ከነበሩት + 1)
        round_res = supabase.table("winners").select("round_no").order("round_no", desc=True).limit(1).execute()
        current_round = (round_res.data[0]['round_no'] + 1) if round_res.data else 1
        
        # የሽልማት ዝርዝር
        prize_res = supabase.table("prizes").select("rank, amount").execute()
        
        all_tickets = ticket_res.data
        all_prizes = {p['rank']: p['amount'] for p in prize_res.data}

        if not all_tickets:
            await message.answer("⚠️ <b>ምንም የጸደቀ ትኬት የለም።</b>", parse_mode="HTML")
            return

        # 3. የተሳታፊዎች ብዛት ቼክ
        unique_users = list(set(t['user_id'] for t in all_tickets))
        if len(unique_users) < 3:
            await message.answer(f"⚠️ <b>ቢያንስ 3 የተለያየ ተሳታፊ ያስፈልጋል። አሁን ያሉት ተሳታፊዎች: {len(unique_users)}</b>", parse_mode="HTML")
            return

        # 4. የቆጠራ Animation (Countdown) በግሩፑ ላይ
        status_msg = await bot.send_message(GROUP_CHAT_ID, f"🔔 <b>የዙር {current_round} የዕጣ ዝግጅት ተጀምሯል!</b>", parse_mode="HTML")
        
        anims = [
            "🕒 <b>3...</b>", 
            "🕑 <b>2...</b>", 
            "🕐 <b>1...</b>", 
            "🎰 <b>እጣው እየተሽከረከረ ነው...</b>"
        ]
        
        for anim in anims:
            await asyncio.sleep(2)
            await status_msg.edit_text(f"🎲 <b>ዕድለኛውን እየፈለግን ነው...</b>\n\n{anim}", parse_mode="HTML")
        
        await bot.delete_message(GROUP_CHAT_ID, status_msg.message_id)

        # 5. 3 አሸናፊዎችን መምረጥ (ያለ መደጋገም)
        # ሎጅክ፡ አንድ ሰው ከአንድ በላይ ትኬት ቢኖረው ዕድሉ ይጨምራል ነገር ግን አንዴ ካሸነፈ ለሌላው Rank አይታጭም
        winner_uids = []
        eligible_candidates = [t['user_id'] for t in all_tickets] # Weighted list

        ranks_display = ["1ኛ 🥇", "2ኛ 🥈", "3ኛ 🥉"]
        db_ranks = ["1ኛ", "2ኛ", "3ኛ"] 

        for i in range(3):
            # አሸናፊ ያልሆኑትን ብቻ መለየት
            current_candidates = [uid for uid in eligible_candidates if uid not in winner_uids]
            if not current_candidates: break
            
            chosen_winner = random.choice(current_candidates)
            winner_uids.append(chosen_winner)

            rank_label = ranks_display[i]
            rank_key = db_ranks[i]
            prize_amount = all_prizes.get(rank_key, "ልዩ ሽልማት")

            # የተጠቃሚ መረጃ ማምጣት
            u_res = supabase.table("users").select("*").eq("user_id", chosen_winner).execute()
            user_data = u_res.data[0]
            u_name = html.escape(user_data.get('username') or user_data.get('full_name', 'ተጠቃሚ'))
            u_lang = user_data.get('lang', 'am')

            # የአሸናፊውን ትኬት መለየት (ከጸደቁት ውስጥ አንዱን)
            user_approved_tickets = [t['ticket_number'] for t in all_tickets if t['user_id'] == chosen_winner]
            t_num = random.choice(user_approved_tickets)

            # 6. ዳታቤዝ ማደስ (Record Winner)
            supabase.table("winners").insert({
                "user_id": chosen_winner, 
                "ticket_number": t_num, 
                "round_no": current_round,
                "prize_rank": (i + 1),
                "prize_name": f"{rank_key} - {prize_amount}"
            }).execute()
            
            # ትኬቱን Winner ተብሎ ምልክት ማድረግ
            supabase.table("tickets").update({"status": "winner"}).eq("ticket_number", t_num).execute()

            # 7. Buttons
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(text="📞 አድሚን አግኝ / Contact", url=f"https://t.me/{ADMIN_USERNAME}"))
            builder.row(types.InlineKeyboardButton(text="🎫 ትኬት ቁረጥ / Buy Ticket", callback_data="buy_ticket"))

            # 8. መልእክት ማዘጋጀት
            # ግሩፕ ላይ የሚለጠፍ (ባለ ሁለት ቋንቋ)
            group_txt = (
                f"🎊 <b>የእጣ አሸናፊ / DRAW WINNER</b> 🎊\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏅 <b>ደረጃ / Rank:</b> {rank_label}\n"
                f"👤 <b>አሸናፊ:</b> @{u_name}\n"
                f"🎫 <b>ትኬት / Ticket:</b> <code>{t_num}</code>\n"
                f"🎁 <b>ሽልማት / Prize:</b> {prize_amount}\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"✨ <i>እንኳን ደስ አላችሁ! / Congratulations!</i>"
            )

            # ለአሸናፊው Inbox የሚላክ
            if u_lang == 'am':
                inbox_txt = (f"🎁 <b>እንኳን ደስ አለዎት!</b>\n\n"
                             f"በዙር {current_round} የ <b>{rank_label}</b> አሸናፊ ሆነዋል!\n"
                             f"ሽልማት፦ {prize_amount}\n"
                             f"ትኬት፦ <code>{t_num}</code>\n\n"
                             f"ለመረከብ አድሚኑን ያነጋግሩ።")
            else:
                inbox_txt = (f"🎁 <b>Congratulations!</b>\n\n"
                             f"You won the <b>{rank_label}</b> prize in Round {current_round}!\n"
                             f"Prize: {prize_amount}\n"
                             f"Ticket: <code>{t_num}</code>\n\n"
                             f"Contact admin to claim.")

            # 9. መላክ
            try:
                await bot.send_message(chosen_winner, inbox_txt, reply_markup=builder.as_markup(), parse_mode="HTML")
            except:
                pass # Block ካደረገ ዝለለው
            
            await bot.send_message(GROUP_CHAT_ID, group_txt, reply_markup=builder.as_markup(), parse_mode="HTML")
            await asyncio.sleep(2) # ለአሸናፊዎች መሃል እረፍት

        # 10. የቀሩትን ትኬቶች Expired ማድረግ
        supabase.table("tickets").update({"status": "expired"}).eq("status", "approved").execute()
        
        await message.answer(f"✅ <b>ዙር {current_round} በስኬት ተጠናቋል። 3 አሸናፊዎች ተለይተዋል።</b>", parse_mode="HTML")

    except Exception as e:
        print(f"Critical Draw Error: {e}")
        await message.answer(f"❌ <b>ስህተት:</b> <code>{e}</code>", parse_mode="HTML")
            
        
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
                  
