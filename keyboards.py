from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# 1. ዋናው ሜኑ (Reply Keyboard)
def get_main_menu(lang="am"):
    kb = ReplyKeyboardBuilder()
    
    if lang == "en":
        buttons = [
            "➕ Buy New Ticket", "👤 My Info", 
            "🎁 Winners", "👥 Invite Friends", 
            "💡 Help", "🌐 Language"
        ]
    else:
        # አማርኛ ምርጫዎች
        buttons = [
            "➕ አዲስ ትኬት ቁረጥ", "👤 የእኔ መረጃ", 
            "🎁 አሸናፊዎች", "👥 ጓደኛ ጋብዝ", 
            "💡 እገዛ", "🌐 ቋንቋ"
        ]
        
    for btn in buttons:
        kb.button(text=btn)
        
    # ቁልፎቹ በምን አይነት ድርድር ይቀመጡ (1 ረድፍ፣ ከዚያ 2፣ ከዚያ 2...)
    kb.adjust(1, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True)

# 2. የጅማሮ ኢንላይን በተኖች (Social Links)
def get_start_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌐 Website", url="https://yourwebsite.com"))
    builder.row(InlineKeyboardButton(text="📺 YouTube", url="https://youtube.com/@yourchannel"))
    builder.row(InlineKeyboardButton(text="📞 Contact Us", url="https://t.me/your_admin_username"))
    return builder.as_markup()

# 3. የቋንቋ መምረጫ በተኖች
def get_language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="አማርኛ 🇪🇹", callback_data="set_am"))
    builder.add(InlineKeyboardButton(text="English 🇺🇸", callback_data="set_en"))
    return builder.as_markup()

# 4. የስልክ ቁጥር ማጋሪያ በተን
def get_contact_keyboard(lang="am"):
    kb = ReplyKeyboardBuilder()
    text = "📲 ስልክ ቁጥርህን አጋራ / Share Contact" if lang == "am" else "📲 Share Contact"
    kb.button(text=text, request_contact=True)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)
    
