import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import re
import json
import os
import asyncio

TOKEN = os.environ.get('TOKEN')

if not TOKEN:
    print("ERROR: TOKEN not found in environment variables!")
    exit(1)

# Данные моделей (оставил как в твоем скрипте)
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
    # ... остальные модели (оставь свой список здесь без изменений) ...
}

SEEN_FILE = 'seen_offers.json'
CHAT_ID = None

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
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
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
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

            km_match = re.search(r'\b(\d{1,3}(?:[.,]\d{3})*)\s*km\b', description)
            if km_match:
                km = int(km_match.group(1).replace('.', '').replace(',', ''))
                if km > 130000: continue

            if 'tüv' not in description and 'hu' not in description: continue

            year_match = re.search(r'\b(20\d{2})\b', description)
            if not year_match or int(year_match.group(0)) != year: continue

            results.append({
                'model': model_name, 'year': year, 'title': title,
                'price': price, 'saving': saving, 'link': link
            })
        return results
    except Exception as e:
        print(f"Scraping error: {e}")
        return []

async def check_new_deals(context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    data = load_seen()
    
    # Если CHAT_ID еще не определен, пробуем взять его из файла
    if not CHAT_ID:
        CHAT_ID = data.get('chat_id')
    
    if not CHAT_ID:
        return

    seen_links = set(data['seen_links'])
    all_results = []
    
    for model, years in MODELS.items():
        for year, year_data in years.items():
            results = scrape_for_year(model, year, year_data)
            for res in results:
                if res['link'] not in seen_links:
                    all_results.append(res)
                    seen_links.add(res['link'])
            await asyncio.sleep(1) # Небольшая пауза, чтобы не забанили

    save_seen(list(seen_links), CHAT_ID)

    if all_results:
        all_results.sort(key=lambda x: x['saving'], reverse=True)
        for res in all_results[:10]:
            text = (f"🚗 *{res['model']} {res['year']}*\n"
                    f"{res['title']}\n"
                    f"💰 *{res['price']:.0f} €* (ниже рынка на {res['saving']:.0f} €)\n"
                    f"🔗 {res['link']}")
            await context.bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id
    save_seen(load_seen()['seen_links'], CHAT_ID)
    await update.message.reply_text('Бот запущен! Проверяю объявления каждые 5 минут.')

async def manual_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Запускаю проверку вручную...')
    await check_new_deals(context)

if __name__ == '__main__':
    # В новых версиях JobQueue требует наличия установленного пакета `python-telegram-bot[job-queue]`
    # Но так как мы обновили версию, всё должно работать через Application
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('best_deals', manual_check))

    # Настройка JobQueue для циклической проверки
    job_queue = app.job_queue
    # Интервал 300 секунд (5 минут)
    job_queue.run_repeating(check_new_deals, interval=300, first=10)

    print("Бот запущен...")
    app.run_polling(drop_pending_updates=True)
