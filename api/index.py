import telebot
from flask import Flask, request

# የሰጠኸኝ Token እዚህ ገብቷል
TOKEN = "7893868461:AAGRFs9oUfKhQNJP1Z_r9TBdYZhppZs_sog"
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# /start ሲባል የሚመጣው መልዕክት
@bot.message_handler(commands=['start'])
def welcome(message):
    user_name = message.from_user.first_name
    welcome_text = f"ሰላም {user_name}! ወደ Smart-X Academy እንኳን ደህና መጣህ።\n\nይህ ቦት በ Vercel Webhook ላይ 24/7 እየሰራ ነው።"
    bot.reply_to(message, welcome_text)

# ማንኛውም ሌላ ጽሁፍ ሲላክ የሚመልሰው
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "መልዕክትህ ደርሶኛል! አሁን ቦቱ በደመና (Vercel) ላይ ነው።")

# Vercel መልዕክት የሚቀበልበት መንገድ (Webhook)
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'ok', 200
    else:
        return 'Forbidden', 403

@app.route('/')
def home():
    return "Bot is active and running!"
