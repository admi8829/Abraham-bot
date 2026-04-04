import os
import telebot
import requests
from flask import Flask, request

TOKEN = "7893868461:AAGRFs9oUfKhQNJP1Z_r9TBdYZhppZs_sog"
CHAPA_KEY = os.getenv("CHAPA_SECRET_KEY")

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def welcome(message):
    markup = telebot.types.InlineKeyboardMarkup()
    btn = telebot.types.InlineKeyboardButton("ትኬት ግዛ (10 ETB)", callback_data="buy_ticket")
    markup.add(btn)
    bot.reply_to(message, "እንኳን ደህና መጣህ! የዕጣ ትኬት ለመግዛት ከታች ያለውን ተጫን።", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "buy_ticket")
def start_payment(call):
    headers = {"Authorization": f"Bearer {CHAPA_KEY}"}
    payload = {
        "amount": "10",
        "currency": "ETB",
        "email": "user@gmail.com",
        "first_name": call.from_user.first_name,
        "tx_ref": f"tx-{call.from_user.id}-{os.urandom(2).hex()}",
        "callback_url": "https://abraham-bot.vercel.app/",
        "customization": {"title": "Smart-X Raffle", "description": "Ticket Payment"}
    }
    
    r = requests.post("https://api.chapa.co/v1/transaction/initialize", json=payload, headers=headers)
    data = r.json()
    
    if data.get("status") == "success":
        url = data['data']['checkout_url']
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("አሁኑኑ ክፈል", url=url))
        bot.send_message(call.message.chat.id, "ክፍያ ለመፈጸም ሊንኩን ተጫን፦", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, "ስህተት አለ! Key-ህን Vercel ላይ መሙላትህን አረጋግጥ።")

@app.route('/', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

@app.route('/')
def home(): return "Bot is Ready!"
    
