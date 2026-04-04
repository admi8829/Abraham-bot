import os
import telebot
from flask import Flask, request

# ከሌሎቹ ፋይሎች ተግባራትን (Functions) እናመጣለን
from .database import check_user
from .register import start_registration

# Tokens ከ Vercel Environment Variables ይነበባሉ
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)

app = Flask(__name__)

# --- የቦቱ ትዕዛዞች (Commands) ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    user = check_user(user_id)
    
    if user:
        # ተማሪው ተመዝግቦ ከሆነ ዋናውን ሜኑ እናሳየዋለን
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        btn1 = telebot.types.InlineKeyboardButton("🎫 ትኬት ቁረጥ", callback_data="buy_ticket")
        btn2 = telebot.types.InlineKeyboardButton("👥 ጓደኛ ጋብዝ", callback_data="referral")
        btn3 = telebot.types.InlineKeyboardButton("📊 የእኔ መረጃ", callback_data="my_stats")
        btn4 = telebot.types.InlineKeyboardButton("📞 እርዳታ", callback_data="help")
        markup.add(btn1, btn2, btn3, btn4)
        
        bot.send_message(
            message.chat.id, 
            f"እንኳን ደህና መጣህ {user['full_name']}! 👋\nየ Smart-X የዕጣ ቦት ዝግጁ ነው። ምን ማድረግ ትፈልጋለህ?",
            reply_markup=markup
        )
    else:
        # ተማሪው ካልተመዘገበ ወደ register.py ይላካል
        start_registration(bot, message)

# --- የባተን (Button) ስራዎች ---
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user_id = call.from_user.id
    
    if call.data == "buy_ticket":
        # ወደ ፊት በ chapa.py የምንሰራው
        bot.answer_callback_query(call.id, "የክፍያ ሲስተሙ በቅርቡ ይከፈታል!")
        bot.send_message(call.message.chat.id, "ትኬት ለመቁረጥ 10 ብር በ Chapa መክፈል አለብህ። (ኮዱ በሂደት ላይ ነው)")
        
    elif call.data == "my_stats":
        user = check_user(user_id)
        text = f"👤 ስም፦ {user['full_name']}\n📱 ስልክ፦ {user['phone']}\n🎓 ክፍል፦ {user['grade']}"
        bot.send_message(call.message.chat.id, text)

# --- የ Vercel Webhook አሰራር ---

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'ok', 200
    else:
        return 'error', 400

@app.route('/')
def home():
    return "<h1>Smart-X Raffle Bot is Running!</h1>"
