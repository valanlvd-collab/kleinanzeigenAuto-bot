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
import asyncio

TOKEN = os.environ.get('TOKEN')

# (весь словарь MODELS вставь полностью — он у тебя есть)
MODELS = {
    'VW Polo 5. Gen. (2009-2017)': {
        2009: {'avg': 4000, 'query': 'volkswagen+polo+2009'},
        2010: {'avg': 4500, 'query': 'volkswagen+polo+2010'},
        2011: {'avg': 5000, 'query': 'volkswagen+polo+2011'},
        2012: {'avg': 5500, 'query': 'volkswagen+polo+2012'},
        2013: {'avg': 6000, 'query': 'volkswagen+polo+2013'},
        2014: {'avg': 6500, 'query': 'volkswagen+polo+2014'},
        2015: {'avg': 7000, 'query': 'volkswagen+polo+2015'},
        2016: {'avg': 7500, 'query': 'volkswagen+polo+2016'},
        2017: {'avg': 8000, 'query': 'volkswagen+polo+2017'},
    },
    'Opel Corsa D (2006-2014)': {
        2006: {'avg': 2000, 'query': 'opel+corsa+d+2006'},
        2007: {'avg': 2500, 'query': 'opel+corsa+d+2007'},
        2008: {'avg': 3000, 'query': 'opel+corsa+d+2008'},
        2009: {'avg': 3500, 'query': 'opel+corsa+d+2009'},
        2010: {'avg': 4000, 'query': 'opel+corsa+d+2010'},
        2011: {'avg': 4500, 'query': 'opel+corsa+d+2011'},
        2012: {'avg': 5000, 'query': 'opel+corsa+d+2012'},
        2013: {'avg': 5500, 'query': 'opel+corsa+d+2013'},
        2014: {'avg': 6000, 'query': 'opel+corsa+d+2014'},
    },
    'Opel Corsa E (2014-2020)': {
        2014: {'avg': 6500, 'query': 'opel+corsa+e+2014'},
        2015: {'avg': 7500, 'query': 'opel+corsa+e+2015'},
        2016: {'avg': 8500, 'query': 'opel+corsa+e+2016'},
        2017: {'avg': 9500, 'query': 'opel+corsa+e+2017'},
        2018: {'avg': 10500, 'query': 'opel+corsa+e+2018'},
        2019: {'avg': 11500, 'query': 'opel+corsa+e+2019'},
        2020: {'avg': 12500, 'query': 'opel+corsa+e+2020'},
    },
    'Ford Fiesta Mk7 (2008-2017)': {
        2008: {'avg': 3000, 'query': 'ford+fiesta+mk7+2008'},
        2009: {'avg': 3500, 'query': 'ford+fiesta+mk7+2009'},
        2010: {'avg': 4000, 'query': 'ford+fiesta+mk7+2010'},
        2011: {'avg': 4500, 'query': 'ford+fiesta+mk7+2011'},
        2012: {'avg': 5000, 'query': 'ford+fiesta+mk7+2012'},
        2013: {'avg': 5500, 'query': 'ford+fiesta+mk7+2013'},
        2014: {'avg': 6000, 'query': 'ford+fiesta+mk7+2014'},
        2015: {'avg': 6500, 'query': 'ford+fiesta+mk7+2015'},
        2016: {'avg': 7000, 'query': 'ford+fiesta+mk7+2016'},
        2017: {'avg': 8000, 'query': 'ford+fiesta+mk7+2017'},
    },
    'Ford Fiesta (2017-2023)': {
        2017: {'avg': 9500, 'query': 'ford+fiesta+2017'},
        2018: {'avg': 10500, 'query': 'ford+fiesta+2018'},
        2019: {'avg': 11500, 'query': 'ford+fiesta+2019'},
        2020: {'avg': 12500, 'query': 'ford+fiesta+2020'},
        2021: {'avg': 14000, 'query': 'ford+fiesta+2021'},
        2022: {'avg': 15500, 'query': 'ford+fiesta+2022'},
        2023: {'avg': 17000, 'query': 'ford+fiesta+2023'},
    },
    'Honda Jazz 3. Gen. (2008-2015)': {
        2008: {'avg': 4000, 'query': 'honda+jazz+2008'},
        2009: {'avg': 4500, 'query': 'honda+jazz+2009'},
        2010: {'avg': 5000, 'query': 'honda+jazz+2010'},
        2011: {'avg': 5500, 'query': 'honda+jazz+2011'},
        2012: {'avg': 6000, 'query': 'honda+jazz+2012'},
        2013: {'avg': 6500, 'query': 'honda+jazz+2013'},
        2014: {'avg': 7000, 'query': 'honda+jazz+2014'},
        2015: {'avg': 8000, 'query': 'honda+jazz+2015'},
    },
    'Honda Jazz 4. Gen. (2015-2020)': {
        2015: {'avg': 9500, 'query': 'honda+jazz+2015'},
        2016: {'avg': 10500, 'query': 'honda+jazz+2016'},
        2017: {'avg': 11500, 'query': 'honda+jazz+2017'},
        2018: {'avg': 12500, 'query': 'honda+jazz+2018'},
        2019: {'avg': 13500, 'query': 'honda+jazz+2019'},
        2020: {'avg': 14500, 'query': 'honda+jazz+2020'},
    },
    'Mazda2 2. Gen. (2007-2014)': {
        2007: {'avg': 3000, 'query': 'mazda2+2007'},
        2008: {'avg': 3500, 'query': 'mazda2+2008'},
        2009: {'avg': 4000, 'query': 'mazda2+2009'},
        2010: {'avg': 4500, 'query': 'mazda2+2010'},
        2011: {'avg': 5000, 'query': 'mazda2+2011'},
        2012: {'avg': 5500, 'query': 'mazda2+2012'},
        2013: {'avg': 6000, 'query': 'mazda2+2013'},
        2014: {'avg': 6500, 'query': 'mazda2+2014'},
    },
    'Mazda2 3. Gen. (2015-2024)': {
        2015: {'avg': 8000, 'query': 'mazda2+2015'},
        2016: {'avg': 9000, 'query': 'mazda2+2016'},
        2017: {'avg': 10000, 'query': 'mazda2+2017'},
        2018: {'avg': 11000, 'query': 'mazda2+2018'},
        2019: {'avg': 12000, 'query': 'mazda2+2019'},
        2020: {'avg': 13000, 'query': 'mazda2+2020'},
        2021: {'avg': 14000, 'query': 'mazda2+2021'},
        2022: {'avg': 15000, 'query': 'mazda2+2022'},
        2023: {'avg': 16000, 'query': 'mazda2+2023'},
        2024: {'avg': 17000, 'query': 'mazda2+2024'},
    },
    'Kia Picanto 1. Gen. (2004-2011)': {
        2004: {'avg': 1500, 'query': 'kia+picanto+2004'},
        2005: {'avg': 1800, 'query': 'kia+picanto+2005'},
        2006: {'avg': 2000, 'query': 'kia+picanto+2006'},
        2007: {'avg': 2200, 'query': 'kia+picanto+2007'},
        2008: {'avg': 2500, 'query': 'kia+picanto+2008'},
        2009: {'avg': 2800, 'query': 'kia+picanto+2009'},
        2010: {'avg': 3200, 'query': 'kia+picanto+2010'},
        2011: {'avg': 3500, 'query': 'kia+picanto+2011'},
    },
    'Kia Picanto 2. Gen. (2011-2017)': {
        2011: {'avg': 5000, 'query': 'kia+picanto+2011'},
        2012: {'avg': 5500, 'query': 'kia+picanto+2012'},
        2013: {'avg': 6000, 'query': 'kia+picanto+2013'},
        2014: {'avg': 6500, 'query': 'kia+picanto+2014'},
        2015: {'avg': 7000, 'query': 'kia+picanto+2015'},
        2016: {'avg': 7500, 'query': 'kia+picanto+2016'},
        2017: {'avg': 8000, 'query': 'kia+picanto+2017'},
    },
    'Kia Picanto 3. Gen. (2017-2024)': {
        2017: {'avg': 9000, 'query': 'kia+picanto+2017'},
        2018: {'avg': 10000, 'query': 'kia+picanto+2018'},
        2019: {'avg': 11000, 'query': 'kia+picanto+2019'},
        2020: {'avg': 12000, 'query': 'kia+picanto+2020'},
        2021: {'avg': 13000, 'query': 'kia+picanto+2021'},
        2022: {'avg': 14000, 'query': 'kia+picanto+2022'},
        2023: {'avg': 15000, 'query': 'kia+picanto+2023'},
        2024: {'avg': 16000, 'query': 'kia+picanto+2024'},
    },
}

# функции scrape_for_year, load_seen, save_seen, check_new_deals — оставь как были

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.message.chat_id
    save_seen(load_seen()['seen_links'], CHAT_ID)
    await update.message.reply_text('Бот запущен! Я проверяю новые объявления каждые 5 минут и присылаю тебе только подходящие машины.')

async def best_deals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Проверяю вручную...')
    text = await check_new_deals(context.bot)
    if text:
        await update.message.reply_text(text)
    else:
        await update.message.reply_text('Нет новых подходящих объявлений.')

async def check_new_deals(bot):
    # (та же функция)
    # в конце вместо await bot.send_message используй:
    if all_results and CHAT_ID:
        text = 'Новые подходящие машины:\n\n'
        for res in all_results:
            text += f"🚗 {res['model']} {res['year']}\n{res['title']}\n💰 {res['price']} € (экономия {res['saving']:.0f} €)\n🔗 {res['link']}\n\n"
        await bot.send_message(chat_id=CHAT_ID, text=text)
        return text
    return ''

def run_scheduler():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    if not TOKEN:
        print("ERROR: TOKEN not found in environment variables!")
        exit(1)

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('best_deals', best_deals))

    # Автоматическая проверка каждые 5 минут
    schedule.every(5).minutes.do(lambda: asyncio.create_task(check_new_deals(app.bot)))

    # Запуск scheduler в отдельном потоке
    threading.Thread(target=run_scheduler, daemon=True).start()

    print("Бот запущен и работает 24/7!")
    app.run_polling(drop_pending_updates=True)
