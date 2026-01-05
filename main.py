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

# --- OPTIMIERTER RENDER HEALTH-CHECK SERVER ---
# Dieser Teil sorgt dafür, dass Render den Bot nicht wegen Inaktivität abschaltet.
class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running...")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
        print(f"✅ Render Health-Check aktiv auf Port {port}")
        httpd.serve_forever()

# Startet den Web-Server in einem separaten Thread
threading.Thread(target=run_dummy_server, daemon=True).start()

# --- KONFIGURATION ---
TOKEN = os.environ.get('TOKEN')
SEEN_FILE = 'seen_offers.json'
CHAT_ID = None

if not TOKEN:
    print("❌ FEHLER: Kein TOKEN in den Umgebungsvariablen gefunden!")
    exit(1)

# --- DEINE VOLLSTÄNDIGE MODELL-LISTE ---
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

# --- FUNKTIONEN ---
def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {'seen_links': [], 'chat_id': None}

def save_seen(seen_links, chat_id=None):
    data = load_seen()
    data['seen_links'] = list(seen_links)
    if chat_id: data['chat_id'] = chat_id
    with open(SEEN_FILE, 'w') as f:
        json.dump(data, f)

def scrape_for_year(model_name, year, data):
    url = f'https://www.kleinanzeigen.de/s-anbieter:privat/autos/{data["query"]}/k0c216'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept-Language': 'de-DE,de;q=0.9',
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200: return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        ads = soup.find_all('li', class_=lambda x: x and 'ad-listitem' in x)
        results = []
        
        for ad in ads:
            title_elem = ad.find('a', class_='ellipsis')
            if not title_elem: continue
            title = title_elem.get_text(strip=True)
            link = 'https://www.kleinanzeigen.de' + title_elem['href']

            price_elem = ad.find('p', class_=lambda x: x and 'price' in x.lower())
            price_str = re.sub(r'[^\d]', '', price_elem.get_text()) if price_elem else ''
            try:
                price = float(price_str)
            except: continue
            
            saving = data['avg'] - price
            if saving < 500: continue

            desc_elem = ad.find('p', class_=lambda x: x and 'description' in x.lower())
            description = (desc_elem.get_text(strip=True) if desc_elem else "").lower()
            full_text = (title + " " + description).lower()
            
            km_found = None
            km_match = re.search(r'(\d{1,3}[\.,]?\d{3})\s*(?:km|км|kilom)', full_text)
            tkm_match = re.search(r'(\d{2,3})\s*tkm', full_text)
            
            if km_match:
                km_found = int(re.sub(r'[^\d]', '', km_match.group(1)))
            elif tkm_match:
                km_found = int(tkm_match.group(1)) * 1000
            
            if km_found is None or km_found > 130000:
                continue

            bad_words = ['unfall', 'defekt', 'bastler', 'schaden', 'beschädigт', 'motorschaden', 'getriebeschaden']
            if any(word in full_text for word in bad_words): continue

            results.append({
                'model': model_name, 'year': year, 'title': f"{title} [{km_found} km]",
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
    
    print("🔎 Suche nach neuen Angeboten...")
    for model, years in MODELS.items():
        for year, year_data in years.items():
            found = scrape_for_year(model, year, year_data)
            for res in found:
                if res['link'] not in seen_links:
                    all_results.append(res)
                    seen_links.add(res['link'])
            await asyncio.sleep(2) # Kurze Pause gegen Bot-Sperre

    save_seen(list(seen_links), CHAT_ID)
    
    if all_results:
        all_results.sort(key=lambda x: x['saving'], reverse=True)
        for res in all_results[:10]:
            msg = (f"🚗 *{res['model']} ({res['year']})*\n"
                   f"📝 {res['title']}\n"
                   f"💰 Цена: {res['price']:.0f} € (Выгода ~{res['saving']:.0f} €)\n"
                   f"🔗 [Открыть на сайте]({res['link']})")
            await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id
    save_seen(load_seen()['seen_links'], CHAT_ID)
    await update.message.reply_text("✅ Бот запущен! Ищу машины (VW, Opel, Ford, Honda, Mazda, Kia) до 130.000 км. Каждые 10 минут проверяю новые объявления.")

# --- HAUPTPROGRAMM ---
if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler('start', start))
    
    # Job Queue: Suchlauf alle 10 Minuten (600 Sekunden)
    if application.job_queue:
        application.job_queue.run_repeating(check_new_deals, interval=600, first=10)
    
    print("🚀 Telegram Bot wird gestartet...")
    application.run_polling(drop_pending_updates=True)
