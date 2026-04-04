import os
import telebot
import time
from flask import Flask, request

# የቦቱን Token ከ Vercel Environment Variables ያነባል
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ያንተ GIF ID
MY_GIF_ID = "CgACAgQAAxkBAAICamnQ4Te5nXpICkuvCyQsEZk0y3O4AALWHAACQtCJUjnn_dB6DekvOwQ"

# --- 1. ዋናው የሜኑ አደረጃጀት ---
def main_menu_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    btn_buy = telebot.types.KeyboardButton("➕ አዲስ ትኬት ቁረጥ")
    btn_acc = telebot.types.KeyboardButton("👤 My Info") # የእኔ ሂሳብ ወደ My Info ተቀይሯል
    btn_win = telebot.types.KeyboardButton("🎁 አሸናፊዎች")
    btn_ref = telebot.types.KeyboardButton("👥 ጓደኛ ጋብዝ (Referral)")
    btn_help = telebot.types.KeyboardButton("💡 እገዛ እና ድጋፍ")
    btn_lang = telebot.types.KeyboardButton("🌐 ቋንቋ (Language)")
    btn_reg = telebot.types.KeyboardButton("📝 Register", request_contact=True) # ስልክ ለመቀበል
    
    markup.add(btn_buy) 
    markup.add(btn_acc, btn_win)
    markup.add(btn_ref, btn_help)
    markup.add(btn_lang, btn_reg)
    
    return markup

# --- 2. የቋንቋ ምርጫ ሜኑ (Inline) ---
def language_keyboard():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🇪🇹 Amharic", callback_data="lang_am"))
    markup.add(telebot.types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"))
    markup.add(telebot.types.InlineKeyboardButton("🇪🇹 Afaan Oromoo", callback_data="lang_or"))
    return markup

# --- 3. የ /start ትዕዛዝ ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    # 'Typing' effect ለማሳየት
    bot.send_chat_action(message.chat.id, 'upload_video')
    time.sleep(1) # ለጥቂት ሰከንድ እንዲቆይ
    
    welcome_text = (
        f"👋 **ሰላም {message.from_user.first_name}!**\n\n"
        "ወደ **Smart-X Academy** እንኳን በደህና መጣህ።\n"
        "ለመቀጠል ከታች ያሉትን በተኖች ተጠቀም።"
    )

    bot.send_animation(
        chat_id=message.chat.id,
        animation=MY_GIF_ID,
        caption=welcome_text,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

# --- 4. የባተን ክሊኮችን ማስተናገጃ ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    # ለእያንዳንዱ መልስ 'Typing' effect እንዲኖር
    bot.send_chat_action(message.chat.id, 'typing')
    
    if message.text == "🌐 ቋንቋ (Language)":
        bot.send_message(message.chat.id, "እባክዎ ቋንቋ ይምረጡ / Please select a language:", reply_markup=language_keyboard())
    
    elif message.text == "👤 My Info":
        info = (
            f"👤 **የእርስዎ መረጃ**\n"
            f"ስም፦ {message.from_user.first_name}\n"
            f"ID፦ `{message.from_user.id}`\n"
            f"ትኬቶች፦ 0"
        )
        bot.send_message(message.chat.id, info, parse_mode="Markdown")

    elif message.text == "➕ አዲስ ትኬት ቁረጥ":
        bot.send_message(message.chat.id, "💳 ትኬት ለመቁረጥ /pay ብለው ይላኩ።")

    elif message.text == "💡 እገዛ እና ድጋፍ":
        bot.send_message(message.chat.id, "ማንኛውም ጥያቄ ካለዎት አድሚኑን ያግኙ፦ @SmartX_Support")

# --- 5. ስልክ ቁጥር ሲላክ (Register) ---
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    bot.send_chat_action(message.chat.id, 'typing')
    if message.contact is not None:
        bot.send_message(
            message.chat.id, 
            f"✅ ተመዝግቧል!\nስም፦ {message.from_user.first_name}\nስልክ፦ {message.contact.phone_number}",
            reply_markup=main_menu_keyboard()
        )

# --- 6. የቋንቋ ምርጫ ሲነካ (Inline Callback) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def callback_language(call):
    lang_name = ""
    if call.data == "lang_am": lang_name = "Amharic"
    elif call.data == "lang_en": lang_name = "English"
    elif call.data == "lang_or": lang_name = "Afaan Oromoo"
    
    bot.answer_callback_query(call.id, f"ቋንቋ ወደ {lang_name} ተቀይሯል")
    bot.edit_message_text(f"✅ ቋንቋ ወደ **{lang_name}** ተቀይሯል።", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# --- 7. Vercel Webhook ---
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
    return "Smart-X Bot is LIVE!"
    
