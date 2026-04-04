import os
import telebot
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "ሰላም! አሁን ያዘጋጀኸውን GIF ላክልኝና ID ቁጥሩን እነግርሃለሁ።")

@bot.message_handler(content_types=['animation'])
def get_gif_id(message):
    # GIF ሲላክለት ID ቁጥሩን ይልካል
    file_id = message.animation.file_id
    bot.reply_to(message, f"የ GIF መለያ ቁጥርህ (File ID) ይኸውልህ፦\n\n`{file_id}`", parse_mode="Markdown")

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
    return "Bot is running..."
    
