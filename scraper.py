import json
import re
from bs4 import BeautifulSoup
from curl_cffi import requests

TARGET_URL = "https://sarkariresult.com.cm/"

def clean(t):
    return re.sub(r'\s+', ' ', t or '').strip()

def is_junk(t, u):
    low = (t + " " + u).lower()
    junk = ['whatsapp', 'telegram', 'meditation', 'tools', 'youtube', 'facebook', 'click here', 'crack exam']
    return any(w in low for w in junk) or len(t) < 5

def run():
    res = requests.get(TARGET_URL, headers={"User-Agent": "Mozilla/5.0"}, impersonate="chrome120", timeout=30)
    if res.status_code != 200:
        return

    soup = BeautifulSoup(res.text, "html.parser")
    feed = {
        "trending_boxes": [],
        "latest_jobs": [],
        "results": [],
        "admit_cards": [],
        "answer_keys": [],
        "syllabus": [],
        "admission": []
    }

    categories = {
        'results': ['result'],
        'admit_cards': ['admit card', 'hall ticket'],
        'latest_jobs': ['latest job', 'latest jobs', 'online form'],
        'answer_keys': ['answer key'],
        'syllabus': ['syllabus'],
        'admission': ['admission']
    }

    for box in soup.find_all(['div', 'td', 'table', 'section']):
        h = box.find(['h1', 'h2', 'h3', 'h4', 'th', 'b', 'strong'])
        if not h:
            continue
        txt = clean(h.get_text()).lower()

        cat = None
        for k, v in categories.items():
            if any(w in txt for w in v):
                if k == 'results' and 'answer' in txt:
                    continue
                cat = k
                break

        if cat and len(feed[cat]) == 0:
            for a in box.find_all('a'):
                title = clean(a.get_text())
                url = a.get('href', '')
                if not url or url.startswith('#') or is_junk(title, url):
                    continue
                if not any(x['url'] == url for x in feed[cat]):
                    feed[cat].append({"title": title, "url": url})
                if len(feed[cat]) >= 35:
                    break

    # Top 6 Trending Forms (Direct clean recruitment links)
    if feed['latest_jobs']:
        feed['trending_boxes'] = [{"title": x['title'], "url": x['url']} for x in feed['latest_jobs'][:6]]

    with open("live_portal_data.json", "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run()
