import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import re
import json
import os
import time
import threading
import schedule

TOKEN = os.environ.get('8596282396:AAFKJKhqeB59XtM_-Dwbh1If4Nt_7wNPN6o')  # Теперь токен берётся из Environment Variables Render

# ... (весь словарь MODELS остаётся тем же, что был раньше — вставь его сюда полностью)

# Функции scrape_for_year, load_seen, save_seen, check_new_deals остаются теми же

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.message.chat_id
    save_seen(load_seen()['seen_links'], CHAT_ID)
    await update.message.reply_text('Бот запущен! Я буду проверять новые объявления каждые 5 минут и присылать тебе подходящие машины.')

async def best_deals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Проверяю новые объявления вручную...')
    text = await check_new_deals(context.bot)
    if text:
        await update.message.reply_text(text)
    else:
        await update.message.reply_text('Нет новых подходящих объявлений.')

async def check_new_deals(bot):
    # (та же функция, что была раньше — вставь её)

    if all_results and CHAT_ID:
        text = 'Новые подходящие машины:\n\n'
        for res in all_results:
            text += f"🚗 {res['model']} {res['year']}\n{res['title']}\n💰 {res['price']} € (экономия {res['saving']:.0f} €)\n🔗 {res['link']}\n\n"
        await bot.send_message(chat_id=CHAT_ID, text=text)
        return text
    return ''

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('best_deals', best_deals))

    schedule.every(5).minutes.do(lambda: asyncio.create_task(check_new_deals(app.bot)))

    threading.Thread(target=run_scheduler, daemon=True).start()

    print("Бот запущен и работает 24/7!")
    app.run_polling(drop_pending_updates=True)
