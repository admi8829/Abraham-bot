import os
import telebot
from flask import Flask, request

# ከሌሎች ፋይሎች ጋር እናገናኛለን
from .database import check_user, add_user

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- 1. ሙሉ ስክሪን የሚሸፍን ዋና ሜኑ (Main Menu) ---
def main_menu_keyboard():
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    
    # አገልግሎቶች
    btn_buy = telebot.types.InlineKeyboardButton("🎫 ትኬት ቁረጥ (10 ETB)", callback_data="buy_ticket")
    btn_ref = telebot.types.InlineKeyboardButton("👥 Referral Link", callback_data="get_referral")
    btn_winners = telebot.types.InlineKeyboardButton("🏆 አሸናፊዎች", callback_data="winners_list")
    btn_profile = telebot.types.InlineKeyboardButton("👤 የእኔ መረጃ", callback_data="my_profile")
    
    # መረጃዎች
    btn_help = telebot.types.InlineKeyboardButton("🆘 Help & Info", callback_data="help_info")
    btn_contact = telebot.types.InlineKeyboardButton("📞 Contact Admin", callback_data="contact_admin")
    btn_yt = telebot.types.InlineKeyboardButton("🎬 YouTube Channel", url="https://youtube.com/@SmartQA_ET")
    btn_web = telebot.types.InlineKeyboardButton("🌐 Official Website", url="https://smartx-academy.vercel.app")
    
    # አደረጃጀት (ሙሉ ስክሪን እንዲመስል በረድፍ መደርደር)
    markup.add(btn_buy)
    markup.add(btn_ref, btn_winners)
    markup.add(btn_profile, btn_help)
    markup.add(btn_contact)
    markup.add(btn_web, btn_yt)
    
    return markup

# --- 2. ስልክ ቁጥር ማጋሪያ (Registration Keyboard) ---
def contact_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    button = telebot.types.KeyboardButton("📲 ስልክ ቁጥሬን አጋራ (Share Contact)", request_contact=True)
    markup.add(button)
    return markup

# --- 3. የ /start ትዕዛዝ (ያለ ምዝገባ የሚመጣ) ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    welcome_text = (
        f"👋 ሰላም {message.from_user.first_name}!\n\n"
        "እንኳን ወደ **Smart-X Academy** የዕጣ ቦት በደህና መጣህ።\n"
        "ይህ ቦት ተማሪዎች ትኬት በመቁረጥ ታላላቅ ሽልማቶችን የሚያገኙበት መድረክ ነው።\n\n"
        "ለመጀመር የሚፈልጉትን አገልግሎት ከታች ይምረጡ፦"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# --- 4. የባተን ክሊኮች (Callback Logic) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id
    user = check_user(user_id) # መመዝገቡን ቼክ እናደርጋለን
    
    # ሀ. ካልተመዘገበ ወደ ምዝገባ የሚወስዱ አገልግሎቶች
    if call.data in ["buy_ticket", "get_referral", "my_profile"]:
        if not user:
            msg = bot.send_message(
                call.message.chat.id, 
                "⚠️ ይህንን አገልግሎት ለመጠቀም መጀመሪያ ስልክ ቁጥርዎን ማጋራት አለብዎት።\nእባክዎ ከታች ያለውን **'Share Contact'** በተን ይጫኑ፦", 
                reply_markup=contact_keyboard()
            )
            # የቴሌግራም ስሙን በራሱ ይወስዳል
            bot.register_next_step_handler(msg, register_user_process, call.from_user.first_name)
            bot.answer_callback_query(call.id)
            return
    
    # ለ. ለተመዘገቡ ሰዎች የሚሰሩ አገልግሎቶች
    if call.data == "get_referral":
        bot.send_message(call.message.chat.id, f"👥 ያንተ መጋበዣ ሊንክ፦\nhttps://t.me/{(bot.get_me()).username}?start={user_id}")
    
    elif call.data == "buy_ticket":
        bot.send_message(call.message.chat.id, "💳 የ 10 ብር ክፍያ በ Chapa ለመፈጸም /pay ይበሉ። (ሊንክ በቅርቡ ይዘጋጃል)")
        
    elif call.data == "my_profile":
        text = f"👤 **መረጃህ**\n\nስም፦ {user['full_name']}\nስልክ፦ {user['phone']}\nክፍል፦ {user['grade']}"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

    # ሐ. ለማንም የሚሰሩ (ያለ ምዝገባ)
    elif call.data == "help_info":
        bot.send_message(call.message.chat.id, "📖 ይህ ቦት በ Smart-X Academy የተዘጋጀ የዕጣ ማውጫ ሲስተም ነው።")
    
    elif call.data == "contact_admin":
        bot.send_message(call.message.chat.id, "አድሚን ለማግኘት፦ @SmartX_Support")

    bot.answer_callback_query(call.id)

# --- 5. የምዝገባ ሂደት (ስልክ ቁጥር ብቻ) ---
def register_user_process(message, first_name):
    if message.contact is not None:
        phone = message.contact.phone_number
        # ስሙን ከቴሌግራም ወስዶ ዳታቤዝ ላይ ይጨምራል
        add_user(message.from_user.id, first_name, phone, "N/A")
        
        bot.send_message(
            message.chat.id, 
            "✅ ምዝገባህ ተሳክቷል! አሁን አገልግሎቱን ደግመህ ተጫን።", 
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )
        bot.send_message(message.chat.id, "ወደ ዋናው ሜኑ ተመለስ፦", reply_markup=main_menu_keyboard())
    else:
        bot.send_message(message.chat.id, "እባክህ ከታች ያለውን በተን ተጠቅመህ ስልክህን አጋራኝ።")

# --- 6. Vercel Webhook ---
@app.route('/', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

@app.route('/')
def home(): return "Smart-X Raffle Bot is Running!"
    
