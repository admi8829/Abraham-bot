import os
import requests
import random
import string
import telebot
# ከዚህ በፊት እንዲህ ነበረ: from api.database import get_active_lotteries, supabase, save_new_ticket
# ወደዚህ ቀይረው፦
try:
    from database import get_active_lotteries, supabase, save_new_ticket
except ImportError:
    from api.database import get_active_lotteries, supabase, save_new_ticket

# Chapa ማረጋገጫ (Vercel Settings ላይ መኖሩን አረጋግጥ)
CHAPA_AUTH_KEY = os.getenv("CHAPA_AUTH_KEY")
# ይህ የ Vercel ፕሮጀክትህ ሊንክ ነው (ለምሳሌ: https://your-bot.vercel.app/api/chapa_webhook)
CALLBACK_URL = os.getenv("CHAPA_CALLBACK_URL") 

def generate_ticket_number():
    """ባለ 6 ዲጂት ለየት ያለ የትኬት ቁጥር ይፈጥራል (ምሳሌ: TX7R29)"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def show_lottery_types(bot, uid, lang):
    """የዕጣ አይነቶችን ከዳታቤዝ አምጥቶ ለተጠቃሚው ያሳያል"""
    lotteries = get_active_lotteries().data
    if not lotteries:
        msg = "⚠️ በአሁኑ ሰዓት ምንም ክፍት ዕጣ የለም።" if lang == "am" else "⚠️ No active lotteries."
        bot.send_message(uid, msg)
        return

    markup = telebot.types.InlineKeyboardMarkup()
    for lott in lotteries:
        name = lott['name_am'] if lang == "am" else lott['name_en']
        markup.add(telebot.types.InlineKeyboardButton(
            f"🎫 {name} - {lott['price']} ETB", 
            callback_data=f"lott_{lott['id']}"
        ))
    
    msg = "🎫 እባክዎ ሊቆርጡት የሚፈልጉትን የዕጣ አይነት ይምረጡ፦" if lang == "am" else "🎫 Select lottery type:"
    bot.send_message(uid, msg, reply_markup=markup)

def show_payment_options(bot, uid, lott_id, lang):
    """Automatic (Chapa) ወይም Manual (Screenshot) መምረጫ"""
    msg = "💳 **የክፍያ መንገድ ይምረጡ / Select Payment**"
    markup = telebot.types.InlineKeyboardMarkup()
    
    # Automatic (በ Chapa በኩል)
    markup.add(telebot.types.InlineKeyboardButton("🤖 Automatic (Chapa)", callback_data=f"pay_auto_{lott_id}"))
    # Manual (በቴሌብር ልኮ ፎቶ መላክ)
    markup.add(telebot.types.InlineKeyboardButton("✍️ Manual (Screenshot)", callback_data=f"pay_man_{lott_id}"))
    
    bot.send_message(uid, msg, reply_markup=markup, parse_mode="Markdown")

def create_chapa_payment(bot, uid, lott_id, amount, name):
    """ወደ Chapa የመክፈያ ሊንክ የሚወስድ ሲስተም"""
    ticket_num = generate_ticket_number()
    # tx_ref ለክፍያ ማረጋገጫነት ያገለግላል (ትኬት ቁጥርና የሰውየው ID ይይዛል)
    tx_ref = f"winx-{ticket_num}-{uid}-{lott_id}"

    payload = {
        "amount": str(amount),
        "currency": "ETB",
        "email": f"user{uid}@telegram.com",
        "first_name": name,
        "tx_ref": tx_ref,
        "callback_url": CALLBACK_URL,
        "customization": {
            "title": "Win-X Lottery",
            "description": f"Payment for Ticket #{ticket_num}"
        }
    }

    headers = {
        'Authorization': f'Bearer {CHAPA_AUTH_KEY}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post("https://api.chapa.co/v1/transaction/initialize", json=payload, headers=headers)
        res_data = response.json()

        if res_data.get('status') == 'success':
            checkout_url = res_data['data']['checkout_url']
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("💳 አሁኑኑ ይክፈሉ (Pay Now)", url=checkout_url))
            
            bot.send_message(uid, f"🚀 **ክፍያ ለመፈጸም ተዘጋጅቷል!**\n\nዕጣ፦ {amount} ETB\nትኬት ቁጥር፦ `{ticket_num}`\n\nከታች ያለውን በተን ተጭነው ይክፈሉ፦", 
                             reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(uid, "⚠️ የክፍያ ሊንኩን ማዘጋጀት አልተቻለም። እባክዎ ቆይተው ይሞክሩ።")
    except Exception as e:
        print(f"Chapa Connection Error: {e}")
        bot.send_message(uid, "❌ ከክፍያ ሲስተሙ ጋር መገናኘት አልተቻለም።")
  
