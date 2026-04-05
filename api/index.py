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
TOKEN = "7893868461:AAGRFs9oUfKhQNJP1Z_r9TBdYZhppZs_sog"
ADMIN_ID = 1417184246 
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
    welcome_msg = (
        "👋 Welcome to Smart-X Academy Lottery!\n"
        "እንኳን ወደ ስማርት-ኤክስ አካዳሚ የሎተሪ ቦት በሰላም መጡ።\n\n"
        "እባክዎ ቋንቋ ይምረጡ / Please choose your language:"
    )
    bot.send_message(message.chat.id, welcome_msg, reply_markup=lang_markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = call.message.chat.id
    data = call.data

    if data.startswith("lang_"):
        lang = data.split("_")[1]
        show_lottery_types(uid, lang)

    elif data.startswith("lott_"):
        lott_id = data.split("_")[1]
        send_payment_instructions(uid, lott_id)

    elif data.startswith(("approve_", "reject_")):
        handle_admin_decision(call)

def show_lottery_types(uid, lang):
    try:
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
    except Exception as e:
        bot.send_message(uid, f"❌ ስህተት ተፈጥሯል፦ {str(e)}")

def send_payment_instructions(uid, lott_id):
    msg = (
        "💳 **የክፍያ መመሪያ (Manual Payment)**\n\n"
        "1️⃣ ከታች ያለውን የ QR ኮድ በቴሌብር ስካን ያድርጉ።\n"
        "2️⃣ ወይም ወደዚህ ስልክ ቁጥር በቴሌብር ይላኩ፦ `0911223344` (ሲነኩት ኮፒ ይሆናል)\n"
        "3️⃣ ክፍያውን ከፈጸሙ በኋላ **የደረሰኙን ፎቶ (Screenshot)** እዚህ ይላኩ።\n\n"
        "⚠️ ትኬት የሚላከው ደረሰኝዎ በአድሚን ተረጋግጦ ሲፈቀድ ብቻ ነው።"
    )
    
    qr_path = os.path.join(os.path.dirname(__file__), 'my_qr.jpg')
    try:
        with open(qr_path, 'rb') as qr:
            bot.send_photo(uid, qr, caption=msg, parse_mode="Markdown")
    except:
        bot.send_message(uid, msg, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def handle_receipt_upload(message):
    uid = message.chat.id
    user_name = message.from_user.first_name
    
    bot.send_message(uid, "⏳ ደረሰኝዎ ደርሶናል። አረጋግጠን ትኬትዎን እስክንልክ ድረስ ለጥቂት ደቂቃዎች ይጠብቁ።")

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
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Permission Denied!")
        return

    action, target_uid = call.data.split('_')
    
    if action == "approve":
        ticket = generate_ticket_number()
        bot.send_message(target_uid, f"🎉 እንኳን ደስ አለዎት! ክፍያዎ ተረጋግጧል።\n\n🎫 የሎተሪ ትኬት ቁጥርዎ፦ `{ticket}`\nመልካም ዕድል!")
        bot.edit_message_caption(f"✅ ለ {target_uid} ትኬት ተልኳል።", call.message.chat.id, call.message.message_id)
    
    elif action == "reject":
        bot.send_message(target_uid, "❌ ይቅርታ፣ የላኩት ደረሰኝ ተቀባይነት አላገኘም። እባክዎ ትክክለኛውን ደረሰኝ መላክዎን ያረጋግጡ።")
        bot.edit_message_caption(f"🛑 የ {target_uid} ክፍያ ውድቅ ተደርጓል።", call.message.chat.id, call.message.message_id)

# --- VERCEL ROUTE ---
@app.route('/api/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Smart-X Bot is Active and Listening!", 200
        
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Forbidden', 403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
    
