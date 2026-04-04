import os
import telebot
from flask import Flask, request

# ከሌሎች ፋይሎች አስፈላጊ የሆኑ ፈንክሽኖችን Import እናደርጋለን
from api.database import register_user, get_user_lang, update_user_lang, get_all_winners

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ያንተ GIF/Video ID
MY_GIF_ID = "CgACAgQAAxkBAAICamnQ4Te5nXpICkuvCyQsEZk0y3O4AALWHAACQtCJUjnn_dB6DekvOwQ"

# --- 1. የጽሁፎች ማከማቻ (Strings) ---
strings = {
    "en": {
        "welcome": "👋 **Welcome, {name}!**\n\n━━━━━━━━━━━━━━━━━━━━\n🚀 **PREMIUM SERVICES**\n━━━━━━━━━━━━━━━━━━━━\n\n📞 **Phone:** +251963959697\n📢 **Channel:** [Join Social Gebeya](https://t.me/Social_Gebeya)\n\n📍 *Select a service from the menu below:*",
        "buy": "➕ Buy Ticket", "info": "👤 My Info", "win": "🎁 Winners",
        "ref": "👥 Referral", "help": "💡 Help", "lang": "🌐 Language",
        "lang_msg": "📌 **Select your preferred language:**",
        "changed": "✅ Language set to English!",
        "no_win": "⚠️ No winners recorded yet."
    },
    "am": {
        "welcome": "👋 **እንኳን ደህና መጡ፣ {name}!**\n\n━━━━━━━━━━━━━━━━━━━━\n🚀 **የእኛ ምርጥ አገልግሎቶች**\n━━━━━━━━━━━━━━━━━━━━\n\n📞 **ስልክ:** +251963959697\n📢 **ቻናል:** [ሶሻል ገበያ](https://t.me/Social_Gebeya)\n\n📍 *ለመጀመር ከታች ካሉት አማራጮች አንዱን ይምረጡ፦*",
        "buy": "➕ አዲስ ትኬት ቁረጥ", "info": "👤 የእኔ መረጃ", "win": "🎁 አሸናፊዎች",
        "ref": "👥 ጓደኛ ጋብዝ", "help": "💡 እገዛ", "lang": "🌐 ቋንቋ",
        "lang_msg": "📌 **እባክዎ ቋንቋ ይምረጡ፦**",
        "changed": "✅ ቋንቋ ወደ አማርኛ ተቀይሯል!",
        "no_win": "⚠️ እስካሁን ምንም አሸናፊ አልተመዘገበም።"
    }
}

# --- 2. የዲዛይን በተኖች (Keyboards) ---
def get_main_menu(lang="en"):
    s = strings[lang]
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(telebot.types.KeyboardButton(s["buy"]))
    markup.add(telebot.types.KeyboardButton(s["info"]), telebot.types.KeyboardButton(s["win"]))
    markup.add(telebot.types.KeyboardButton(s["ref"]), telebot.types.KeyboardButton(s["help"]))
    markup.add(telebot.types.KeyboardButton(s["lang"]))
    return markup

def lang_inline():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🇺🇸 English", callback_data="set_en"),
               telebot.types.InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="set_am"))
    return markup

# --- 3. የ /start ትዕዛዝ ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid, name = message.chat.id, message.from_user.first_name
    
    # ተጠቃሚውን ዳታቤዝ ላይ ይመዘግባል (ከ database.py የመጣ)
    register_user(uid, name)
    lang = get_user_lang(uid)
    
    bot.send_animation(
        uid, MY_GIF_ID, 
        caption=strings[lang]["welcome"].format(name=name),
        parse_mode="Markdown",
        reply_markup=get_main_menu(lang)
    )

# --- 4. የመልዕክት ማጣሪያ ---
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid, text = message.chat.id, message.text
    lang = get_user_lang(uid)
    s = strings[lang]

    if text == s["lang"]:
        bot.send_message(uid, s["lang_msg"], reply_markup=lang_inline())

    elif text == s["win"]:
        # አሸናፊዎችን ከዳታቤዝ ያመጣል
        winners = get_all_winners().data
        if not winners:
            bot.send_message(uid, s["no_win"])
            return
        
        msg = "🏆 **Recent Winners** 🏆\n\n"
        for w in winners:
            msg += f"👤 {w['users']['full_name']} | 🎫 {w['ticket_number']}\n💰 {w['prize_amount']}\n\n"
        bot.send_message(uid, msg, parse_mode="Markdown")

# --- 5. ቋንቋ መቀየሪያ Callback ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def set_language(call):
    uid = call.message.chat.id
    new_lang = call.data.split("_")[1]
    
    # ቋንቋውን ዳታቤዝ ላይ ያድሳል
    update_user_lang(uid, new_lang)
    s = strings[new_lang]
    
    bot.answer_callback_query(call.id, s["changed"])
    bot.send_message(uid, s["changed"], reply_markup=get_main_menu(new_lang))
    bot.delete_message(uid, call.message.message_id)

# --- 6. Vercel Webhook ---
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
        return 'ok', 200
    return 'error', 400

@app.route('/')
def home(): return "Win-X Bot is Active!"
    
