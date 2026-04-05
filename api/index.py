import os
import telebot
import random
import string
from flask import Flask, request

# የዳታቤዝ ፈንክሽኖችን ከ database.py ማስገባት
try:
    from database import get_active_lotteries, supabase, save_new_ticket
except ImportError:
    from api.database import get_active_lotteries, supabase, save_new_ticket

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 1417184246  # 👈 እዚህ ጋር ያንተን ID ተካው!
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def generate_ticket_number():
    """ባለ 6 ዲጂት ለየት ያለ የትኬት ቁጥር ይፈጥራል"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# --- BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    lang_markup = telebot.types.InlineKeyboardMarkup()
    lang_markup.add(
        telebot.types.InlineKeyboardButton("አማርኛ 🇪🇹", callback_data="lang_am"),
        telebot.types.InlineKeyboardButton("English 🇺🇸", callback_data="lang_en")
    )
    bot.send_message(message.chat.id, "Welcome to Win-X Academy Lottery! / እንኳን ወደ ዊን-ኤክስ አካዳሚ የሎተሪ ቦት መጡ።\n\nእባክዎ ቋንቋ ይምረጡ / Please choose your language:", reply_markup=lang_markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = call.message.chat.id
    data = call.data

    # ቋንቋ መረጣ
    if data.startswith("lang_"):
        lang = data.split("_")[1]
        show_lottery_types(uid, lang)

    # የሎተሪ አይነት መረጣ
    elif data.startswith("lott_"):
        lott_id = data.split("_")[1]
        send_payment_instructions(uid, lott_id)

    # የአድሚን ማረጋገጫ (Approve/Reject)
    elif data.startswith(("approve_", "reject_")):
        handle_admin_decision(call)

def show_lottery_types(uid, lang):
    res = get_active_lotteries()
    lotteries = res.data
    
    if not lotteries:
        bot.send_message(uid, "⚠️ በአሁኑ ሰዓት ምንም ክፍት ዕጣ የለም።")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    for lott in lotteries:
        name = lott['name_am'] if lang == "am" else lott['name_en']
        btn_text = f"🎫 {name} - {lott['price']} ETB"
        markup.add(telebot.types.InlineKeyboardButton(btn_text, callback_data=f"lott_{lott['id']}"))
    
    msg = "🎰 ሊሳተፉበት የሚፈልጉትን የዕጣ አይነት ይምረጡ፦"
    bot.send_message(uid, msg, reply_markup=markup)

def send_payment_instructions(uid, lott_id):
    """ለተጠቃሚው የ QR ኮድ እና የክፍያ መመሪያ መላኪያ"""
    msg = (
        "💳 **የክፍያ መመሪያ**\n\n"
        "1️⃣ ከታች ያለውን የ QR ኮድ 'Save' አድርገው በቴሌብር ስካን ያድርጉ።\n"
        "2️⃣ ወይም ወደዚህ ስልክ ቁጥር ይላኩ፦ `0911223344` (ሲነኩት ኮፒ ይሆናል)\n"
        "3️⃣ ክፍያውን ከፈጸሙ በኋላ **የደረሰኙን ፎቶ (Screenshot)** እዚህ ይላኩ።\n\n"
        "⚠️ ትኬት የሚላከው ደረሰኝዎ በአድሚን ሲረጋገጥ ብቻ ነው።"
    )
    
    # የ QR ፎቶውን መላክ (ፎቶው በፎልደሩ ውስጥ 'my_qr.jpg' ተብሎ መቀመጥ አለበት)
    try:
        with open('my_qr.jpg', 'rb') as qr:
            bot.send_photo(uid, qr, caption=msg, parse_mode="Markdown")
    except FileNotFoundError:
        bot.send_message(uid, msg, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def handle_receipt_upload(message):
    """ተጠቃሚው የደረሰኝ ፎቶ ሲልክ"""
    uid = message.chat.id
    user_name = message.from_user.first_name
    
    bot.send_message(uid, "⏳ ደረሰኝዎ ደርሶናል። አረጋግጠን ትኬትዎን እስክንልክ ድረስ ለጥቂት ደቂቃዎች ይጠብቁ።")

    # ለአድሚኑ (ላንተ) ፎቶውን መላክ
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("✅ ፍቀድ (Approve)", callback_data=f"approve_{uid}"),
        telebot.types.InlineKeyboardButton("❌ ከልክል (Reject)", callback_data=f"reject_{uid}")
    )
    
    bot.send_photo(
        ADMIN_ID, 
        message.photo[-1].file_id, 
        caption=f"💰 **አዲስ የክፍያ ደረሰኝ!**\n\nከ: {user_name}\nID: `{uid}`",
        reply_markup=markup,
        parse_mode="Markdown"
    )

def handle_admin_decision(call):
    action, target_uid = call.data.split('_')
    
    if action == "approve":
        ticket = generate_ticket_number()
        # ለተጠቃሚው ትኬት መላክ
        bot.send_message(target_uid, f"🎉 እንኳን ደስ አለዎት! ክፍያዎ ተረጋግጧል።\n\n🎫 የሎተሪ ትኬት ቁጥርዎ፦ `{ticket}`\nመልካም ዕድል!")
        bot.edit_message_caption(f"✅ ለ {target_uid} ትኬት ተልኳል።", call.message.chat.id, call.message.message_id)
        
        # ለዳታቤዝ ማስቀመጥ ከፈለግህ እዚህ ጋር save_new_ticket መጥራት ትችላለህ
    
    elif action == "reject":
        bot.send_message(target_uid, "❌ ይቅርታ፣ የላኩት ደረሰኝ ተቀባይነት አላገኘም። እባክዎ ትክክለኛውን ደረሰኝ መላክዎን ያረጋግጡ።")
        bot.edit_message_caption(f"🛑 የ {target_uid} ክፍያ ውድቅ ተደርጓል።", call.message.chat.id, call.message.message_id)

# --- VERCEL ROUTE ---
@app.route('/api/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Forbidden', 403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
