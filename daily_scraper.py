import requests
from bs4 import BeautifulSoup
import csv
import re
import time
from datetime import datetime

# ============================================================
# MASTER PROPERTY SCRAPER
# PropertyPro + NPC + Nairaland
# ============================================================

APIFY_TOKEN = "apify_api_l2iSfxruKZ9Hht4WlU1vHMtce0lWfe35g5Lp"

today = datetime.now().strftime("%Y-%m-%d")
filename = f"today_sellers_{today}.csv"

all_sellers = []

# ============================================================
# 1. PROPERTYPRO (Apify)
# ============================================================
print(f"[{today}] 1. SCRAPING PROPERTYPRO...")
try:
    pp_url = f"https://api.apify.com/v2/acts/gio21~propertypro-ng-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    r = requests.post(pp_url, json={"startUrls": ["https://propertypro.ng/property-for-sale/house"], "maxItems": 30}, timeout=180)
    data = r.json()
    if isinstance(data, list) and len(data) > 0:
        print(f"   PropertyPro: {len(data)} listings")
        for item in data:
            phone = "N/A"
            link = item.get('url', 'N/A')
            if "phone=" in link:
                try: phone = link.split('phone=')[1].split('&')[0]
                except: pass
            all_sellers.append({
                "source": "propertypro", "city": "Nigeria", "type": "sale",
                "title": item.get('title', 'N/A'), "price": item.get('price', 'N/A'),
                "size": "Unknown", "phone": phone, "link": link, "date": today
            })
    else:
        print(f"   PropertyPro: empty response")
except Exception as e:
    print(f"   PropertyPro error: {str(e)[:100]}")

# ============================================================
# 2. NIGERIA PROPERTY CENTRE (Apify)
# ============================================================
print(f"[{today}] 2. SCRAPING NPC...")
try:
    npc_url = f"https://api.apify.com/v2/acts/crawlerbros~nigeria-property-centre-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    r = requests.post(npc_url, json={"mode": "search", "listingType": "for-sale", "propertyType": "houses", "state": "any", "maxItems": 30}, timeout=180)
    data = r.json()
    if isinstance(data, list) and len(data) > 0:
        print(f"   NPC: {len(data)} listings")
        for item in data:
            all_sellers.append({
                "source": "npc", "city": item.get('state', 'Nigeria'), "type": "sale",
                "title": item.get('title', 'N/A'), "price": item.get('price', 'N/A'),
                "size": "Unknown", "phone": item.get('phone', 'N/A'),
                "link": item.get('listingUrl') or item.get('url', 'N/A'), "date": today
            })
    else:
        print(f"   NPC: empty response")
except Exception as e:
    print(f"   NPC error: {str(e)[:100]}")

# ============================================================
# 3. NAIRALAND
# ============================================================
print(f"[{today}] 3. SCRAPING NAIRALAND...")
try:
    headers_nl = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    queries = [
        "house for sale lagos", "apartment abuja", "land for sale ibadan",
        "flat lagos rent", "property port harcourt", "commercial land lagos",
        "land for sale ibeju lekki", "land for sale ikorodu"
    ]
    nl_count = 0
    seen_nl = set()
    for query in queries:
        url = f"https://www.nairaland.com/search?q={query.replace(' ', '+')}&section=properties"
        try:
            response = requests.get(url, headers=headers_nl, timeout=8)
            if response.status_code != 200: continue
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True)
                if href.startswith('/') and len(href) > 10:
                    parts = href.split('/')
                    if len(parts) >= 2 and parts[1].isdigit() and len(parts[1]) >= 6:
                        if href in seen_nl: continue
                        seen_nl.add(href)
                        if len(text) < 20 or text.startswith('Re:'): continue
                        all_url = "https://www.nairaland.com" + href
                        
                        phone = "See Post"
                        price = "See Post"
                        size_str = "Unknown"
                        try:
                            post_r = requests.get(all_url, headers=headers_nl, timeout=6)
                            if post_r.status_code == 200:
                                post_soup = BeautifulSoup(post_r.text, 'html.parser')
                                post_text = post_soup.get_text()
                                phones = re.findall(r'\b(0[789][01]\d{8})\b', post_text)
                                if phones: phone = phones[0]
                                prices = re.findall(r'(?:N|₦|NGN)\s*([\d,]{6,})', post_text)
                                if prices: price = f"₦{prices[0]}"
                                sizes = re.findall(r'(\d{3,5})\s*(?:sqm|sq\.?\s*m|square\s*meters?)', post_text, re.IGNORECASE)
                                if sizes: size_str = f"{max(int(s) for s in sizes)} sqm"
                        except: pass
                        
                        all_sellers.append({
                            "source": "nairaland", "city": "Nigeria", "type": "listing",
                            "title": text[:200], "price": price, "size": size_str,
                            "phone": phone, "link": all_url, "date": today
                        })
                        nl_count += 1
        except: pass
        time.sleep(0.5)
    print(f"   Nairaland: {nl_count} posts")
except Exception as e:
    print(f"   Nairaland error: {str(e)[:100]}")

# ============================================================
# SAVE EVERYTHING
# ============================================================
print(f"\n[{today}] SAVING...")
with open(filename, 'w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=["source", "city", "type", "title", "price", "size", "phone", "link", "date"])
    writer.writeheader()
    writer.writerows(all_sellers)

print(f"DONE! Saved {len(all_sellers)} listings to {filename}")

# Summary
sources = {}
for s in all_sellers:
    sources[s['source']] = sources.get(s['source'], 0) + 1
print("\nSummary by source:")
for source, count in sorted(sources.items(), key=lambda x: -x[1]):
    print(f"  {source}: {count} listings")
