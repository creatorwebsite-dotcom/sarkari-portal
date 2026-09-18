import os
import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

DATABASE_FILE = 'jobs_database.json'
PDF_STORAGE_DIR = 'downloads/pdfs'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Folder create karna agar exist na kare
os.makedirs(PDF_STORAGE_DIR, exist_ok=True)

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

STOPWORDS = {
    'online', 'form', 'recruitment', 'vacancy', 'bharti', 'post', 'posts', 
    'apply', '2025', '2026', '2027', 'notification', 'check', 'download',
    'various', 'admit', 'card', 'result', 'exam', 'date', 'latest'
}

def clean_and_tokenize(title):
    words = re.findall(r'[a-zA-Z0-9]+', title.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 1}

def find_matching_existing_key(new_title, db):
    new_tokens = clean_and_tokenize(new_title)
    if not new_tokens:
        return None
    for existing_key, existing_data in db.items():
        existing_tokens = clean_and_tokenize(existing_data.get('title', existing_key))
        common = new_tokens.intersection(existing_tokens)
        if len(common) >= 2:
            if len(common) / min(len(new_tokens), len(existing_tokens)) >= 0.60:
                return existing_key
    return None

# ACTUAL FILE DOWNLOADER FUNCTION
def download_and_store_file(file_url, post_slug, file_type):
    """
    Real file download karta hai aur repo ke downloads/pdfs folder me store karta hai.
    Returns: local relative file path
    """
    if not file_url or not file_url.startswith('http'):
        return None
    
    clean_slug = re.sub(r'[^a-zA-Z0-9_]', '_', post_slug)[:30]
    filename = f"{clean_slug}_{file_type}.pdf"
    filepath = os.path.join(PDF_STORAGE_DIR, filename)

    # Agar file pehle se downloaded hai to dobara download nahi karega
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1024:
        return filepath

    try:
        res = requests.get(file_url, headers=HEADERS, timeout=20, stream=True)
        # Verify agar server ne sach me PDF ya file deliver ki
        if res.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in res.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Khali ya corrupt file check
            if os.path.getsize(filepath) > 1024:
                print(f"📥 Downloaded Real File: {filepath}")
                return filepath
            else:
                os.remove(filepath)
    except Exception as e:
        print(f"File download failed for {file_url}: {e}")
    
    return None

# DEEP DETAILS & ATTACHMENT EXTRACTION
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
        },
        'stored_files': {
            'notification_pdf': '',
            'result_pdf': '',
            'answer_key_pdf': ''
        }
    }

    title_el = soup.find('h1') or soup.find('h2')
    details['title'] = title_el.get_text(strip=True) if title_el else 'New Job Vacancy'
    post_slug = re.sub(r'[^a-zA-Z0-9]', '_', details['title']).lower()

    # Dates, Fee, Age Patterns
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

    fee_patterns = [
        ('gen_obc_ews', r'(?:General,\s*OBC,\s*EWS|For General / Other State)\s*:\s*([^\n\r]+)'),
        ('sc_st_ph', r'(?:SC\s*/\s*ST|SC\s*,\s*ST\s*,\s*PH)\s*:\s*([^\n\r]+)'),
        ('portal_charge', r'Portal Charge Extra\s*:\s*([^\n\r]+)')
    ]
    for key, pat in fee_patterns:
        m = re.search(pat, page_text, re.IGNORECASE)
        if m:
            details['application_fee'][key] = m.group(1).strip()

    age_patterns = [
        ('min_age', r'Minimum Age\s*:\s*([^\n\r]+)'),
        ('max_age', r'Maximum Age\s*:\s*([^\n\r]+)'),
        ('relaxation', r'Age Relaxation\s*:\s*([^\n\r]+)')
    ]
    for key, pat in age_patterns:
        m = re.search(pat, page_text, re.IGNORECASE)
        if m:
            details['age_limit'][key] = m.group(1).strip()

    # Tables Extraction
    for table in soup.find_all('table'):
        t_text = table.get_text()
        if 'Post Name' in t_text or 'Eligibility' in t_text:
            for tr in table.find_all('tr'):
                cols = [td.get_text(separator=' ', strip=True) for td in tr.find_all(['td', 'th'])]
                if len(cols) >= 2 and not any(h in cols[0] for h in ['Post Name', 'Total']):
                    details['vacancy_details'].append(cols)

    # ACTION LINKS & DIRECT FILE GRABBING
    for a in soup.find_all('a', href=True):
        link_href = urljoin(post_url, a['href'].strip())
        link_text = (a.get_text() or '').lower()
        parent_row = a.find_parent('tr')
        row_label = (parent_row.get_text() if parent_row else '').lower()
        full_ctx = f"{link_text} {row_label}"

        # 1. Apply Online
        if 'apply' in full_ctx and not details['action_links']['apply_online']:
            details['action_links']['apply_online'] = link_href

        # 2. Official Notification (Link + Real PDF Download)
        elif 'notification' in full_ctx and not details['action_links']['download_notification']:
            details['action_links']['download_notification'] = link_href
            # Real file download trigger
            saved_path = download_and_store_file(link_href, post_slug, 'notification')
            if saved_path:
                details['stored_files']['notification_pdf'] = saved_path

        # 3. Official Website
        elif ('official website' in full_ctx or 'esb.mp.gov' in link_href) and not details['action_links']['official_website']:
            details['action_links']['official_website'] = link_href

        # 4. Admit Card
        elif 'admit' in full_ctx and not details['action_links']['admit_card']:
            details['action_links']['admit_card'] = link_href

        # 5. Answer Key (Link + PDF if available)
        elif 'answer key' in full_ctx and not details['action_links']['answer_key']:
            details['action_links']['answer_key'] = link_href
            if link_href.endswith('.pdf'):
                saved_path = download_and_store_file(link_href, post_slug, 'answer_key')
                if saved_path:
                    details['stored_files']['answer_key_pdf'] = saved_path

        # 6. Result (Link + PDF if available)
        elif 'result' in full_ctx and not details['action_links']['result']:
            details['action_links']['result'] = link_href
            if link_href.endswith('.pdf'):
                saved_path = download_and_store_file(link_href, post_slug, 'result')
                if saved_path:
                    details['stored_files']['result_pdf'] = saved_path

    return details

# MULTI-SOURCE SCRAPER EXECUTION
def run_master_scraper():
    db = load_existing_database()
    new_counter = 0

    sources = [
        {'name': 'Rojgar Result', 'base': 'https://rojgarresult.com/', 'url': 'https://rojgarresult.com/'},
        {'name': 'Sarkari Result', 'base': 'https://sarkariresult.com.cm/', 'url': 'https://sarkariresult.com.cm/'},
        {'name': 'Free Job Alert', 'base': 'https://www.freejobalert.com/', 'url': 'https://www.freejobalert.com/latest-notifications/'}
    ]

    for src in sources:
        try:
            res = requests.get(src['url'], headers=HEADERS, timeout=12)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, 'html.parser')

            for a in soup.find_all('a', href=True):
                title = a.get_text(strip=True)
                if len(title) < 12:
                    continue

                existing_key = find_matching_existing_key(title, db)
                if existing_key:
                    continue

                full_url = urljoin(src['base'], a['href'])
                post_data = extract_post_full_details(full_url, 'Latest Jobs', src['name'])

                if post_data and post_data.get('title'):
                    key_id = re.sub(r'[^a-zA-Z0-9]', '', post_data['title'])[:30].lower()
                    db[key_id] = post_data
                    new_counter += 1
                    print(f"✅ Added: {post_data['title']}")

        except Exception as e:
            print(f"Error scraping {src['name']}: {e}")

    save_database(db)
    print(f"Finished! Total new posts added with files: {new_counter}")

if __name__ == '__main__':
    run_master_scraper()
