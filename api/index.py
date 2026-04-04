import os
import telebot
from flask import Flask, request

# በ Vercel ላይ ፋይሎቹ በአንድ ፎልደር ውስጥ ስላሉ ከፊት ለፊቱ ነጥብ (.) እንጠቀማለን
# ወይም ቀጥታ ስማቸውን ብቻ መጥራት ይቻላል
try:
    from database import register_user, get_user_lang, update_user_lang, get_all_winners
    from lottery import show_lottery_types, show_payment_options, create_chapa_payment
except ImportError:
    # ይህ ደግሞ በሎካል ኮምፒውተር ላይ ስትሞክረው እንዳይሳሳት ይረዳል
    from api.database import register_user, get_user_lang, update_user_lang, get_all_winners
    from api.lottery import show_lottery_types, show_payment_options, create_chapa_payment
    
# የቦቱን Token ከ Vercel Environment Variables ያነባል
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ያንተ ቪዲዮ/GIF ID
MY_GIF_ID = "CgACAgQAAxkBAAICamnQ4Te5nXpICkuvCyQsEZk0y3O4AALWHAACQtCJUjnn_dB6DekvOwQ"

# --- 1. የቋንቋ እና የጽሁፍ ማከማቻ ---
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
    # ዳታቤዝ ውስጥ ያለው ቋንቋ ባይኖር እንኳ ወደ English Default እንዲያደርግ strings.get ተጠቅመናል
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

# --- 3. የ /start ትዕዛዝ ---
@bot.message_handler(commands=['start'])
def start_command(message):
    uid = message.chat.id
    name = message.from_user.first_name
    
    # መጀመሪያ ዳታቤዝ ውስጥ ያለውን ቋንቋ እንፈትሻለን (Register ከማድረጋችን በፊት)
    lang = get_user_lang(uid)
    
    # ተጠቃሚውን ባለበት ቋንቋ ዳታቤዝ ላይ እንመዘግባለን
    register_user(uid, name, lang)
    
    # ቪዲዮውን እና ሜኑውን እንልካለን
    bot.send_animation(
        uid, MY_GIF_ID, 
        caption=strings[lang]["welcome"].format(name=name),
        parse_mode="Markdown",
        reply_markup=get_main_menu(lang)
    )
    # --- 4. የመልዕክት ማጣሪያ (Main Logic) ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    uid = message.chat.id
    text = message.text
    
    # ቋንቋውን ከዳታቤዝ እናነባለን
    lang = get_user_lang(uid)
    s = strings.get(lang, strings["en"])

    # 1. ቋንቋ ለመቀየር
    if text == s["lang"]:
        bot.send_message(uid, s["lang_msg"], reply_markup=get_lang_inline())

    # 2. አዲስ ትኬት ለመቁረጥ (አዲስ የተጨመረው ክፍል)
    elif text == s["buy"]:
        # ከ lottery.py ፋይል ላይ show_lottery_typesን ይጠራል
        from api.lottery import show_lottery_types
        show_lottery_types(bot, uid, lang)

    # 3. አሸናፊዎችን ለማየት
    elif text == s["win"]:
        winners_res = get_all_winners()
        winners_list = winners_res.data
        
        if not winners_list:
            bot.send_message(uid, s["no_win"])
            return
            
        response = "🏆 **Recent Winners** 🏆\n━━━━━━━━━━━━━━━━━━━━\n"
        for w in winners_list:
            user_name = w.get('users', {}).get('full_name', 'Player')
            response += f"👤 {user_name} | 🎫 {w['ticket_number']}\n💰 {w['prize_amount']}\n━━━━━━━━━━━━━━━━━━━━\n"
        bot.send_message(uid, response, parse_mode="Markdown")

    # 4. የተጠቃሚው መረጃ
    elif text == s["info"]:
        info_text = f"📊 **DASHBOARD**\n━━━━━━━━━━━━━━━━━━━━\n👤 Name: {message.from_user.first_name}\n🆔 ID: `{uid}`\n🎟 Tickets: 0\n━━━━━━━━━━━━━━━━━━━━"
        bot.send_message(uid, info_text, parse_mode="Markdown")
    
# --- 5. የቋንቋ ምርጫ Callback ---
@bot.callback_query_handler(func=lambda call: True)
def callback_all(call):
    uid = call.message.chat.id
    data = call.data
    lang = get_user_lang(uid)

    # ሀ. ቋንቋ መቀየሪያ (ቀድሞ የነበረው)
    if data.startswith("set_"):
        new_lang = data.split("_")[1]
        update_user_lang(uid, new_lang)
        bot.send_message(uid, strings[new_lang]["changed"], reply_markup=get_main_menu(new_lang))
        bot.delete_message(uid, call.message.message_id)

    # ለ. የእጣ አይነት ሲመረጥ (አዲስ የሚጨመር)
    elif data.startswith("lott_"):
        lott_id = data.split("_")[1]
        # ተጠቃሚው Manual ወይስ Auto እንዲከፍል ምርጫ እናሳያለን
        show_payment_options(bot, uid, lott_id, lang)
        bot.delete_message(uid, call.message.message_id)

    # ሐ. በ Chapa (Automatic) መክፈል ሲመርጥ (አዲስ የሚጨመር)
    elif data.startswith("pay_auto_"):
        lott_id = data.split("_")[2]
        # ከዳታቤዝ ዋጋውን አምጥተን ወደ Chapa እንልካለን
        from api.database import supabase
        lott_data = supabase.table("lotteries").select("*").eq("id", lott_id).execute().data[0]
        
        # የ Chapa ሊንክ ይፈጠራል
        create_chapa_payment(bot, uid, lott_id, lott_data['price'], f"user{uid}@telegram.com", call.from_user.first_name)

    # መ. በሰው (Manual) መክፈል ሲመርጥ (አዲስ የሚጨመር)
    elif data.startswith("pay_man_"):
        bot.send_message(uid, "🙏 እባክዎ ክፍያውን በ Telebirr 0963959697 ይላኩና የደረሰኙን ፎቶ (Screenshot) እዚህ ይላኩ።")
        

# --- 6. Vercel Webhook Configuration ---
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
    return "Win-X Bot is Active and Running!"

if __name__ == "__main__":
    app.run()
    
