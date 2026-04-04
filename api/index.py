import os
import telebot
from flask import Flask, request

# የቦቱን Token ከ Vercel Environment Variables ያነባል
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- 1. ዋናው የሜኑ አደረጃጀት (Professional Layout) ---
def main_menu_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # ዋና ዋና በተኖች
    btn_buy = telebot.types.KeyboardButton("➕ አዲስ ትኬት ቁረጥ")
    btn_acc = telebot.types.KeyboardButton("💰 የእኔ ሂሳብ")
    btn_win = telebot.types.KeyboardButton("🎁 አሸናፊዎች")
    btn_ref = telebot.types.KeyboardButton("👥 ጓደኛ ጋብዝ (Referral)")
    btn_help = telebot.types.KeyboardButton("💡 እገዛ እና ድጋፍ")
    btn_lang = telebot.types.KeyboardButton("🌐 ቋንቋ (Language)")
    
    # አቀማመጥ (Layout)
    markup.add(btn_buy) # ትኬት መቁረጫው ለብቻው ሰፊ እንዲሆን
    markup.add(btn_acc, btn_win)
    markup.add(btn_ref, btn_help)
    markup.add(btn_lang)
    
    return markup

# --- 2. የ /start ትዕዛዝ (ከ GIF ጋር) ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_name = message.from_user.first_name
    
    # አንተ የሰጠኸኝ የ GIF ID እዚህ ገብቷል
    gif_id = "CgACAgQAAxkBAAICamnQ4Te5nXpICkuvCyQsEZk0y3O4AALWHAACQtCJUjnn_dB6DekvOwQ" 
    
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
    except Exception as e:
        # ችግር ካለ በጽሁፍ ብቻ ይልካል
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# --- 3. የባተን ክሊኮችን ማስተናገጃ ---
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    if message.text == "➕ አዲስ ትኬት ቁረጥ":
        bot.send_message(message.chat.id, "💳 ትኬት ለመቁረጥ የ 10 ብር ክፍያ በ Chapa መፈጸም አለብህ።\nለመክፈል /pay የሚለውን ይጫኑ።")
    
    elif message.text == "💰 የእኔ ሂሳብ":
        bot.send_message(message.chat.id, "📊 ያንተ የትኬት ብዛት፦ 0\n💰 የሪፈራል ኮሚሽን፦ 0.00 ETB")
        
    elif message.text == "💡 እገዛ እና ድጋፍ":
        bot.send_message(message.chat.id, "ማንኛውም ጥያቄ ካለዎት አድሚኑን ያግኙ፦ @SmartX_Support")
    
    else:
        bot.send_message(message.chat.id, "እባክህ ከታች ካሉት በተኖች አንዱን ምረጥ።", reply_markup=main_menu_keyboard())

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
    return "Smart-X Bot is Running with GIF!"
    
