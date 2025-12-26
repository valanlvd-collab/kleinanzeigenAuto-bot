import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import re
import json
import os
import asyncio

# Настройки
TOKEN = os.environ.get('TOKEN')
SEEN_FILE = 'seen_offers.json'
CHAT_ID = None

if not TOKEN:
    print("ERROR: TOKEN not found in environment variables!")
    exit(1)

# АКТУАЛИЗИРОВАННЫЙ СПИСОК МОДЕЛЕЙ И ПАРАМЕТРОВ
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
    'Toyota Auris (с 2009)': {
        2009: {'avg': 5500, 'query': 'toyota+auris+2009'},
        2010: {'avg': 6000, 'query': 'toyota+auris+2010'},
        2011: {'avg': 6500, 'query': 'toyota+auris+2011'},
        2012: {'avg': 7500, 'query': 'toyota+auris+2012'},
        2013: {'avg': 8500, 'query': 'toyota+auris+2013'},
        2014: {'avg': 9500, 'query': 'toyota+auris+2014'},
    },
    'Toyota Aygo (с 2009)': {
        2009: {'avg': 3500, 'query': 'toyota+aygo+2009'},
        2010: {'avg': 3800, 'query': 'toyota+aygo+2010'},
        2011: {'avg': 4200, 'query': 'toyota+aygo+2011'},
        2012: {'avg': 4600, 'query': 'toyota+aygo+2012'},
        2013: {'avg': 5000, 'query': 'toyota+aygo+2013'},
        2014: {'avg': 5800, 'query': 'toyota+aygo+2014'},
        2015: {'avg': 6800, 'query': 'toyota+aygo+2015'},
    }
}

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {'seen_links': [], 'chat_id': None}

def save_seen(seen_links, chat_id=None):
    data = load_seen()
    data['seen_links'] = seen_links
    if chat_id: data['chat_id'] = chat_id
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
            # Извлекаем только цифры цены, игнорируя символы валют и ошибки
            price_str = re.sub(r'[^\d]', '', price_elem.get_text()) if price_elem else ''
            try:
                price = float(price_str)
            except: continue

            saving = avg - price
            if saving < 500: continue # Ищем только выгодные сделки

            desc_elem = ad.find('p', class_=lambda x: x and 'description' in x.lower())
            description = (desc_elem.get_text(strip=True) if desc_elem else "").lower()
            full_text = (title + " " + description).lower()

            # ФИЛЬТР ПРОБЕГА: Извлекаем цифры перед "km" или аналогичными сокращениями
            # Позволяет игнорировать грамматические ошибки в написании километража
            km_match = re.search(r'(\d{1,3}[\.,]?\d{3})\s*(?:km|kilom|км)', full_text)
            if km_match:
                km = int(re.sub(r'[^\d]', '', km_match.group(1)))
                if km > 130000: continue # Игнорируем авто с пробегом выше 130к
            
            # Базовая проверка на повреждения
            bad_words = ['unfall', 'defekt', 'bastler', 'schaden', 'beschädigt', 'motorschaden']
            if any(word in full_text for word in bad_words): continue

            results.append({
                'model': model_name, 'year': year, 'title': title,
                'price': price, 'saving': saving, 'link': link
            })
        return results
    except: return []

async def check_new_deals(context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    stored_data = load_seen()
    if not CHAT_ID: CHAT_ID = stored_data.get('chat_id')
    if not CHAT_ID: return

    seen_links = set(stored_data['seen_links'])
    all_results = []
    
    for model, years in MODELS.items():
        for year, year_data in years.items():
            found = scrape_for_year(model, year, year_data)
            for res in found:
                if res['link'] not in seen_links:
                    all_results.append(res)
                    seen_links.add(res['link'])
            await asyncio.sleep(2) # Защита от блокировки (Rate limit)

    save_seen(list(seen_links), CHAT_ID)

    if all_results:
        all_results.sort(key=lambda x: x['saving'], reverse=True)
        for res in all_results[:10]:
            msg = (f"🚗 *{res['model']} ({res['year']})*\n"
                   f"📝 {res['title']}\n"
                   f"💰 Цена: {res['price']:.0f} €\n"
                   f"📈 Выгода: ~{res['saving']:.0f} €\n"
                   f"🔗 [Открыть объявление]({res['link']})")
            await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id
    save_seen(load_seen()['seen_links'], CHAT_ID)
    await update.message.reply_text("Бот запущен! Ищу Toyota и VW (пробег до 130к, выгода от 500€).")

async def manual_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Начинаю поиск новых объявлений...")
    await check_new_deals(context)

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('best_deals', manual_check))

    # Настройка автоматической проверки каждые 5 минут (300 секунд)
    job_queue = app.job_queue
    job_queue.run_repeating(check_new_deals, interval=300, first=10)

    print("Бот запущен и готов к работе...")
    app.run_polling(drop_pending_updates=True)
