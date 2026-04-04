import os
import telebot
import time
from flask import Flask, request

# የቦቱን Token ከ Vercel Environment Variables ያነባል
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ያንተ GIF ID (በትክክል መስራቱን አረጋግጥ)
MY_GIF_ID = "CgACAgQAAxkBAAICamnQ4Te5nXpICkuvCyQsEZk0y3O4AALWHAACQtCJUjnn_dB6DekvOwQ"

# --- 1. የቋንቋ ዳታ (መጀመሪያ በ English እንዲሆን) ---
strings = {
    "en": {
        "welcome": "👋 **Welcome, {name}!**\n\nThis platform provides the best services for your needs. Join us to grow and achieve more.\n\n📞 **+251963959697**\n📢 [Join Our Telegram Channel](https://t.me/Social_Gebeya)\n\nChoose a service below to start: 👇",
        "buy": "➕ Buy Ticket",
        "info": "👤 My Info",
        "win": "🎁 Winners",
        "ref": "👥 Referral",
        "help": "💡 Help",
        "lang": "🌐 Language",
        "lang_msg": "📌 Please select your preferred language:",
        "changed": "✅ Language set to English!"
    },
    "am": {
        "welcome": "👋 **እንኳን ደህና መጡ፣ {name}!**\n\nይህ መድረክ ለፍላጎትዎ ምርጥ አገልግሎቶችን ይሰጣል። ለማደግ እና የበለጠ ለማግኘት ይቀላቀሉን።\n\n📞 **+251963959697**\n📢 [ቴሌግራም ቻናላችንን ይቀላቀሉ](https://t.me/Social_Gebeya)\n\nለመጀመር ከታች ካሉት አገልግሎቶች አንዱን ይምረጡ፦ 👇",
        "buy": "➕ አዲስ ትኬት ቁረጥ",
        "info": "👤 የእኔ መረጃ",
        "win": "🎁 አሸናፊዎች",
        "ref": "👥 ጓደኛ ጋብዝ",
        "help": "💡 እገዛ",
        "lang": "🌐 ቋንቋ",
        "lang_msg": "📌 እባክዎ ቋንቋ ይምረጡ፦",
        "changed": "✅ ቋንቋ ወደ አማርኛ ተቀይሯል!"
    },
    "or": {
        "welcome": "👋 **Baga Nagaan Dhuftan, {name}!**\n\nPlatformiin kun tajaajila gaarii isiniif kenna. Nuun walitti makamaa.\n\n📞 **+251963959697**\n📢 [Garee Keenya Tajaajilaa](https://t.me/Social_Gebeya)\n\nEegaluuf tajaajila gadii keessaa tokko filadhu: 👇",
        "buy": "➕ Tikkee Bitadhu",
        "info": "👤 Odeeffannoo Koo",
        "win": "🎁 Mo'attoota",
        "ref": "👥 Nama Affeeruuf",
        "help": "💡 Gargaarsa",
        "lang": "🌐 Afaan",
        "lang_msg": "📌 Maaloo afaan filadhu:",
        "changed": "✅ Afaan gara Oromootti jijjiirameera!"
    }
}

# --- 2. የሊንክ በተኖች (Website, Contact, TikTok) ---
def welcome_inline_buttons():
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn_web = telebot.types.InlineKeyboardButton("🌐 Website", url="https://yourwebsite.com")
    btn_con = telebot.types.InlineKeyboardButton("📩 Contact Us", url="https://t.me/your_admin_username")
    btn_tik = telebot.types.InlineKeyboardButton("🎬 TikTok", url="https://tiktok.com/@your_id")
    markup.add(btn_web, btn_con)
    markup.add(btn_tik)
    return markup

# --- 3. ቋሚ ሜኑ (Reply Keyboard) ---
def main_menu_keyboard(lang="en"):
    s = strings[lang]
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(telebot.types.KeyboardButton(s["buy"]))
    markup.add(telebot.types.KeyboardButton(s["info"]), telebot.types.KeyboardButton(s["win"]))
    markup.add(telebot.types.KeyboardButton(s["ref"]), telebot.types.KeyboardButton(s["help"]))
    markup.add(telebot.types.KeyboardButton(s["lang"]))
    return markup

# --- 4. የቋንቋ ምርጫ Inline ---
def language_inline():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🇺🇸 English", callback_data="setlang_en"),
               telebot.types.InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="setlang_am"),
               telebot.types.InlineKeyboardButton("🇪🇹 Afaan Oromoo", callback_data="setlang_or"))
    return markup

# --- 5. የ /start ትዕዛዝ ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        bot.send_chat_action(message.chat.id, 'upload_video')
        # ቪዲዮውን ከነ caption እና inline buttons ይልካል
        bot.send_animation(
            chat_id=message.chat.id,
            animation=MY_GIF_ID,
            caption=strings["en"]["welcome"].format(name=message.from_user.first_name),
            reply_markup=welcome_inline_buttons(),
            parse_mode="Markdown",
            disable_notification=True
        )
        # ዋናውን ሜኑ ይልካል
        bot.send_message(message.chat.id, "--- Main Menu ---", reply_markup=main_menu_keyboard("en"))
    except Exception as e:
        # ቪዲዮው ላይ ችግር ካለ በጽሁፍ ብቻ እንዲልክ
        bot.send_message(message.chat.id, strings["en"]["welcome"].format(name=message.from_user.first_name), reply_markup=main_menu_keyboard("en"), parse_mode="Markdown")

# --- 6. የባተን ክሊኮችን ማስተናገጃ ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    text = message.text
    user_id = message.chat.id
    bot.send_chat_action(user_id, 'typing')

    for lang in strings:
        s = strings[lang]
        if text == s["lang"]:
            bot.send_message(user_id, s["lang_msg"], reply_markup=language_inline())
            return
        if text == s["info"]:
            info_text = f"📋 **User Dashboard**\n\n👤 Name: {message.from_user.first_name}\n🆔 User ID: `{user_id}`\n🎟 Tickets: 0"
            bot.send_message(user_id, info_text, parse_mode="Markdown")
            return
        if text == s["buy"]:
            # ምንም መልስ አይሰጥም (ባዶ)
            return

# --- 7. የቋንቋ ምርጫ Callback ---
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
    # የቆየውን መልዕክት ያጠፋል
    bot.delete_message(call.message.chat.id, call.message.message_id)

# --- 8. Vercel Webhook Configuration ---
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
    return "Bot is Live and Responsive!"
    
