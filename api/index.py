import os
import telebot
import time
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ያንተ GIF ID
MY_GIF_ID = "CgACAgQAAxkBAAICamnQ4Te5nXpICkuvCyQsEZk0y3O4AALWHAACQtCJUjnn_dB6DekvOwQ"

# ተጠቃሚዎች የመረጡትን ቋንቋ ለጊዜው ለማስታወስ (Memory Storage)
# ማሳሰቢያ፡ ሰርቨሩ Restart ካደረገ ወደ English ይመለሳል። ለቋሚነት Database ያስፈልጋል።
user_languages = {}

strings = {
    "en": {
        "welcome": "👋 **Welcome, {name}!**\n\n━━━━━━━━━━━━━━━━━━━━\n🚀 **Our Premium Services**\n━━━━━━━━━━━━━━━━━━━━\n\n📞 **Support:** +251963959697\n📢 **Telegram:** [Social Gebeya](https://t.me/Social_Gebeya)\n\n📍 *Select a service from the menu below to start your journey.*",
        "buy": "➕ Buy Ticket", "info": "👤 My Info", "win": "🎁 Winners",
        "ref": "👥 Referral", "help": "💡 Help", "lang": "🌐 Language",
        "lang_msg": "📌 **Please select your language:**",
        "changed": "✅ Language updated to English!"
    },
    "am": {
        "welcome": "👋 **እንኳን በደህና መጡ፣ {name}!**\n\n━━━━━━━━━━━━━━━━━━━━\n🚀 **የእኛ ምርጥ አገልግሎቶች**\n━━━━━━━━━━━━━━━━━━━━\n\n📞 **ስልክ:** +251963959697\n📢 **ቴሌግራም:** [ሶሻል ገበያ](https://t.me/Social_Gebeya)\n\n📍 *ለመጀመር ከታች ካሉት አማራጮች አንዱን ይምረጡ።*",
        "buy": "➕ አዲስ ትኬት ቁረጥ", "info": "👤 የእኔ መረጃ", "win": "🎁 አሸናፊዎች",
        "ref": "👥 ጓደኛ ጋብዝ", "help": "💡 እገዛ", "lang": "🌐 ቋንቋ",
        "lang_msg": "📌 **እባክዎ ቋንቋ ይምረጡ፦**",
        "changed": "✅ ቋንቋ ወደ አማርኛ ተቀይሯል!"
    },
    "or": {
        "welcome": "👋 **Baga Nagaan Dhuftan, {name}!**\n\n━━━━━━━━━━━━━━━━━━━━\n🚀 **Tajaajila Keenya**\n━━━━━━━━━━━━━━━━━━━━\n\n📞 **Bilbila:** +251963959697\n📢 **Telegram:** [Social Gebeya](https://t.me/Social_Gebeya)\n\n📍 *Tajaajila eegaluf filannoowwan gadii fayyadamaa.*",
        "buy": "➕ Tikkee Bitadhu", "info": "👤 Odeeffannoo Koo", "win": "🎁 Mo'attoota",
        "ref": "👥 Nama Affeeruuf", "help": "💡 Gargaarsa", "lang": "🌐 Afaan",
        "lang_msg": "📌 **Maaloo Afaan filadhu:**",
        "changed": "✅ Afaan gara Oromootti jijjiirameera!"
    }
}

# --- 1. Inline Buttons (Social Links) ---
def welcome_inline_buttons():
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn_web = telebot.types.InlineKeyboardButton("🌐 Website", url="https://yourwebsite.com")
    btn_con = telebot.types.InlineKeyboardButton("📩 Contact Us", url="https://t.me/your_admin")
    btn_tik = telebot.types.InlineKeyboardButton("🎬 TikTok", url="https://tiktok.com/@your_id")
    markup.add(btn_web, btn_con)
    markup.add(btn_tik)
    return markup

# --- 2. Main Menu (Reply Keyboard) ---
def main_menu_keyboard(lang="en"):
    s = strings[lang]
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(telebot.types.KeyboardButton(s["buy"]))
    markup.add(telebot.types.KeyboardButton(s["info"]), telebot.types.KeyboardButton(s["win"]))
    markup.add(telebot.types.KeyboardButton(s["ref"]), telebot.types.KeyboardButton(s["help"]))
    markup.add(telebot.types.KeyboardButton(s["lang"]))
    return markup

# --- 3. Language Inline ---
def language_inline():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🇺🇸 English", callback_data="setlang_en"),
               telebot.types.InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="setlang_am"),
               telebot.types.InlineKeyboardButton("🇪🇹 Afaan Oromoo", callback_data="setlang_or"))
    return markup

# --- 4. Start Handler ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    # ተጠቃሚው በፊት የመረጠው ቋንቋ ካለ እሱን ይጠቀማል፣ ከሌለ English
    lang = user_languages.get(user_id, "en")
    
    bot.send_chat_action(user_id, 'upload_video')
    
    bot.send_animation(
        chat_id=user_id,
        animation=MY_GIF_ID,
        caption=strings[lang]["welcome"].format(name=message.from_user.first_name),
        reply_markup=welcome_inline_buttons(),
        parse_mode="Markdown"
    )
    # ያለምንም ተጨማሪ ጽሁፍ ሜኑውን ብቻ ያያይዛል
    bot.send_message(user_id, "⚙️", reply_markup=main_menu_keyboard(lang))
    # ከላይ ያለውን የ "⚙️" ምልክት ቶሎ ለማጥፋት (አማራጭ)
    # bot.delete_message(user_id, msg.message_id)

# --- 5. Message Handler ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.chat.id
    text = message.text
    lang = user_languages.get(user_id, "en")
    s = strings[lang]

    bot.send_chat_action(user_id, 'typing')

    if text == s["lang"]:
        bot.send_message(user_id, s["lang_msg"], reply_markup=language_inline(), parse_mode="Markdown")
    
    elif text == s["info"]:
        dashboard = (
            f"📊 **DASHBOARD**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** {message.from_user.first_name}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"🎟 **My Tickets:** 0\n"
            f"👥 **Referrals:** 0\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(user_id, dashboard, parse_mode="Markdown")
        
    elif text == s["buy"]:
        pass # አዲስ ትኬት ሲነካ ዝም ይላል

# --- 6. Callback for Language ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def callback_language(call):
    user_id = call.message.chat.id
    lang_code = call.data.split('_')[1]
    
    # ቋንቋውን በ Memory ውስጥ ያስቀምጠዋል
    user_languages[user_id] = lang_code
    s = strings[lang_code]
    
    bot.answer_callback_query(call.id, s["changed"])
    
    # መልዕክቱን ቀይሮ አዲሱን ሜኑ ያሳያል
    bot.edit_message_text(
        f"✨ **{s['changed']}**\n\nClick /start to refresh the welcome screen.",
        user_id, call.message.message_id, parse_mode="Markdown"
    )
    
    bot.send_message(user_id, "🔄", reply_markup=main_menu_keyboard(lang_code))

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'ok', 200
    return 'error', 400

@app.route('/')
def home(): return "Professional Bot is Running!"
    
