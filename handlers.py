from aiogram import types, F
from aiogram.filters import Command
from keyboards import get_main_menu, get_start_inline
import database as db

# እዚህ ጋር ሁሉንም የ @dp.message እና @dp.callback_query handlers ትጨምራለህ
# ለምሳሌ Start handler:
async def start_handler(message: types.Message, bot):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    db.register_user(user_id, username, None) # ቀለል ያለ ምሳሌ
    lang = db.get_user_lang(user_id)
    await message.answer("ሰላም!", reply_markup=get_main_menu(lang))

