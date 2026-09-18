import os
import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

DATABASE_FILE = 'jobs_database.json'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 1. DATABASE LOAD & SAVE
def load_existing_database():
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_database(data):
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 2. SMART TITLE NORMALIZATION & STOPWORDS CLEANER
STOPWORDS = {
    'online', 'form', 'recruitment', 'vacancy', 'bharti', 'post', 'posts', 
    'apply', '2025', '2026', '2027', 'notification', 'check', 'download',
    'various', 'admit', 'card', 'result', 'exam', 'date', 're-open', 'latest'
}

def clean_and_tokenize(title):
    words = re.findall(r'[a-zA-Z0-9]+', title.lower())
    meaningful_words = {w for w in words if w not in STOPWORDS and len(w) > 1}
    return meaningful_words

# 3. CONFLICT CHECKER (TOKEN SIMILARITY MATCHER)
def find_matching_existing_key(new_title, db):
    new_tokens = clean_and_tokenize(new_title)
    if not new_tokens:
        return None

    for existing_key, existing_data in db.items():
        existing_title = existing_data.get('title', existing_key)
        existing_tokens = clean_and_tokenize(existing_title)

        # Intersection ratio (Jaccard similarity on core exam keywords)
        common = new_tokens.intersection(existing_tokens)
        if len(common) >= 2:
            match_score = len(common) / min(len(new_tokens), len(existing_tokens))
            if match_score >= 0.60:  # 60% se zyada core tokens match
                return existing_key
    return None

# 4. DEEP DETAILS SCRAPER (SAME POST PARSER)
def extract_post_full_details(post_url, category_name, source_domain):
    try:
        r = requests.get(post_url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
    except:
        return None

    soup = BeautifulSoup(r.text, 'html.parser')
    page_text = soup.get_text()

    details = {
        'url': post_url,
        'category': category_name,
        'source': source_domain,
        'important_dates': {},
        'application_fee': {},
        'age_limit': {},
        'vacancy_details': [],
        'eligibility': [],
        'physical_standards': {},
        'selection_mode': [],
        'action_links': {
            'apply_online': '',
            'download_notification': '',
            'official_website': '',
            'admit_card': '',
            'answer_key': '',
            'result': ''
        }
    }

    title_el = soup.find('h1') or soup.find('h2')
    details['title'] = title_el.get_text(strip=True) if title_el else 'New Job Vacancy'

    # Important Dates
    date_patterns = [
        ('apply_start', r'Online Apply Start Date\s*:\s*([^\n\r]+)'),
        ('apply_last', r'Online Apply Last Date\s*:\s*([^\n\r]+)'),
        ('fee_last', r'(?:Last Date for Fee Payment|Pay Exam Fee Last Date)\s*:\s*([^\n\r]+)'),
        ('correction_last', r'Correction Last Date\s*:\s*([^\n\r]+)'),
        ('exam_date', r'(?:Exam Date|Pre Exam Date)\s*:\s*([^\n\r]+)'),
        ('admit_card_date', r'(?:Admit Card Release|Pre Admit Card)\s*:\s*([^\n\r]+)'),
        ('result_date', r'(?:Result Date|Pre Result Date)\s*:\s*([^\n\r]+)')
    ]
    for key, pat in date_patterns:
        m = re.search(pat, page_text, re.IGNORECASE)
        if m:
            details['important_dates'][key] = m.group(1).strip()

    # Application Fee
    fee_patterns = [
        ('gen_obc_ews', r'(?:General,\s*OBC,\s*EWS|For General / Other State)\s*:\s*([^\n\r]+)'),
        ('sc_st_ph', r'(?:SC\s*/\s*ST|SC\s*,\s*ST\s*,\s*PH)\s*:\s*([^\n\r]+)'),
        ('portal_charge', r'Portal Charge Extra\s*:\s*([^\n\r]+)')
    ]
    for key, pat in fee_patterns:
        m = re.search(pat, page_text, re.IGNORECASE)
        if m:
            details['application_fee'][key] = m.group(1).strip()

    # Age Limits
    age_patterns = [
        ('min_age', r'Minimum Age\s*:\s*([^\n\r]+)'),
        ('max_age', r'Maximum Age\s*:\s*([^\n\r]+)'),
        ('relaxation', r'Age Relaxation\s*:\s*([^\n\r]+)')
    ]
    for key, pat in age_patterns:
        m = re.search(pat, page_text, re.IGNORECASE)
        if m:
            details['age_limit'][key] = m.group(1).strip()

    # Vacancy & Eligibility Tables
    for table in soup.find_all('table'):
        t_text = table.get_text()
        if 'Post Name' in t_text or 'Eligibility' in t_text:
            for tr in table.find_all('tr'):
                cols = [td.get_text(separator=' ', strip=True) for td in tr.find_all(['td', 'th'])]
                if len(cols) >= 2 and not any(h in cols[0] for h in ['Post Name', 'Total']):
                    details['vacancy_details'].append(cols)

    # Action Links
    for a in soup.find_all('a', href=True):
        link_href = urljoin(post_url, a['href'].strip())
        link_text = (a.get_text() or '').lower()
        parent_row = a.find_parent('tr')
        row_label = (parent_row.get_text() if parent_row else '').lower()
        full_context = f"{link_text} {row_label}"

        if 'apply' in full_context and not details['action_links']['apply_online']:
            details['action_links']['apply_online'] = link_href
        elif 'notification' in full_context and not details['action_links']['download_notification']:
            details['action_links']['download_notification'] = link_href
        elif ('official website' in full_context or 'esb.mp.gov' in link_href) and not details['action_links']['official_website']:
            details['action_links']['official_website'] = link_href
        elif 'admit' in full_context and not details['action_links']['admit_card']:
            details['action_links']['admit_card'] = link_href
        elif 'answer key' in full_context and not details['action_links']['answer_key']:
            details['action_links']['answer_key'] = link_href
        elif 'result' in full_context and not details['action_links']['result']:
            details['action_links']['result'] = link_href

    return details

# 5. EXECUTION ENGINE (NO-CONFLICT SEQUENTIAL PROCESSING)
def run_master_scraper():
    db = load_existing_database()
    new_jobs_counter = 0

    sources = [
        {'name': 'Rojgar Result', 'base': 'https://rojgarresult.com/', 'url': 'https://rojgarresult.com/'},
        {'name': 'Sarkari Result', 'base': 'https://sarkariresult.com.cm/', 'url': 'https://sarkariresult.com.cm/'},
        {'name': 'Free Job Alert', 'base': 'https://www.freejobalert.com/', 'url': 'https://www.freejobalert.com/latest-notifications/'}
    ]

    for src in sources:
        print(f"Checking {src['name']}...")
        try:
            res = requests.get(src['url'], headers=HEADERS, timeout=12)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, 'html.parser')

            for a in soup.find_all('a', href=True):
                title = a.get_text(strip=True)
                if len(title) < 12:
                    continue

                # Conflict Check: Check if this post already exists from a previous site
                existing_match_key = find_matching_existing_key(title, db)

                if existing_match_key:
                    # CONFLICT DETECTED: Post already saved from earlier website. Skip complete rewrite!
                    print(f"⏩ [SKIP DUPLICATE] '{title}' already captured as '{db[existing_match_key]['title']}'")
                    continue

                # Unique post: Extract & Save
                full_post_url = urljoin(src['base'], a['href'])
                post_data = extract_post_full_details(full_post_url, 'Latest Jobs', src['name'])

                if post_data and post_data.get('title'):
                    key_id = re.sub(r'[^a-zA-Z0-9]', '', post_data['title'])[:30].lower()
                    db[key_id] = post_data
                    new_jobs_counter += 1
                    print(f"✅ [{src['name']}] Added New: {post_data['title']}")

        except Exception as e:
            print(f"Error on {src['name']}: {e}")

    save_database(db)
    print(f"Done! Added {new_jobs_counter} unique posts without any conflict.")

if __name__ == '__main__':
    run_master_scraper()
