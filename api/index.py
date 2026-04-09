import os
import sys
import asyncio
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# 1. የፋይል መንገድ ማስተካከያ (ለ Vercel ወሳኝ ነው)
# ይህ መስመር Python ከ 'api' ፎልደር ውጭ ያሉትን handlers እና database እንዲያይ ይረዳዋል
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# አሁን ያለምንም ስህተት ከ handlers.py ላይ መጥራት ይቻላል
from handlers import (
    start_handler, 
    handle_photos, 
    buy_ticket_step1, 
    handle_contact, 
    my_info_handler, 
    show_winners, 
    invite_friends_handler, 
    show_language_options
)

# 2. Initialization
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# 3. Handlers Registration
# እዚህ ጋር ለ handlers አስፈላጊ የሆኑ ተጨማሪ መረጃዎችን (እንደ bot) በ lambda እናስተላልፋለን
dp.message.register(lambda m: start_handler(m, bot), Command("start"))
dp.message.register(buy_ticket_step1, lambda m: m.text in ["➕ አዲስ ትኬት ቁረጥ", "➕ Buy New Ticket"])
dp.message.register(handle_contact, lambda m: m.contact is not None)
dp.message.register(lambda m: handle_photos(m, bot), lambda m: m.photo is not None)
dp.message.register(my_info_handler, lambda m: m.text in ["👤 የእኔ መረጃ", "👤 My Info"])
dp.message.register(show_winners, lambda m: m.text in ["🎁 አሸናፊዎች", "🎁 Winners"])
dp.message.register(lambda m: invite_friends_handler(m, bot), lambda m: m.text in ["👥 ጓደኛ ጋብዝ", "👥 Invite Friends"])
dp.message.register(show_language_options, lambda m: m.text in ["🌐 ቋንቋ", "🌐 Language"])

# 4. FastAPI Setup
app = FastAPI()
WEBHOOK_PATH = f"/bot/{TOKEN}"

@app.get("/")
async def root():
    return {"message": "Bot is running!"}

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    try:
        update_data = await request.json()
        update = types.Update.model_validate(update_data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        print(f"Webhook Error: {e}")
        return {"status": "error", "message": str(e)}

# 5. Webhook Setup on Startup
@app.on_event("startup")
async def on_startup():
    webhook_url = f"{os.getenv('WEBHOOK_URL')}{WEBHOOK_PATH}"
    await bot.set_webhook(url=webhook_url)
