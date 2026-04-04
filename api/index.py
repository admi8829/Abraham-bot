import os
import telebot
from flask import Flask, request

# በ Vercel ላይ ፋይሎቹ በአንድ api/ ፎልደር ውስጥ ስለሚገኙ እንዲህ እናስገባቸዋለን
try:
    from database import register_user, get_user_lang, update_user_lang, get_all_winners, supabase, save_new_ticket
    from lottery import show_lottery_types, show_payment_options, create_chapa_payment
except ImportError:
    from api.database import register_user, get_user_lang, update_user_lang, get_all_winners, supabase, save_new_ticket
    from api.lottery import show_lottery_types, show_payment_options, create_chapa_payment
    
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

MY_GIF_ID = "CgACAgQAAxkBAAICamnQ4Te5nXpICkuvCyQsEZk0y3O4AALWHAACQtCJUjnn_dB6DekvOwQ"

strings = {
    "en": {
        "welcome": "👋 **Welcome, {name}!**\n\n📍 *Select a service from the menu below:*",
        "buy": "➕ Buy Ticket", "info": "👤 My Info", "win": "🎁 Winners",
        "ref": "👥 Referral", "help": "💡 Help", "lang": "🌐 Language",
        "lang_msg": "📌 **Select your preferred language:**",
        "changed": "✅ Language set to English!",
        "no_win": "⚠️ No winners recorded yet."
    },
    "am": {
        "welcome": "👋 **እንኳን ደህና መጡ፣ {name}!**\n\n📍 *ለመጀመር ከታች ካሉት አማራጮች አንዱን ይምረጡ፦*",
        "buy": "➕ አዲስ ትኬት ቁረጥ", "info": "👤 የእኔ መረጃ", "win": "🎁 አሸናፊዎች",
        "ref": "👥 ጓደኛ ጋብዝ", "help": "💡 እገዛ", "lang": "🌐 ቋንቋ",
        "lang_msg": "📌 **እባክዎ ቋንቋ ይምረጡ፦**",
        "changed": "✅ ቋንቋ ወደ አማርኛ ተቀይሯል!",
        "no_win": "⚠️ እስካሁን ምንም አሸናፊ አልተመዘገበም።"
    }
}

def get_main_menu(lang="en"):
    s = strings.get(lang, strings["en"])
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(telebot.types.KeyboardButton(s["buy"]))
    markup.add(telebot.types.KeyboardButton(s["info"]), telebot.types.KeyboardButton(s["win"]))
    markup.add(telebot.types.KeyboardButton(s["ref"]), telebot.types.KeyboardButton(s["help"]))
    markup.add(telebot.types.KeyboardButton(s["lang"]))
    return markup

def get_lang_inline():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🇺🇸 English", callback_data="set_en"),
               telebot.types.InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="set_am"))
    return markup

@bot.message_handler(commands=['start'])
def start_command(message):
    uid = message.chat.id
    name = message.from_user.first_name
    lang = get_user_lang(uid)
    register_user(uid, name, lang)
    bot.send_animation(uid, MY_GIF_ID, caption=strings[lang]["welcome"].format(name=name),
                       parse_mode="Markdown", reply_markup=get_main_menu(lang))

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    uid = message.chat.id
    lang = get_user_lang(uid)
    s = strings.get(lang, strings["en"])

    if message.text == s["lang"]:
        bot.send_message(uid, s["lang_msg"], reply_markup=get_lang_inline())
    elif message.text == s["buy"]:
        show_lottery_types(bot, uid, lang)
    elif message.text == s["win"]:
        winners_list = get_all_winners().data
        if not winners_list:
            bot.send_message(uid, s["no_win"])
            return
        response = "🏆 **Recent Winners** 🏆\n"
        for w in winners_list:
            user_name = w.get('users', {}).get('full_name', 'Player')
            response += f"👤 {user_name} | 🎫 {w['ticket_number']}\n"
        bot.send_message(uid, response, parse_mode="Markdown")
    elif message.text == s["info"]:
        bot.send_message(uid, f"📊 **DASHBOARD**\n👤 Name: {message.from_user.first_name}\n🆔 ID: `{uid}`", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_all(call):
    uid = call.message.chat.id
    data = call.data
    lang = get_user_lang(uid)

    if data.startswith("set_"):
        new_lang = data.split("_")[1]
        update_user_lang(uid, new_lang)
        bot.send_message(uid, strings[new_lang]["changed"], reply_markup=get_main_menu(new_lang))
        bot.delete_message(uid, call.message.message_id)
    elif data.startswith("lott_"):
        show_payment_options(bot, uid, data.split("_")[1], lang)
        bot.delete_message(uid, call.message.message_id)
    elif data.startswith("pay_auto_"):
        lott_id = data.split("_")[2]
        res = supabase.table("lotteries").select("*").eq("id", lott_id).execute()
        if res.data:
            create_chapa_payment(bot, uid, lott_id, res.data[0]['price'], call.from_user.first_name)
        bot.answer_callback_query(call.id)
    elif data.startswith("pay_man_"):
        bot.send_message(uid, "🙏 እባክዎ ክፍያውን በ Telebirr 0963959697 ይላኩና ደረሰኝ ይላኩ።")

@app.route('/api/chapa_webhook', methods=['POST'])
def chapa_webhook():
    data = request.get_json()
    if data and data.get('status') == 'success':
        tx_ref = data.get('tx_ref') # winx-TICKET-UID-LID
        p = tx_ref.split('-')
        if len(p) >= 4:
            save_new_ticket(p[2], p[3], p[1])
            bot.send_message(p[2], f"✅ ክፍያ ተረጋግጧል! ትኬት ቁጥር፦ `{p[1]}`")
    return 'ok', 200

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
        return 'ok', 200
    return 'error', 400

@app.route('/')
def home(): return "Win-X Bot is Active!"
