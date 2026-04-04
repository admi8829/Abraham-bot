import os
import telebot
import time
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

MY_GIF_ID = "CgACAgQAAxkBAAICamnQ4Te5nXpICkuvCyQsEZk0y3O4AALWHAACQtCJUjnn_dB6DekvOwQ"

# --- 1. የቋንቋ ትርጉሞች (Dictionary) ---
strings = {
    "en": {
        "welcome": "Welcome! Please use the buttons below to navigate.",
        "buy": "➕ Buy New Ticket",
        "info": "👤 My Info",
        "win": "🎁 Winners",
        "ref": "👥 Referral",
        "help": "💡 Help & Support",
        "lang": "🌐 Language",
        "lang_msg": "Please select your preferred language:",
        "changed": "Language changed to English!"
    },
    "am": {
        "welcome": "እንኳን ደህና መጡ! ለመቀጠል ከታች ያሉትን በተኖች ይጠቀሙ።",
        "buy": "➕ አዲስ ትኬት ቁረጥ",
        "info": "👤 የእኔ መረጃ",
        "win": "🎁 አሸናፊዎች",
        "ref": "👥 ጓደኛ ጋብዝ",
        "help": "💡 እገዛ እና ድጋፍ",
        "lang": "🌐 ቋንቋ (Language)",
        "lang_msg": "እባክዎ ቋንቋ ይምረጡ፦",
        "changed": "ቋንቋ ወደ አማርኛ ተቀይሯል!"
    },
    "or": {
        "welcome": "Baga nagaan dhuftan! Itti fufuuf battoniiwwan gadii fayyadamaa.",
        "buy": "➕ Tikkee Haaraa Bitadhu",
        "info": "👤 Odeeffannoo Koo",
        "win": "🎁 Mo'attoota",
        "ref": "👥 Nama Affeeruuf",
        "help": "💡 Gargaarsa",
        "lang": "🌐 Afaan (Language)",
        "lang_msg": "Maaloo afaan filadhu:",
        "changed": "Afaan gara Oromootti jijjiirameera!"
    }
}

# --- 2. ዳይናሚክ የሜኑ አደረጃጀት ---
def main_menu_keyboard(lang="en"):
    s = strings[lang]
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    markup.add(telebot.types.KeyboardButton(s["buy"]))
    markup.add(telebot.types.KeyboardButton(s["info"]), telebot.types.KeyboardButton(s["win"]))
    markup.add(telebot.types.KeyboardButton(s["ref"]), telebot.types.KeyboardButton(s["help"]))
    markup.add(telebot.types.KeyboardButton(s["lang"]))
    
    return markup

# --- 3. የሊንክ በተኖች (Inline) ---
def link_buttons():
    markup = telebot.types.InlineKeyboardMarkup()
    btn_web = telebot.types.InlineKeyboardButton("🌐 Website", url="https://example.com") # ሊንኩን እዚህ ቀይረው
    btn_con = telebot.types.InlineKeyboardButton("📞 Contact Us", url="https://t.me/your_admin_username") # ዩዘርኔም ቀይረው
    markup.row(btn_web, btn_con)
    return markup

# --- 4. የቋንቋ ምርጫ (Inline) ---
def language_inline():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🇺🇸 English", callback_data="setlang_en"))
    markup.add(telebot.types.InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="setlang_am"))
    markup.add(telebot.types.InlineKeyboardButton("🇪🇹 Afaan Oromoo", callback_data="setlang_or"))
    return markup

# --- 5. የ /start ትዕዛዝ ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_chat_action(message.chat.id, 'upload_video')
    time.sleep(1)
    
    # መጀመሪያ በ English ይጀምራል
    bot.send_animation(
        chat_id=message.chat.id,
        animation=MY_GIF_ID,
        caption=strings["en"]["welcome"],
        reply_markup=main_menu_keyboard("en"),
        parse_mode="Markdown"
    )
    # የሊንክ በተኖቹን ለብቻው ይልካል
    bot.send_message(message.chat.id, "Quick Links:", reply_markup=link_buttons())

# --- 6. የባተን ክሊኮችን ማስተናገጃ ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    text = message.text
    user_id = message.chat.id
    
    # የትኛው ቋንቋ እንደተመረጠ ለማወቅ (ለሙከራ ያህል በጽሁፍ እናወዳድራለን)
    current_lang = "en"
    for lang, s in strings.items():
        if text == s["lang"]:
            bot.send_chat_action(user_id, 'typing')
            bot.send_message(user_id, s["lang_msg"], reply_markup=language_inline())
            return
        if text == s["info"]:
            bot.send_chat_action(user_id, 'typing')
            info_text = f"👤 **User Info**\nName: {message.from_user.first_name}\nID: `{user_id}`"
            bot.send_message(user_id, info_text, parse_mode="Markdown")
            return
        if text == s["buy"]:
            # ለዚህ መልስ አይሰጥም (ዝም ይላል)
            return

# --- 7. የቋንቋ ምርጫ ሲነካ (Callback) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def callback_language(call):
    lang_code = call.data.split('_')[1]
    s = strings[lang_code]
    
    bot.answer_callback_query(call.id, s["changed"])
    
    # ሜኑውን ወደ ተመረጠው ቋንቋ ይቀይራል
    bot.send_message(
        call.message.chat.id, 
        s["changed"], 
        reply_markup=main_menu_keyboard(lang_code)
    )
    # የድሮውን ሜሴጅ ያጠፋዋል
    bot.delete_message(call.message.chat.id, call.message.message_id)

# --- 8. Vercel Webhook ---
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
    return "Bot is LIVE!"
