from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import re

TARGET_URL = "https://sarkariresult.com.cm/"

def clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()

def run_scraper():
    session = requests.Session(impersonate="chrome120")
    res = session.get(TARGET_URL, timeout=30)
    
    if res.status_code != 200:
        print(f"Error fetching: {res.status_code}")
        return

    soup = BeautifulSoup(res.content, 'html.parser')
    feed = {
        "trending_boxes": [],
        "latest_jobs": [],
        "results": [],
        "admit_cards": [],
        "answer_keys": [],
        "syllabus": [],
        "admission": []
    }

    # Top Trending Boxes
    for a in soup.find_all('a', href=True):
        txt = clean(a.get_text())
        href = a['href']
        if txt and href and ('Post' in txt or 'Form' in txt or 'Exam' in txt) and 6 < len(txt) < 60:
            if not href.startswith('http'):
                href = f"https://sarkariresult.com.cm/{href.lstrip('/')}"
            if not any(x['url'] == href for x in feed['trending_boxes']):
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
