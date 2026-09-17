import json
import re
from bs4 import BeautifulSoup
from curl_cffi import requests

TARGET_URL = "https://sarkariresult.com.cm/"

def clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()

def is_junk(text, url):
    low = (text + " " + url).lower()
    junk = ['whatsapp', 'telegram', 'meditation', 'tools', 'youtube', 'facebook', 'twitter', 'click here', 'view more', 'crack exam', 'disclaimer', 'contact']
    return any(w in low for w in junk) or len(text) < 5

def detect_state(text):
    low = text.lower()
    mapping = {
        'up': ['up ', 'upsssc', 'uppsc', 'uttar pradesh'],
        'bihar': ['bihar', 'bpsc', 'bssc'],
        'delhi': ['delhi', 'dsssb'],
        'rajasthan': ['rajasthan', 'rpsc', 'rsmssb'],
        'mp': ['mp ', 'mppsc', 'vyapam']
    }
    for st, keys in mapping.items():
        if any(k in low for k in keys):
            return st
    return 'central'

def detect_job(text):
    low = text.lower()
    if any(k in low for k in ['police', 'constable', 'si ', 'army', 'navy', 'defence']):
        return 'police-defence'
    if any(k in low for k in ['teacher', 'tgt', 'pgt', 'tet', 'ctet']):
        return 'teaching'
    if any(k in low for k in ['bank', 'ibps', 'sbi', 'rbi']):
        return 'banking'
    if any(k in low for k in ['railway', 'rrb']):
        return 'railway'
    return 'civil'

def run():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    res = requests.get(TARGET_URL, headers=headers, impersonate="chrome120", timeout=30)
    if res.status_code != 200:
        print("Fetch failed")
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

    # Strict Heading Matching
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
        
        assigned_cat = None
        for cat, match_keys in categories.items():
            if any(k in txt for k in match_keys):
                if cat == 'results' and 'answer' in txt:
                    continue
                assigned_cat = cat
                break

        if assigned_cat and len(feed[assigned_cat]) == 0:
            for a in box.find_all('a'):
                title = clean(a.get_text())
                url = a.get('href', '')
                if not url or url.startswith('#') or is_junk(title, url):
                    continue
                if not any(x['url'] == url for x in feed[assigned_cat]):
                    feed[assigned_cat].append({
                        "title": title,
                        "url": url,
                        "state": detect_state(title),
                        "job_type": detect_job(title)
                    })
                if len(feed[assigned_cat]) >= 30:
                    break

    # Fallback to make sure Admit Card and others never stay empty
    for a in soup.find_all('a'):
        t = clean(a.get_text())
        u = a.get('href', '')
        if not u or u.startswith('#') or is_junk(t, u):
            continue
        low = (t + " " + u).lower()
        if ('admit' in low or 'hall' in low) and len(feed['admit_cards']) < 20:
            if not any(x['url'] == u for x in feed['admit_cards']):
                feed['admit_cards'].append({"title": t, "url": u, "state": detect_state(t), "job_type": detect_job(t)})
        elif ('answer-key' in low or 'answer key' in low) and len(feed['answer_keys']) < 20:
            if not any(x['url'] == u for x in feed['answer_keys']):
                feed['answer_keys'].append({"title": t, "url": u, "state": detect_state(t), "job_type": detect_job(t)})
        elif 'syllabus' in low and len(feed['syllabus']) < 20:
            if not any(x['url'] == u for x in feed['syllabus']):
                feed['syllabus'].append({"title": t, "url": u, "state": detect_state(t), "job_type": detect_job(t)})
        elif 'admission' in low and len(feed['admission']) < 20:
            if not any(x['url'] == u for x in feed['admission']):
                feed['admission'].append({"title": t, "url": u, "state": detect_state(t), "job_type": detect_job(t)})

    # Top 6 Trending Cards strictly from Clean Latest Jobs
    if feed['latest_jobs']:
        feed['trending_boxes'] = [{"title": x['title'], "url": x['url']} for x in feed['latest_jobs'][:6]]

    with open("live_portal_data.json", "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)

    print("Success: JSON generated!")

if __name__ == "__main__":
    run()
