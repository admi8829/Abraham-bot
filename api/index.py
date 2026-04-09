import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from handlers import start_handler

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Handler-ን እዚህ Register እናደርጋለን
dp.message.register(start_handler, Command("start"))

app = FastAPI()
WEBHOOK_PATH = f"/bot/{TOKEN}"

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update_data = await request.json()
    update = types.Update.model_validate(update_data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"status": "ok"}
    
