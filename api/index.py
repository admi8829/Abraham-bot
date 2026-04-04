import os
import telebot
from flask import Flask, request

# ከሌሎች ፋይሎች ጋር እናገናኛለን (እነዚህ ፋይሎች በ api/ ውስጥ መኖር አለባቸው)
from .database import check_user, add_user

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- 1. ዋናው የሜኑ አደረጃጀት (Professional Layout) ---
def main_menu_keyboard():
    # ከታች የሚቀመጡ ትልልቅ በተኖች (Reply Keyboard)
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    btn_buy = telebot.types.KeyboardButton("➕ አዲስ ትኬት ቁረጥ")
    btn_acc = telebot.types.KeyboardButton("💰 የእኔ ሂሳብ")
    btn_win = telebot.types.KeyboardButton("🎁 አሸናፊዎች")
    btn_ref = telebot.types.KeyboardButton("👥 ጓደኛ ጋብዝ (Referral)")
    btn_help = telebot.types.KeyboardButton("💡 እገዛ እና ድጋፍ")
    btn_lang = telebot.types.KeyboardButton("🌐 ቋንቋ (Language)")
    
    markup.add(btn_buy) # ትኬት መቁረጫው ለብቻው ከላይ ሰፊ እንዲሆን
    markup.add(btn_acc, btn_win)
    markup.add(btn_ref, btn_help)
    markup.add(btn_lang)
    
    return markup

# --- 2. ስልክ ቁጥር ማጋሪያ በተን (Registration) ---
def contact_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    button = telebot.types.KeyboardButton("📲 ስልክ ቁጥሬን አጋራ (Share Contact)", request_contact=True)
    markup.add(button)
    return markup

# --- 3. የ /start ትዕዛዝ (ከ GIF ጋር) ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    # መመዝገቡን ቼክ አድርገን ስሙን እንቀበላለን
    user_name = message.from_user.first_name
    
    # እዚህ ጋር ያገኘኸውን GIF File ID አስገባ (ካልያዝከው ለጊዜው ምስል መጠቀም ትችላለህ)
    gif_id = "YOUR_GIF_FILE_ID_HERE" 
    
    welcome_text = (
        f"👋 **ሰላም {user_name}!**\n\n"
        "ወደ **Smart-X Academy** የዕጣ ቦት በደህና መጣህ።\n"
        "ይህ ቦት ተማሪዎች ትኬት በመቁረጥ ታላላቅ ሽልማቶችን የሚያገኙበት መድረክ ነው።\n\n"
        "ለመጀመር ከታች ያሉትን በተኖች ይጠቀሙ፦"
    )

    try:
        # GIF ፋይሉን ከነ ጽሁፉ እና ሜኑው ጋር ይልካል
        bot.send_animation(
            chat_id=message.chat.id,
            animation=gif_id,
            caption=welcome_text,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
    except:
        # GIF ካልተገኘ በጽሁፍ ብቻ ይልካል
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# --- 4. የትልልቅ በተኖች ተግባር (Message Handler) ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    user = check_user(user_id)
    text = message.text

    # ካልተመዘገበ ወደ ምዝገባ የሚወስዱ አገልግሎቶች
    if text in ["➕ አዲስ ትኬት ቁረጥ", "💰 የእኔ ሂሳብ", "👥 ጓደኛ ጋብዝ (Referral)"]:
        if not user:
            msg = bot.send_message(
                message.chat.id, 
                "⚠️ ይህንን አገልግሎት ለመጠቀም መጀመሪያ ስልክ ቁጥርዎን ማጋራት አለብዎት።\nእባክዎ ከታች ያለውን **'Share Contact'** በተን ይጫኑ፦", 
                reply_markup=contact_keyboard()
            )
            bot.register_next_step_handler(msg, process_registration, message.from_user.first_name)
            return

    # አገልግሎቶቹ ከተመዘገበ በኋላ የሚሰሩት
    if text == "➕ አዲስ ትኬት ቁረጥ":
        bot.send_message(message.chat.id, "💳 የ 10 ብር ክፍያ በ Chapa ለመፈጸም /pay ይበሉ።")
    
    elif text == "💰 የእኔ ሂሳብ":
        bot.send_message(message.chat.id, f"👤 **ስም፦** {user['full_name']}\n📞 **ስልክ፦** {user['phone']}\n🎟 **ትኬቶች፦** 0")
        
    elif text == "👥 ጓደኛ ጋብዝ (Referral)":
        bot.send_message(message.chat.id, f"🔗 ያንተ መጋበዣ ሊንክ፦\nhttps://t.me/{(bot.get_me()).username}?start={user_id}")
        
    elif text == "💡 እገዛ እና ድጋፍ":
        bot.send_message(message.chat.id, "ማንኛውም ጥያቄ ካለዎት አድሚኑን ያግኙ፦ @SmartX_Support")

# --- 5. የምዝገባ ሂደት ---
def process_registration(message, first_name):
    if message.contact is not None:
        phone = message.contact.phone_number
        add_user(message.from_user.id, first_name, phone, "N/A")
        
        bot.send_message(
            message.chat.id, 
            "✅ ምዝገባህ ተሳክቷል! አሁን አገልግሎቱን ደግመህ መጠቀም ትችላለህ።", 
            reply_markup=main_menu_keyboard()
        )
    else:
        bot.send_message(message.chat.id, "እባክህ ስልክህን ለማጋራት በተኑን ተጠቀም።", reply_markup=contact_keyboard())

# --- 6. Vercel Webhook ---
@app.route('/', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

@app.route('/')
def home(): return "Smart-X Raffle Bot is LIVE!"
    
