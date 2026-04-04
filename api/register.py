from .database import check_user, add_user

def start_registration(bot, message):
    user_id = message.from_user.id
    user = check_user(user_id)
    
    if user:
        bot.send_message(message.chat.id, f"ሰላም {user['full_name']}! አስቀድመህ ተመዝግበሃል።")
    else:
        msg = bot.send_message(message.chat.id, "ለዕጣው ለመሳተፍ መጀመሪያ መመዝገብ አለብህ። ሙሉ ስምህን ጻፍልኝ፦")
        bot.register_next_step_handler(msg, get_name, bot)

def get_name(message, bot):
    name = message.text
    msg = bot.send_message(message.chat.id, f"በጣም ጥሩ {name}! አሁን ደግሞ ስልክህን አስገባ፦")
    bot.register_next_step_handler(msg, get_phone, bot, name)

def get_phone(message, bot, name):
    phone = message.text
    msg = bot.send_message(message.chat.id, "የመጨረሻ! ስንተኛ ክፍል ነህ? (9-12)፦")
    bot.register_next_step_handler(msg, finish_reg, bot, name, phone)

def finish_reg(message, bot, name, phone):
    grade = message.text
    add_user(message.from_user.id, name, phone, grade)
    bot.send_message(message.chat.id, "🎉 ምዝገባህ ተሳክቷል! አሁን ትኬት መቁረጥ ትችላለህ።")

