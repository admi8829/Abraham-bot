import os
import telebot
from flask import Flask, request

# ከሌሎቹ ፋይሎች ጋር እናገናኛለን
from .database import check_user, add_user

# Tokens ከ Vercel Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)

app = Flask(__name__)

# --- 1. ዋናው የሜኑ ገጽ (Main Menu Function) ---
def get_main_keyboard():
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    
    # ዋና ዋና በተኖች
    btn_buy = telebot.types.InlineKeyboardButton("🎫 ትኬት ግዛ (10 ETB)", callback_data="buy_ticket")
    btn_ref = telebot.types.InlineKeyboardButton("👥 Referral Link", callback_data="get_referral")
    btn_winners = telebot.types.InlineKeyboardButton("🏆 አሸናፊዎች", callback_data="winners_list")
    btn_info = telebot.types.InlineKeyboardButton("ℹ️ መረጃ (Info)", callback_data="bot_info")
    btn_help = telebot.types.InlineKeyboardButton("🆘 Help", callback_data="help_center")
    btn_contact = telebot.types.InlineKeyboardButton("📞 Contact Us", callback_data="contact_admin")
    
    # ሶሻል ሚዲያ እና ዌብሳይት
    btn_web = telebot.types.InlineKeyboardButton("🌐 Website", url="https://smartx-academy.vercel.app")
    btn_yt = telebot.types.InlineKeyboardButton("🎬 YouTube Channel", url="https://youtube.com/@SmartQA_ET")
    
    # አደረጃጀት
    markup.add(btn_buy) # ጎልቶ እንዲወጣ
    markup.add(btn_ref, btn_winners)
    markup.add(btn_info, btn_help)
    markup.add(btn_contact)
    markup.add(btn_web, btn_yt)
    
    return markup

# --- 2. የስልክ ቁጥር ማጋሪያ በተን (Contact Keyboard) ---
def get_contact_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    button = telebot.types.KeyboardButton("📲 ስልክ ቁጥሬን አጋራ (Share Contact)", request_contact=True)
    markup.add(button)
    return markup

# --- 3. የ /start ትዕዛዝ ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    user = check_user(user_id)
    
    if user:
        # ተማሪው ቀድሞ ተመዝግቧል - ዋናውን ገጽ እናሳያለን
        welcome_msg = (
            f"ሰላም {user['full_name']}! 👋\n\n"
            "ወደ **Smart-X Academy** የዕጣ ቦት እንኳን በደህና መጣህ። "
            "ከታች ያሉትን አማራጮች በመጠቀም ትኬት መቁረጥ ወይም መረጃ ማግኘት ትችላለህ።"
        )
        bot.send_message(message.chat.id, welcome_msg, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    else:
        # ተማሪው ካልተመዘገበ መጀመሪያ ስም ይጠየቃል
        msg = bot.send_message(message.chat.id, "እንኳን ደህና መጣህ! ለዕጣው ለመሳተፍ መጀመሪያ መመዝገብ አለብህ።\n\nእባክህ **ሙሉ ስምህን** ጻፍልኝ፦")
        bot.register_next_step_handler(msg, process_registration_name)

# --- 4. የምዝገባ ሂደት (Name -> Contact) ---
def process_registration_name(message):
    name = message.text
    user_id = message.from_user.id
    
    msg = bot.send_message(
        message.chat.id, 
        f"በጣም ጥሩ {name}! አሁን ደግሞ ከታች ያለውን **'Share Contact'** በተን በመጫን ስልክ ቁጥርህን አጋራኝ፦", 
        reply_markup=get_contact_keyboard()
    )
    bot.register_next_step_handler(msg, process_registration_contact, name)

def process_registration_contact(message, name):
    user_id = message.from_user.id
    
    if message.contact is not None:
        phone = message.contact.phone_number
        # ወደ ዳታቤዝ መላክ (grade ለጊዜው 'N/A' ተደርጓል)
        add_user(user_id, name, phone, "N/A")
        
        bot.send_message(
            message.chat.id, 
            "🎉 ምዝገባህ ተሳክቷል! አሁን ሁሉንም አገልግሎቶች መጠቀም ትችላለህ።", 
            reply_markup=telebot.types.ReplyKeyboardRemove() # የ share contact በተኑን ለማጥፋት
        )
        # ዋናውን ሜኑ ያሳየዋል
        bot.send_message(message.chat.id, "ዋናው ገጽ፦", reply_markup=get_main_keyboard())
    else:
        # በተኑን ካልተጫኑት በስተቀር ስልክ ቁጥር አንቀበልም
        msg = bot.send_message(message.chat.id, "እባክህ ስልክህን ለማጋራት ከታች ያለውን በተን ተጠቀም፦", reply_markup=get_contact_keyboard())
        bot.register_next_step_handler(msg, process_registration_contact, name)

# --- 5. የባተን ክሊክ ማስተናገጃ (Callbacks) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id
    
    if call.data == "buy_ticket":
        bot.send_message(call.message.chat.id, "💳 የ 10 ብር ክፍያ በ Chapa ለመፈጸም /pay ይበሉ። (የክፍያ ሊንክ በቅርቡ ይከፈታል)")
        
    elif call.data == "get_referral":
        bot.send_message(call.message.chat.id, f"🔗 ያንተ መጋበዣ ሊንክ፦\nhttps://t.me/{(bot.get_me()).username}?start={user_id}")
        
    elif call.data == "bot_info":
        info_text = "📖 **ስለ Smart-X Academy**\n\nይህ ቦት ተማሪዎች የትምህርት መሳሪያዎችን እና የተለያዩ ሽልማቶችን የሚያሸንፉበት መድረክ ነው።"
        bot.send_message(call.message.chat.id, info_text, parse_mode="Markdown")
        
    elif call.data == "contact_admin":
        bot.send_message(call.message.chat.id, "አድሚን ለማግኘት፦ @SmartX_Support")

    bot.answer_callback_query(call.id)

# --- 6. Vercel Webhook ---
@app.route('/', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

@app.route('/')
def home(): return "<h1>Smart-X Raffle Engine is LIVE!</h1>"
    
