import json
import re
from bs4 import BeautifulSoup
from curl_cffi import requests

TARGET_URL = "https://sarkariresult.com.cm/"

def clean(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def is_junk(title, url):
    low = (title + " " + url).lower()
    junk = [
        'whatsapp', 'telegram', 'meditation', 'tools', 'youtube',
        'facebook', 'twitter', 'instagram', 'contact', 'disclaimer',
        'privacy policy', 'sarkari result', 'sarkariresult', 'view more',
        'click here', 'crack exams'
    ]
    return any(w in low for w in junk) or len(title) < 5

def detect_state(text):
    low = text.lower()
    states = {
        'up': ['up ', 'uttar pradesh', 'upsssc', 'uppsc', 'up police'],
        'bihar': ['bihar', 'bpsc', 'bssc'],
        'delhi': ['delhi', 'dsssb'],
        'rajasthan': ['rajasthan', 'rpsc', 'rsmssb'],
        'mp': ['mp ', 'madhya pradesh', 'mppsc', 'vyapam'],
        'central': ['ssc', 'upsc', 'railway', 'rrb', 'ibps', 'nta', 'army', 'navy', 'airforce']
    }
    for st, keys in states.items():
        if any(k in low for k in keys):
            return st
    return 'central'

def detect_job_type(text):
    low = text.lower()
    if any(k in low for k in ['police', 'constable', 'si ', 'army', 'navy', 'airforce', 'defence', 'nda', 'cds']):
        return 'police-defence'
    if any(k in low for k in ['teacher', 'tgt', 'pgt', 'prt', 'tet', 'ctet', 'school']):
        return 'teaching'
    if any(k in low for k in ['bank', 'ibps', 'sbi', 'rbi']):
        return 'banking'
    if any(k in low for k in ['railway', 'rrb', 'ntpc']):
        return 'railway'
    if any(k in low for k in ['ssc', 'upsc', 'clerk', 'officer', 'assistant']):
        return 'civil'
    return 'other'

def run_scraper():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    print("Fetching site...")
    resp = requests.get(TARGET_URL, headers=headers, impersonate="chrome120", timeout=30)
    if resp.status_code != 200:
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    data = {
        "trending_boxes": [],
        "latest_jobs": [],
        "results": [],
        "admit_cards": [],
        "answer_keys": [],
        "syllabus": [],
        "admission": []
    }

    # 1. Top 6 Trending Forms (Strict Form Filtering)
    for a in soup.find_all('a'):
        t = clean(a.get_text())
        u = a.get('href', '')
        if not u or u.startswith('#') or is_junk(t, u):
            continue
        low = t.lower()
        if any(w in low for w in ['form', 'post', 'recruitment', 'bharti', 'online form']) and not any(k in low for k in ['admit', 'result', 'key']):
            if 8 < len(t) < 65 and not any(x['url'] == u for x in data['trending_boxes']):
                data['trending_boxes'].append({"title": t, "url": u})
        if len(data['trending_boxes']) >= 6:
            break

    # 2. Extract Category Sections
    for block in soup.find_all(['div', 'td', 'table', 'section']):
        head = block.find(['h1', 'h2', 'h3', 'h4', 'th', 'b', 'strong'])
        if not head:
            continue
        htxt = clean(head.get_text()).lower()
        cat = None

        if 'result' in htxt and 'answer' not in htxt:
            cat = 'results'
        elif 'admit' in htxt or 'hall ticket' in htxt:
            cat = 'admit_cards'
        elif 'latest' in htxt or ('job' in htxt and 'answer' not in htxt):
            cat = 'latest_jobs'
        elif 'answer' in htxt or 'key' in htxt:
            cat = 'answer_keys'
        elif 'syllabus' in htxt:
            cat = 'syllabus'
        elif 'admission' in htxt:
            cat = 'admission'

        if cat and len(data[cat]) == 0:
            for link in block.find_all('a'):
                lt = clean(link.get_text())
                lu = link.get('href', '')
                if not lu or lu.startswith('#') or is_junk(lt, lu):
                    continue
                if not any(it['url'] == lu for it in data[cat]):
                    data[cat].append({
                        "title": lt,
                        "url": lu,
                        "state": detect_state(lt),
                        "job_type": detect_job_type(lt)
                    })
                if len(data[cat]) >= 40:
                    break

    with open("live_portal_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Generated live_portal_data.json successfully")

if __name__ == "__main__":
    run_scraper()
