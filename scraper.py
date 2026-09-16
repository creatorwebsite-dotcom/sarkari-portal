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
    resp = requests.get(TARGET_URL, headers=headers, impersonate="chrome120", timeout=25)
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

    # 1. Top Trending Boxes
    for a in soup.find_all('a'):
        t = clean(a.get_text())
        u = a.get('href', '')
        if not u or u.startswith('#') or 'javascript' in u:
            continue
        if any(w in t.lower() for w in ['post', 'form', 'recruitment', 'teacher', 'constable', 'admit card', 'result']):
            if 8 < len(t) < 70 and not any(x['url'] == u for x in final_data['trending_boxes']):
                final_data['trending_boxes'].append({"title": t, "url": u})
        if len(final_data['trending_boxes']) >= 12:
            break

    # 2. Block/Table Based Category Parsing
    blocks = soup.find_all(['div', 'td', 'section'])
    for b in blocks:
        heading = b.find(['h1', 'h2', 'h3', 'h4', 'th', 'b', 'strong'])
        if not heading:
            continue
        h_text = clean(heading.get_text()).lower()

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

    # 3. Dedicated Fallback Search (Answer Key, Syllabus, Admission)
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

    # Save to complete JSON
    with open("live_portal_data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print("Success: live_portal_data.json generated with all categories!")

if __name__ == "__main__":
    run_scraper()            if not any(x['url'] == href for x in feed['trending_boxes']):
                feed['trending_boxes'].append({"title": txt, "url": href})

    # All 6 Categories
    blocks = soup.find_all(['div', 'table', 'td'])
    for b in blocks:
        head = b.find(['h1', 'h2', 'h3', 'h4', 'th', 'b'])
        if not head:
            continue
        h = clean(head.get_text()).lower()
        key = None

        if 'result' in h and not feed['results']:
            key = 'results'
        elif 'admit' in h and not feed['admit_cards']:
            key = 'admit_cards'
        elif ('job' in h or 'recruitment' in h) and not feed['latest_jobs']:
            key = 'latest_jobs'
        elif 'answer key' in h and not feed['answer_keys']:
            key = 'answer_keys'
        elif 'syllabus' in h and not feed['syllabus']:
            key = 'syllabus'
        elif 'admission' in h and not feed['admission']:
            key = 'admission'

        if key:
            for a in b.find_all('a', href=True):
                t = clean(a.get_text())
                href = a['href']
                if t and href and len(t) > 4 and not href.startswith('#'):
                    if not href.startswith('http'):
                        href = f"https://sarkariresult.com.cm/{href.lstrip('/')}"
                    feed[key].append({"title": t, "url": href})

    with open('live_portal_data.json', 'w', encoding='utf-8') as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)
    print("Success! Generated live_portal_data.json")

if __name__ == "__main__":
    run_scraper()
