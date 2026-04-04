import os
import telebot
from flask import Flask, request

# ከሌሎቹ ፋይሎች ተግባራትን እናመጣለን
from .database import check_user
from .register import start_registration

# Tokens ከ Vercel Environment Variables (Secrets)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)

app = Flask(__name__)

# --- 1. ዋናው ሜኑ (Main Menu) ---
def show_main_menu(bot, message, name):
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    
    # የሚያምሩ በተኖች ከነ ኢሞጂያቸው
    btn1 = telebot.types.InlineKeyboardButton("🎫 ትኬት ቁረጥ (10 ETB)", callback_data="buy")
    btn2 = telebot.types.InlineKeyboardButton("👥 ጓደኛ ጋብዝ", callback_data="referral")
    btn3 = telebot.types.InlineKeyboardButton("📊 የእኔ መረጃ", callback_data="profile")
    btn4 = telebot.types.InlineKeyboardButton("🏆 አሸናፊዎች", callback_data="winners")
    btn5 = telebot.types.InlineKeyboardButton("📱 YouTube", url="https://youtube.com/@SmartQA_ET")
    btn6 = telebot.types.InlineKeyboardButton("🆘 እርዳታ", callback_data="help")
    
    markup.add(btn1) # ትኬት መቁረጫው ጎልቶ እንዲታይ ለብቻው
    markup.add(btn2, btn3, btn4, btn6)
    markup.add(btn5)

    welcome_text = (
        f"ሰላም {name}! 👋\n\n"
        "እንኳን ወደ **Smart-X Academy** የዕጣ ቦት በደህና መጣህ።\n"
        "እዚህ ትኬት በመቁረጥ የተለያዩ ሽልማቶችን ማሸነፍ ትችላለህ።\n\n"
        "ለመጀመር የሚፈልጉትን አማራጭ ይምረጡ፦"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# --- 2. የ Start ትዕዛዝ ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    user = check_user(user_id)
    
    if user:
        # ተማሪው ቀድሞ ተመዝግቧል
        show_main_menu(bot, message, user['full_name'])
    else:
        # ተማሪው ካልተመዘገበ ወደ register.py ይላካል
        start_registration(bot, message)

# --- 3. የባተን ክሊክ ማስተናገጃ (Callback Handler) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    if call.data == "buy":
        bot.answer_callback_query(call.id, "ወደ ክፍያ እየወሰድኩህ ነው...")
        bot.send_message(call.message.chat.id, "🔗 የ Chapa ክፍያ ሊንክህን ለማመንጨት /pay የሚለውን ይጫኑ ወይም ትንሽ ይጠብቁ።")
        
    elif call.data == "profile":
        user = check_user(user_id)
        profile_text = (
            "👤 **የእኔ መረጃ**\n\n"
            f"🔹 ስም፦ {user['full_name']}\n"
            f"🔹 ስልክ፦ {user['phone']}\n"
            f"🔹 ክፍል፦ {user['grade']}\n"
            "------------------\n"
            "Smart-X Academy"
        )
        bot.send_message(call.message.chat.id, profile_text, parse_mode="Markdown")
        
    elif call.data == "help":
        bot.send_message(call.message.chat.id, "ማንኛውም ጥያቄ ካለዎት በአድራሻችን ያግኙን፦ @SmartX_Support")

# --- 4. Vercel Webhook Configuration ---
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'ok', 200
    return 'error', 400

@app.route('/')
def home():
    return "<h1>Smart-X Raffle Bot is Online!</h1>"
    
