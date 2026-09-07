import requests
import csv
import json
from datetime import datetime
from bs4 import BeautifulSoup

# PUT YOUR APIFY TOKEN HERE
APIFY_TOKEN = "apify_api_l2iSfxruKZ9Hht4WlU1vHMtce0lWfe35g5Lp"

# --- Step 1: Get today's date ---
today = datetime.now().strftime("%Y-%m-%d")
filename = f"today_sellers_{today}.csv"

all_sellers = []

# --- Step 2: Scrape PropertyPro ---
print(f"Scraping sellers for {today}...")
pp_actor = "gio21~propertypro-ng-scraper"
pp_url = f"https://api.apify.com/v2/acts/{pp_actor}/run-sync-get-dataset-items?token={APIFY_TOKEN}"
pp_payload = {"startUrls": ["https://propertypro.ng/property-for-sale/house"], "maxItems": 5}

try:
    response = requests.post(pp_url, json=pp_payload, timeout=180)
    data = response.json()
    
    if isinstance(data, list):
        print(f"Found {len(data)} listings from PropertyPro.")
        for item in data:
            link = item.get('url', 'N/A')
            phone = "N/A"
            price = "N/A"
            
            # Extract phone from link if available
            if "phone=" in link:
                try:
                    phone = link.split('phone=')[1].split('&')[0]
                except:
                    phone = "N/A"
            
            # Try to scrape the page to get price (Simple approach)
            try:
                page = requests.get(link, timeout=10)
                soup = BeautifulSoup(page.text, 'html.parser')
                # Look for price in typical HTML tags
                price_tag = soup.find(class_='price') or soup.find(itemprop='price')
                if price_tag:
                    price = price_tag.get_text(strip=True)
            except:
                pass

            all_sellers.append({
                "source": "propertypro",
                "type": "listing",
                "phone": phone,
                "price": price,
                "details": item.get('title', 'N/A'),
                "link": link,
                "date": today
            })
    else:
        print(f"PropertyPro error: {data}")
except Exception as e:
    print(f"PropertyPro Error: {e}")


# --- Step 3: Scrape NPC ---
print("Scraping NPC...")
npc_actor = "crawlerbros~nigeria-property-centre-scraper"
npc_url = f"https://api.apify.com/v2/acts/{npc_actor}/run-sync-get-dataset-items?token={APIFY_TOKEN}"
npc_payload = {"mode": "search", "listingType": "for-sale", "propertyType": "houses", "state": "any", "maxItems": 5}

try:
    response = requests.post(npc_url, json=npc_payload, timeout=180)
    data = response.json()
    
    if isinstance(data, list):
        print(f"Found {len(data)} listings from NPC.")
        for item in data:
            link = item.get('listingUrl') or item.get('url', 'N/A')
            phone = item.get('phone', 'N/A')
            price = item.get('price', 'N/A') # NPC actor often provides this directly
            
            all_sellers.append({
                "source": "npc",
                "type": "listing",
                "phone": phone,
                "price": price,
                "details": item.get('title', 'N/A'),
                "link": link,
                "date": today
            })
    else:
        print(f"NPC error: {data}")
except Exception as e:
    print(f"NPC Error: {e}")


# --- Step 4: Save ---
if all_sellers:
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=["source", "type", "phone", "price", "details", "link", "date"])
        writer.writeheader()
        writer.writerows(all_sellers)
    print(f"DONE! Saved {len(all_sellers)} sellers to {filename}")
else:
    print("No sellers found.")
