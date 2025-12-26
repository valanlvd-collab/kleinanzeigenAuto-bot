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

if not TOKEN:
    print("ERROR: TOKEN not found in environment variables!")
    exit(1)

MODELS = {
    'VW Polo 5. Gen. (2009-2017)': {
        2009: {'avg': 4500, 'query': 'volkswagen+polo+2009'},
        2010: {'avg': 5000, 'query': 'volkswagen+polo+2010'},
        2011: {'avg': 5500, 'query': 'volkswagen+polo+2011'},
        2012: {'avg': 6000, 'query': 'volkswagen+polo+2012'},
        2013: {'avg': 6500, 'query': 'volkswagen+polo+2013'},
        2014: {'avg': 7000, 'query': 'volkswagen+polo+2014'},
        2015: {'avg': 8000, 'query': 'volkswagen+polo+2015'},
        2016: {'avg': 9000, 'query': 'volkswagen+polo+2016'},
        2017: {'avg': 10000, 'query': 'volkswagen+polo+2017'},
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
        2014: {'avg': 7000, 'query': 'opel+corsa+e+2014'},
        2015: {'avg': 7500, 'query': 'opel+corsa+e+2015'},
        2016: {'avg': 8000, 'query': 'opel+corsa+e+2016'},
        2017: {'avg': 9000, 'query': 'opel+corsa+e+2017'},
        2018: {'avg': 10000, 'query': 'opel+corsa+e+2018'},
        2019: {'avg': 11000, 'query': 'opel+corsa+e+2019'},
        2020: {'avg': 12000, 'query': 'opel+corsa+e+2020'},
    },
    'Ford Fiesta Mk7 (2008-2017)': {
        2008: {'avg': 4000, 'query': 'ford+fiesta+mk7+2008'},
        2009: {'avg': 4500, 'query': 'ford+fiesta+mk7+2009'},
        2010: {'avg': 5000, 'query': 'ford+fiesta+mk7+2010'},
        2011: {'avg': 5500, 'query': 'ford+fiesta+mk7+2011'},
        2012: {'avg': 6000, 'query': 'ford+fiesta+mk7+2012'},
        2013: {'avg': 6500, 'query': 'ford+fiesta+mk7+2013'},
        2014: {'avg': 7000, 'query': 'ford+fiesta+mk7+2014'},
        2015: {'avg': 7500, 'query': 'ford+fiesta+mk7+2015'},
        2016: {'avg': 8000, 'query': 'ford+fiesta+mk7+2016'},
        2017: {'avg': 9000, 'query': 'ford+fiesta+mk7+2017'},
    },
    'Ford Fiesta (2017-2023)': {
        2017: {'avg': 10000, 'query': 'ford+fiesta+2017'},
        2018: {'avg': 11000, 'query': 'ford+fiesta+2018'},
        2019: {'avg': 12000, 'query': 'ford+fiesta+2019'},
        2020: {'avg': 13000, 'query': 'ford+fiesta+2020'},
        2021: {'avg': 14000, 'query': 'ford+fiesta+2021'},
        2022: {'avg': 15000, 'query': 'ford+fiesta+2022'},
        2023: {'avg': 16000, 'query': 'ford+fiesta+2023'},
    },
    'Ford Focus (2009-2018)': {
        2009: {'avg': 4500, 'query': 'ford+focus+2009'},
        2010: {'avg': 5000, 'query': 'ford+focus+2010'},
        2011: {'avg': 5500, 'query': 'ford+focus+2011'},
        2012: {'avg': 6000, 'query': 'ford+focus+2012'},
        2013: {'avg': 6500, 'query': 'ford+focus+2013'},
        2014: {'avg': 7000, 'query': 'ford+focus+2014'},
        2015: {'avg': 8000, 'query': 'ford+focus+2015'},
        2016: {'avg': 9000, 'query': 'ford+focus+2016'},
        2017: {'avg': 10000, 'query': 'ford+focus+2017'},
        2018: {'avg': 11000, 'query': 'ford+focus+2018'},
    },
    'Honda Jazz 3. Gen. (2008-2015)': {
        2008: {'avg': 4000, 'query': 'honda+jazz+2008'},
        2009: {'avg': 4500, 'query': 'honda+jazz+2009'},
        2010: {'avg': 5000, 'query': 'honda+jazz+2010'},
        2011: {'avg': 5500, 'query': 'honda+jazz+2011'},
        2012: {'avg': 6000, 'query': 'honda+jazz+2012'},
        2013: {'avg': 6500, 'query': 'honda+jazz+2013'},
        2014: {'avg': 7000, 'query': 'honda+jazz+2014'},
        2015: {'avg': 7500, 'query': 'honda+jazz+2015'},
    },
    'Honda Jazz 4. Gen. (2015-2020)': {
        2015: {'avg': 8000, 'query': 'honda+jazz+2015'},
        2016: {'avg': 9000, 'query': 'honda+jazz+2016'},
        2017: {'avg': 10000, 'query': 'honda+jazz+2017'},
        2018: {'avg': 11000, 'query': 'honda+jazz+2018'},
        2019: {'avg': 12000, 'query': 'honda+jazz+2019'},
        2020: {'avg': 13000, 'query': 'honda+jazz+2020'},
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
        2015: {'avg': 7000, 'query': 'mazda2+2015'},
        2016: {'avg': 7500, 'query': 'mazda2+2016'},
        2017: {'avg': 8000, 'query': 'mazda2+2017'},
        2018: {'avg': 8500, 'query': 'mazda2+2018'},
        2019: {'avg': 9000, 'query': 'mazda2+2019'},
        2020: {'avg': 9500, 'query': 'mazda2+2020'},
        2021: {'avg': 10000, 'query': 'mazda2+2021'},
        2022: {'avg': 10500, 'query': 'mazda2+2022'},
        2023: {'avg': 11000, 'query': 'mazda2+2023'},
        2024: {'avg': 11500, 'query': 'mazda2+2024'},
    },
    'Kia Picanto 1. Gen. (2004-2011)': {
        2004: {'avg': 2000, 'query': 'kia+picanto+2004'},
        2005: {'avg': 2500, 'query': 'kia+picanto+2005'},
        2006: {'avg': 3000, 'query': 'kia+picanto+2006'},
        2007: {'avg': 3500, 'query': 'kia+picanto+2007'},
        2008: {'avg': 4000, 'query': 'kia+picanto+2008'},
        2009: {'avg': 4500, 'query': 'kia+picanto+2009'},
        2010: {'avg': 5000, 'query': 'kia+picanto+2010'},
        2011: {'avg': 5500, 'query': 'kia+picanto+2011'},
    },
    'Kia Picanto 2. Gen. (2011-2017)': {
        2011: {'avg': 5500, 'query': 'kia+picanto+2011'},
        2012: {'avg': 6000, 'query': 'kia+picanto+2012'},
        2013: {'avg': 6500, 'query': 'kia+picanto+2013'},
        2014: {'avg': 7000, 'query': 'kia+picanto+2014'},
        2015: {'avg': 7500, 'query': 'kia+picanto+2015'},
        2016: {'avg': 8000, 'query': 'kia+picanto+2016'},
        2017: {'avg': 8500, 'query': 'kia+picanto+2017'},
    },
    'Kia Picanto 3. Gen. (2017-2024)': {
        2017: {'avg': 8500, 'query': 'kia+picanto+2017'},
        2018: {'avg': 9000, 'query': 'kia+picanto+2018'},
        2019: {'avg': 9500, 'query': 'kia+picanto+2019'},
        2020: {'avg': 10000, 'query': 'kia+picanto+2020'},
        2021: {'avg': 10500, 'query': 'kia+picanto+2021'},
        2022: {'avg': 11000, 'query': 'kia+picanto+2022'},
        2023: {'avg': 11500, 'query': 'kia+picanto+2023'},
        2024: {'avg': 12000, 'query': 'kia+picanto+2024'},
    },
    'Toyota Auris (2009-2019)': {
        2009: {'avg': 4500, 'query': 'toyota+auris+2009'},
        2010: {'avg': 5000, 'query': 'toyota+auris+2010'},
        2011: {'avg': 5500, 'query': 'toyota+auris+2011'},
        2012: {'avg': 6000, 'query': 'toyota+auris+2012'},
        2013: {'avg': 6500, 'query': 'toyota+auris+2013'},
        2014: {'avg': 7000, 'query': 'toyota+auris+2014'},
        2015: {'avg': 8000, 'query': 'toyota+auris+2015'},
        2016: {'avg': 9000, 'query': 'toyota+auris+2016'},
        2017: {'avg': 10000, 'query': 'toyota+auris+2017'},
        2018: {'avg': 11000, 'query': 'toyota+auris+2018'},
        2019: {'avg': 12000, 'query': 'toyota+auris+2019'},
    },
    'Toyota Aygo (2009-2021)': {
        2009: {'avg': 3500, 'query': 'toyota+aygo+2009'},
        2010: {'avg': 4000, 'query': 'toyota+aygo+2010'},
        2011: {'avg': 4500, 'query': 'toyota+aygo+2011'},
        2012: {'avg': 5000, 'query': 'toyota+aygo+2012'},
        2013: {'avg': 5500, 'query': 'toyota+aygo+2013'},
        2014: {'avg': 6000, 'query': 'toyota+aygo+2014'},
        2015: {'avg': 6500, 'query': 'toyota+aygo+2015'},
        2016: {'avg': 7000, 'query': 'toyota+aygo+2016'},
        2017: {'avg': 7500, 'query': 'toyota+aygo+2017'},
        2018: {'avg': 8000, 'query': 'toyota+aygo+2018'},
        2019: {'avg': 8500, 'query': 'toyota+aygo+2019'},
        2020: {'avg': 9000, 'query': 'toyota+aygo+2020'},
        2021: {'avg': 9500, 'query': 'toyota+aygo+2021'},
    },
}

SEEN_FILE = 'seen_offers.json'
CHAT_ID = None

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, 'r') as f:
            return json.load(f)
    return {'seen_links': [], 'chat_id': None}

def save_seen(seen_links, chat_id=None):
    data = load_seen()
    data['seen_links'] = seen_links
    if chat_id:
        data['chat_id'] = chat_id
    with open(SEEN_FILE, 'w') as f:
        json.dump(data, f)

def scrape_for_year(model_name, year, data):
    url = f'https://www.kleinanzeigen.de/s-anbieter:privat/autos/{data["query"]}/k0c216'
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    ads = soup.find_all('li', class_=lambda x: x and 'ad-listitem' in x)

    results = []
    avg = data['avg']
    for ad in ads:
        title_elem = ad.find('a', class_='ellipsis')
        if not title_elem: continue
        title = title_elem.get_text(strip=True)
        link = 'https://www.kleinanzeigen.de' + title_elem['href']

        price_elem = ad.find('p', class_=lambda x: x and 'price' in x.lower())
        price_str = price_elem.get_text(strip=True).replace('€', '').replace('.', '').replace('-', '').strip() if price_elem else ''
        try:
            price = float(price_str)
        except:
            continue

        saving = avg - price
        if saving < 500: continue

        desc = ad.find('p', class_=lambda x: x and 'description' in x.lower())
        description = (desc.get_text(strip=True) + title).lower() if desc else title.lower()

        bad_words = ['unfall', 'defekt', 'bastler', 'reparatur', 'schaden', 'beschädigt', 'tüv abgelaufen']
        if any(word in description for word in bad_words): continue

        km_match = re.search(r'\b(\d{1,3}(?:[.,]\d{3})*)\s*km\b', description + title)
        if km_match:
            km = int(km_match.group(1).replace('.', '').replace(',', ''))
            if km > 130000: continue

        if 'tüv' not in description and 'hu' not in description: continue

        year_match = re.search(r'\b(20\d{2})\b', description + title)
        if not year_match or int(year_match.group(0)) != year: continue

        results.append({
            'model': model_name,
            'year': year,
            'title': title,
            'price': price,
            'saving': saving,
            'link': link
        })

    return results

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
    data = load_seen()
    seen_links = set(data['seen_links'])
    all_results = []
    for model, years in MODELS.items():
        for year, year_data in years.items():
            results = scrape_for_year(model, year, year_data)
            for res in results:
                if res['link'] not in seen_links:
                    all_results.append(res)
                    seen_links.add(res['link'])

    save_seen(list(seen_links))

    if all_results and CHAT_ID:
        text = 'Новые подходящие машины:\n\n'
        all_results.sort(key=lambda x: x['saving'], reverse=True)
        for res in all_results[:15]:
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
