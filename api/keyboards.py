from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def get_main_menu(lang="am"):
    kb = ReplyKeyboardBuilder()
    buttons = {
        "en": ["➕ Buy New Ticket", "👤 My Info", "🎁 Winners", "👥 Invite Friends", "💡 Help", "🌐 Language"],
        "am": ["➕ አዲስ ትኬት ቁረጥ", "👤 የእኔ መረጃ", "🎁 አሸናፊዎች", "👥 ጓደኛ ጋብዝ", "💡 እገዛ", "🌐 ቋንቋ"]
    }
    for btn in buttons[lang]:
        kb.button(text=btn)
    kb.adjust(1, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True)

def get_start_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌐 Website", url="https://yourwebsite.com"))
    builder.row(InlineKeyboardButton(text="📺 YouTube", url="https://youtube.com/@yourchannel"))
    return builder.as_markup()

