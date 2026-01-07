import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import re
import json
import os
import asyncio
import http.server
import socketserver
import threading

# --- RENDER DUMMY SERVER ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Dummy server started on port {port}")
        httpd.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

TOKEN = os.environ.get('TOKEN')
SEEN_FILE = 'seen_offers.json'
CHAT_ID = None

if not TOKEN:
    print("ERROR: TOKEN not found!")
    exit(1)

# ПОЛНЫЙ СПИСОК (С учетом VW up! и Seat)
MODELS = {
    'VW Polo (2009-2017)': {y: {'avg': 4000+(i*500), 'query': f'volkswagen+polo+{y}'} for i, y in enumerate(range(2009, 2018))},
    'VW up! (2011-2017)': {y: {'avg': 4500+(i*600), 'query': f'volkswagen+up+{y}'} for i, y in enumerate(range(2011, 2018))},
    'Seat Ibiza (2008-2017)': {y: {'avg': 3500+(i*650), 'query': f'seat+ibiza+{y}'} for i, y in enumerate(range(2008, 2018))},
    'Seat Mii (2011-2017)': {y: {'avg': 4000+(i*600), 'query': f'seat+mii+{y}'} for i, y in enumerate(range(2011, 2018))},
    'Mazda 3 (2007-2017)': {y: {'avg': 4500+(i*750), 'query': f'mazda+3+{y}'} for i, y in enumerate(range(2007, 2018))},
    'Opel Corsa D/E (2007-2017)': {y: {'avg': 3000+(i*600), 'query': f'opel+corsa+{y}'} for i, y in enumerate(range(2007, 2018))},
    'Ford Fiesta (2008-2017)': {y: {'avg': 3500+(i*600), 'query': f'ford+fiesta+{y}'} for i, y in enumerate(range(2008, 2018))},
    'Toyota Auris (2007-2017)': {y: {'avg': 5500+(i*600), 'query': f'toyota+auris+{y}'} for i, y in enumerate(range(2007, 2018))},
    'Toyota Aygo (2007-2017)': {y: {'avg': 3000+(i*400), 'query': f'toyota+aygo+{y}'} for i, y in enumerate(range(2007, 2018))},
    'Honda Jazz (2008-2017)': {y: {'avg': 4500+(i*600), 'query': f'honda+jazz+{y}'} for i, y in enumerate(range(2008, 2018))}
}

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, 'r') as f: return json.load(f)
        except: pass
    return {'seen_links': [], 'chat_id': None}

def save_seen(seen_links, chat_id=None):
    data = load_seen()
    data['seen_links'] = seen_links
    if chat_id: data['chat_id'] = chat_id
    with open(SEEN_FILE, 'w') as f: json.dump(data, f)

def scrape_for_year(model_name, year, data):
    url = f'https://www.kleinanzeigen.de/s-anbieter:privat/autos/{data["query"]}/k0c216'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Accept-Language': 'de-DE,de;q=0.9'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200: return []
        soup = BeautifulSoup(response.text, 'html.parser')
        ads = soup.find_all('li', class_=lambda x: x and 'ad-listitem' in x)
        results = []
        for ad in ads:
            title_elem = ad.find('a', class_='ellipsis')
            if not title_elem: continue
            title, link = title_elem.get_text(strip=True), 'https://www.kleinanzeigen.de' + title_elem['href']
            price_elem = ad.find('p', class_=lambda x: x and 'price' in x.lower())
            price_str = re.sub(r'[^\d]', '', price_elem.get_text()) if price_elem else ''
            try: price = float(price_str)
            except: continue
            if (data['avg'] - price) < 500: continue
            
            desc = (ad.find('p', class_=lambda x: x and 'description' in x.lower()).get_text(strip=True) if ad.find('p', class_=lambda x: x and 'description' in x.lower()) else "").lower()
            full_text = (title + " " + desc).lower()
            
            km_found = None
            km_match = re.search(r'(\d{1,3}[\.,]?\d{3})\s*(?:km|км|kilom)', full_text)
            tkm_match = re.search(r'(\d{2,3})\s*tkm', full_text)
            if km_match: km_found = int(re.sub(r'[^\d]', '', km_match.group(1)))
            elif tkm_match: km_found = int(tkm_match.group(1)) * 1000
            
            if km_found is None or km_found > 130000: continue
            if any(word in full_text for word in ['unfall', 'defekt', 'bastler', 'schaden', 'beschädigт', 'motorschaden']): continue
            
            results.append({'model': model_name, 'year': year, 'title': f"{title} [{km_found} km]", 'price': price, 'saving': data['avg'] - price, 'link': link})
        return results
    except: return []

async def check_new_deals(context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    stored = load_seen()
    if not CHAT_ID: CHAT_ID = stored.get('chat_id')
    if not CHAT_ID: return
    seen_links = set(stored['seen_links'])
    all_results = []
    for model, years in MODELS.items():
        for year, year_data in years.items():
            found = scrape_for_year(model, year, year_data)
            for res in found:
                if res['link'] not in seen_links:
                    all_results.append(res)
                    seen_links.add(res['link'])
            await asyncio.sleep(7) # Увеличил паузу до 7 сек из-за объема
    save_seen(list(seen_links), CHAT_ID)
    if all_results:
        all_results.sort(key=lambda x: x['saving'], reverse=True)
        for res in all_results[:10]:
            msg = f"🚗 *{res['model']} ({res['year']})*\n📝 {res['title']}\n💰 {res['price']:.0f} € (Выгода ~{res['saving']:.0f} €)\n🔗 [Link]({res['link']})"
            await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id
    save_seen(load_seen()['seen_links'], CHAT_ID)
    await update.message.reply_text("Бот обновлен! Ищу Mazda 3, Seat, VW up! и др. до 130к пробега.")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.job_queue.run_repeating(check_new_deals, interval=1800, first=10) # Раз в 30 минут
    app.run_polling(drop_pending_updates=True)
