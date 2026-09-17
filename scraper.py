import json
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

SPAM_KEYWORDS = ['meditation', 'whatsapp', 'telegram', 'tools', 'disclaimer', 'contact us', 'crack exam']

def clean_title(text):
    if not text:
        return ""
    text = re.sub(r'sarkari\s*result', 'Sarkari Naukar', text, flags=re.IGNORECASE)
    text = re.sub(r'govtjobalert', 'Sarkari Naukar', text, flags=re.IGNORECASE)
    return " ".join(text.split()).strip()

def is_valid_title(t):
    low = (t or "").lower()
    if len(low) < 5:
        return False
    return not any(w in low for w in SPAM_KEYWORDS)

def detect_meta(title):
    t = title.lower()
    state = "all"
    job = "other"

    if any(k in t for k in ['up ', 'upsssc', 'uppsc', 'uttar pradesh']): state = 'up'
    elif any(k in t for k in ['bihar', 'bpsc', 'bssc']): state = 'bihar'
    elif any(k in t for k in ['delhi', 'dsssb']): state = 'delhi'
    elif any(k in t for k in ['rajasthan', 'rpsc']): state = 'rajasthan'
    elif any(k in t for k in ['mp ', 'mppsc']): state = 'mp'

    if any(k in t for k in ['police', 'constable', 'si ', 'army', 'defence']): job = 'police'
    elif any(k in t for k in ['teacher', 'tet', 'pgt', 'tgt', 'prt']): job = 'teacher'
    elif any(k in t for k in ['railway', 'rrb', 'rrc', 'alp', 'ntpc']): job = 'railway'
    elif any(k in t for k in ['bank', 'ibps', 'sbi', 'rbi']): job = 'bank'
    elif 'ssc' in t: job = 'ssc'
    elif 'upsc' in t: job = 'upsc'

    return state, job

def scrape_sources():
    dataset = {
        "trending_boxes": [],
        "latest_jobs": [],
        "results": [],
        "admit_cards": [],
        "answer_keys": [],
        "syllabus": [],
        "admission": []
    }
    seen = set()
    sources = ['https://sarkariresult.com.cm/', 'https://www.govtjobalert.in/']

    for url in sources:
        try:
            res = requests.get(url, headers=HEADERS, timeout=12)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, 'html.parser')

            for b in soup.find_all(['div', 'td', 'section'], class_=re.compile(r'(col|card|box|panel)', re.I)):
                head = b.find(['h1', 'h2', 'h3', 'h4', 'th', 'b', 'strong'])
                if not head:
                    continue
                htxt = head.get_text().lower()

                target_key = None
                if 'job' in htxt or 'vacancy' in htxt: target_key = 'latest_jobs'
                elif 'result' in htxt and 'admit' not in htxt: target_key = 'results'
                elif 'admit' in htxt or 'hall' in htxt: target_key = 'admit_cards'
                elif 'key' in htxt: target_key = 'answer_keys'
                elif 'syllabus' in htxt: target_key = 'syllabus'
                elif 'admission' in htxt: target_key = 'admission'

                if target_key:
                    for a in b.find_all('a'):
                        t = clean_title(a.get_text())
                        if is_valid_title(t) and t not in seen:
                            seen.add(t)
                            st, jb = detect_meta(t)
                            dataset[target_key].append({
                                "title": t,
                                "state": st,
                                "job": jb,
                                "dates": "<li>• Application Status: <strong>Active Notice</strong></li><li>• Last Date: <strong>Check Official Notice</strong></li>",
                                "fee": "<li>• General / OBC: <strong>₹ 100/-</strong></li><li>• SC / ST / Female: <strong>₹ 0/-</strong></li>",
                                "eligibility": "Passed 10th / 12th / Degree from recognized board or university.",
                                "apply": "https://ssc.gov.in/",
                                "notification": "https://ssc.gov.in/",
                                "official": "https://ssc.gov.in/"
                            })
        except Exception:
            pass

    dataset["trending_boxes"] = dataset["latest_jobs"][:6]

    with open('live_portal_data.json', 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    scrape_sources()
