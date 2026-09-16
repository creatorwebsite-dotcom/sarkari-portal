import json
import re
from bs4 import BeautifulSoup
from curl_cffi import requests

TARGET_URL = "https://sarkariresult.com.cm/"

def clean(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def run_scraper():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    print("Fetching portal...")
    resp = requests.get(TARGET_URL, headers=headers, impersonate="chrome120", timeout=30)
    if resp.status_code != 200:
        print(f"Failed with status: {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")

    final_data = {
        "trending_boxes": [],
        "latest_jobs": [],
        "results": [],
        "admit_cards": [],
        "answer_keys": [],
        "syllabus": [],
        "admission": []
    }

    # 1. Trending Boxes
    for a in soup.find_all('a'):
        t = clean(a.get_text())
        u = a.get('href', '')
        if not u or u.startswith('#') or 'javascript' in u:
            continue
        low = t.lower()
        if any(w in low for w in ['post', 'form', 'recruitment', 'teacher', 'constable', 'admit card', 'result']):
            if 8 < len(t) < 70 and not any(x['url'] == u for x in final_data['trending_boxes']):
                final_data['trending_boxes'].append({"title": t, "url": u})
        if len(final_data['trending_boxes']) >= 12:
            break

    # 2. Category Blocks Parsing
    blocks = soup.find_all(['div', 'td', 'section'])
    for b in blocks:
        header = b.find(['h1', 'h2', 'h3', 'h4', 'th', 'b', 'strong'])
        if not header:
            continue
        h_text = clean(header.get_text()).lower()

        cat = None
        if 'latest' in h_text or 'job' in h_text:
            cat = 'latest_jobs'
        elif 'result' in h_text:
            cat = 'results'
        elif 'admit' in h_text or 'hall' in h_text:
            cat = 'admit_cards'
        elif 'answer' in h_text or 'key' in h_text:
            cat = 'answer_keys'
        elif 'syllabus' in h_text:
            cat = 'syllabus'
        elif 'admission' in h_text:
            cat = 'admission'

        if cat and len(final_data[cat]) == 0:
            for link in b.find_all('a'):
                title = clean(link.get_text())
                url = link.get('href', '')
                if title and url and len(title) > 4 and not url.startswith('#'):
                    low = title.lower()
                    if low in ['sarkari result', 'sarkariresult', 'view more', 'click here']:
                        continue
                    if not any(item['url'] == url for item in final_data[cat]):
                        final_data[cat].append({"title": title, "url": url})
                if len(final_data[cat]) >= 30:
                    break

    # 3. Dedicated Fallback Search
    for a in soup.find_all('a'):
        t = clean(a.get_text())
        u = a.get('href', '')
        low = t.lower()
        if not u or u.startswith('#') or len(t) < 6:
            continue

        if 'answer key' in low and not any(x['url'] == u for x in final_data['answer_keys']):
            final_data['answer_keys'].append({"title": t, "url": u})
        elif 'syllabus' in low and not any(x['url'] == u for x in final_data['syllabus']):
            final_data['syllabus'].append({"title": t, "url": u})
        elif ('admission' in low or 'entrance' in low) and not any(x['url'] == u for x in final_data['admission']):
            final_data['admission'].append({"title": t, "url": u})

    with open("live_portal_data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print("Success: Generated full JSON!")

if __name__ == "__main__":
    run_scraper()
