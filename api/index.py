import os
import telebot
import time
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ያንተ GIF ID
MY_GIF_ID = "CgACAgQAAxkBAAICamnQ4Te5nXpICkuvCyQsEZk0y3O4AALWHAACQtCJUjnn_dB6DekvOwQ"

# --- 1. የቋንቋ ዳታቤዝ (Multi-language Support) ---
strings = {
    "en": {
        "welcome": "👋 **Welcome to our Platform!**\n\n📞 **Phone:** +251900000000\n💬 **Group:** [Join Our Community](https://t.me/your_group_link)\n\nSelect an option from the menu below to get started.",
        "buy": "➕ Buy New Ticket",
        "info": "👤 My Info",
        "win": "🎁 Winners",
        "ref": "👥 Referral",
        "help": "💡 Help & Support",
        "lang": "🌐 Language",
        "lang_msg": "📌 Please select your preferred language:",
        "changed": "✅ Language set to English!"
    },
    "am": {
        "welcome": "👋 **እንኳን በደህና መጡ!**\n\n📞 **ስልክ:** +251900000000\n💬 **ግሩፕ:** [ቤተሰባችንን ይቀላቀሉ](https://t.me/your_group_link)\n\nለመቀጠል ከታች ካሉት አማራጮች አንዱን ይምረጡ።",
        "buy": "➕ አዲስ ትኬት ቁረጥ",
        "info": "👤 የእኔ መረጃ",
        "win": "🎁 አሸናፊዎች",
        "ref": "👥 ጓደኛ ጋብዝ",
        "help": "💡 እገዛ እና ድጋፍ",
        "lang": "🌐 ቋንቋ (Language)",
        "lang_msg": "📌 እባክዎ ቋንቋ ይምረጡ፦",
        "changed": "✅ ቋንቋ ወደ አማርኛ ተቀይሯል!"
    },
    "or": {
        "welcome": "👋 **Baga Nagaan Dhuftan!**\n\n📞 **Bilbila:** +251900000000\n💬 **Garee:** [Hawaasa Keenya Tajaajilaa](https://t.me/your_group_link)\n\nItti fufuuf filannoowwan gadii keessaa tokko fayaadamaa.",
        "buy": "➕ Tikkee Haaraa Bitadhu",
        "info": "👤 Odeeffannoo Koo",
        "win": "🎁 Mo'attoota",
        "ref": "👥 Nama Affeeruuf",
        "help": "💡 Gargaarsa",
        "lang": "🌐 Afaan (Language)",
        "lang_msg": "📌 Maaloo afaan filadhu:",
        "changed": "✅ Afaan gara Oromootti jijjiirameera!"
    }
}

# --- 2. ቋሚ ሜኑ (Reply Keyboard) ---
def main_menu_keyboard(lang="en"):
    s = strings[lang]
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(telebot.types.KeyboardButton(s["buy"]))
    markup.add(telebot.types.KeyboardButton(s["info"]), telebot.types.KeyboardButton(s["win"]))
    markup.add(telebot.types.KeyboardButton(s["ref"]), telebot.types.KeyboardButton(s["help"]))
    markup.add(telebot.types.KeyboardButton(s["lang"]))
    return markup

# --- 3. ከቪዲዮው ስር የሚሆኑ በተኖች (Inline Keyboard) ---
def welcome_inline_buttons():
    markup = telebot.types.InlineKeyboardMarkup()
    btn_web = telebot.types.InlineKeyboardButton("🌐 Visit Website", url="https://yourwebsite.com")
    btn_con = telebot.types.InlineKeyboardButton("📩 Contact Admin", url="https://t.me/your_admin")
    markup.row(btn_web, btn_con)
    return markup

# --- 4. የቋንቋ መምረጫ በተኖች ---
def language_inline():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🇺🇸 English", callback_data="setlang_en"))
    markup.add(telebot.types.InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="setlang_am"))
    markup.add(telebot.types.InlineKeyboardButton("🇪🇹 Afaan Oromoo", callback_data="setlang_or"))
    return markup

# --- 5. የ /start ትዕዛዝ ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    # 'Uploading video' effect
    bot.send_chat_action(message.chat.id, 'upload_video')
    time.sleep(0.5)
    
    # ቪዲዮውን፣ ጽሁፉን እና ሊንኮቹን በአንድ ላይ ይልካል
    bot.send_animation(
        chat_id=message.chat.id,
        animation=MY_GIF_ID,
        caption=strings["en"]["welcome"],
        reply_markup=welcome_inline_buttons(), # Inline buttons under video
        parse_mode="Markdown"
    )
    
    # ዋናውን ሜኑ (Keyboard) ያሳያል
    bot.send_message(message.chat.id, "--- Menu Activated ---", reply_markup=main_menu_keyboard("en"))

# --- 6. የሜኑ በተኖች ተግባር ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    text = message.text
    user_id = message.chat.id
    
    # Typing effect
    bot.send_chat_action(user_id, 'typing')

    for lang, s in strings.items():
        if text == s["lang"]:
            bot.send_message(user_id, s["lang_msg"], reply_markup=language_inline())
            return
        
        if text == s["info"]:
            info_box = (
                f"📋 **User Dashboard**\n"
                f"━━━━━━━━━━━━━━\n"
                f"👤 Name: {message.from_user.first_name}\n"
                f"🆔 ID: `{user_id}`\n"
                f"🎟 Tickets: 0\n"
                f"━━━━━━━━━━━━━━"
            )
            bot.send_message(user_id, info_box, parse_mode="Markdown")
            return
        
        if text == s["buy"]:
            # ለዚህ ምንም መልስ አይሰጥም (ባዶ)
            return

# --- 7. የቋንቋ ምርጫ ሲነካ (Callback) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def callback_language(call):
    lang_code = call.data.split('_')[1]
    s = strings[lang_code]
    
    bot.answer_callback_query(call.id, s["changed"])
    
    # ሜኑውን ይቀይራል
    bot.send_message(
        call.message.chat.id, 
        s["changed"], 
        reply_markup=main_menu_keyboard(lang_code)
    )
    # የቋንቋ መምረጫ መልዕክቱን ያጠፋዋል
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
    return "Bot is LIVE and Optimized!"
    
