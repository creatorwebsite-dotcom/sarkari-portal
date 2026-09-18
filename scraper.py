import os
import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

DATABASE_FILE = 'jobs_database.json'
PDF_STORAGE_DIR = 'downloads/pdfs'

os.makedirs(PDF_STORAGE_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

def load_existing_database():
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
        except Exception as e:
            print(f"DB load warning: {e}")
            return {}
    return {}

def save_database(data):
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Successfully saved {len(data)} posts into {DATABASE_FILE}")

def clean_text(txt):
    return re.sub(r'\s+', ' ', txt).strip() if txt else ''

def download_and_store_file(file_url, post_slug, file_type):
    if not file_url or not file_url.startswith('http'):
        return None
    
    clean_slug = re.sub(r'[^a-zA-Z0-9_]', '_', post_slug)[:30]
    filename = f"{clean_slug}_{file_type}.pdf"
    filepath = os.path.join(PDF_STORAGE_DIR, filename)

    if os.path.exists(filepath) and os.path.getsize(filepath) > 1024:
        return filepath

    try:
        res = requests.get(file_url, headers=HEADERS, timeout=20, stream=True)
        if res.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in res.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            if os.path.getsize(filepath) > 1024:
                print(f"📥 Downloaded Real File: {filepath}")
                return filepath
            else:
                os.remove(filepath)
    except Exception as e:
        print(f"File download failed for {file_url}: {e}")
    
    return None

def extract_post_full_details(post_url, category_name, source_domain):
    try:
        session = requests.Session()
        r = session.get(post_url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"⚠️ Page error ({r.status_code}): {post_url}")
            return None
    except Exception as err:
        print(f"⚠️ Request failed for {post_url}: {err}")
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
    details['title'] = clean_text(title_el.get_text()) if title_el else 'Government Job Vacancy'
    post_slug = re.sub(r'[^a-zA-Z0-9]', '_', details['title']).lower()

    date_patterns = [
        ('apply_start', r'(?:Online Apply Start Date|Application Begin)\s*:\s*([^\n\r<]+)'),
        ('apply_last', r'(?:Online Apply Last Date|Last Date for Apply Online)\s*:\s*([^\n\r<]+)'),
        ('fee_last', r'(?:Last Date for Fee Payment|Pay Exam Fee Last Date)\s*:\s*([^\n\r<]+)'),
        ('correction_last', r'Correction Last Date\s*:\s*([^\n\r<]+)'),
        ('exam_date', r'(?:Exam Date|Pre Exam Date)\s*:\s*([^\n\r<]+)'),
        ('admit_card_date', r'(?:Admit Card Release|Admit Card Available)\s*:\s*([^\n\r<]+)'),
        ('result_date', r'(?:Result Date|Pre Result Date)\s*:\s*([^\n\r<]+)')
    ]
    for key, pat in date_patterns:
        m = re.search(pat, page_text, re.IGNORECASE)
        if m:
            details['important_dates'][key] = clean_text(m.group(1))

    fee_patterns = [
        ('gen_obc_ews', r'(?:General,\s*OBC,\s*EWS|General\s*/\s*Other\s*State)\s*:\s*([^\n\r<]+)'),
        ('sc_st_ph', r'(?:SC\s*/\s*ST|SC\s*,\s*ST\s*,\s*PH)\s*:\s*([^\n\r<]+)'),
        ('portal_charge', r'Portal Charge Extra\s*:\s*([^\n\r<]+)')
    ]
    for key, pat in fee_patterns:
        m = re.search(pat, page_text, re.IGNORECASE)
        if m:
            details['application_fee'][key] = clean_text(m.group(1))

    age_patterns = [
        ('min_age', r'Minimum Age\s*:\s*([^\n\r<]+)'),
        ('max_age', r'Maximum Age\s*:\s*([^\n\r<]+)'),
        ('relaxation', r'Age Relaxation\s*:\s*([^\n\r<]+)')
    ]
    for key, pat in age_patterns:
        m = re.search(pat, page_text, re.IGNORECASE)
        if m:
            details['age_limit'][key] = clean_text(m.group(1))

    for table in soup.find_all('table'):
        t_text = table.get_text()
        if 'Post Name' in t_text or 'Eligibility' in t_text:
            for tr in table.find_all('tr'):
                cols = [clean_text(td.get_text()) for td in tr.find_all(['td', 'th'])]
                if len(cols) >= 2 and not any(h in cols[0] for h in ['Post Name', 'Total']):
                    details['vacancy_details'].append(cols)

    for a in soup.find_all('a', href=True):
        link_href = urljoin(post_url, a['href'].strip())
        link_text = clean_text(a.get_text()).lower()
        parent_row = a.find_parent('tr')
        row_label = clean_text(parent_row.get_text()).lower() if parent_row else ''
        full_ctx = f"{link_text} {row_label}"

        if 'apply' in full_ctx and not details['action_links']['apply_online']:
            details['action_links']['apply_online'] = link_href
        elif 'notification' in full_ctx and not details['action_links']['download_notification']:
            details['action_links']['download_notification'] = link_href
            saved_path = download_and_store_file(link_href, post_slug, 'notification')
            if saved_path:
                details['stored_files']['notification_pdf'] = saved_path
        elif ('official website' in full_ctx or 'gov.in' in link_href) and not details['action_links']['official_website']:
            details['action_links']['official_website'] = link_href
        elif 'admit' in full_ctx and not details['action_links']['admit_card']:
            details['action_links']['admit_card'] = link_href
        elif 'answer key' in full_ctx and not details['action_links']['answer_key']:
            details['action_links']['answer_key'] = link_href
            if link_href.endswith('.pdf'):
                saved_path = download_and_store_file(link_href, post_slug, 'answer_key')
                if saved_path:
                    details['stored_files']['answer_key_pdf'] = saved_path
        elif 'result' in full_ctx and not details['action_links']['result']:
            details['action_links']['result'] = link_href
            if link_href.endswith('.pdf'):
                saved_path = download_and_store_file(link_href, post_slug, 'result')
                if saved_path:
                    details['stored_files']['result_pdf'] = saved_path

    return details

def run_master_scraper():
    print("🚀 Initializing Master Job Scraper...")
    db = load_existing_database()
    print(f"📊 Initial DB size: {len(db)} entries")

    sources = [
        {'name': 'Rojgar Result', 'base': 'https://rojgarresult.com/', 'url': 'https://rojgarresult.com/'},
        {'name': 'Sarkari Result', 'base': 'https://sarkariresult.com.cm/', 'url': 'https://sarkariresult.com.cm/'},
        {'name': 'Free Job Alert', 'base': 'https://www.freejobalert.com/', 'url': 'https://www.freejobalert.com/latest-notifications/'}
    ]

    new_posts_found = 0

    for src in sources:
        print(f"\n🔍 Connecting to {src['name']} ({src['url']})...")
        try:
            res = requests.get(src['url'], headers=HEADERS, timeout=15)
            print(f"Response Status: {res.status_code}")
            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            print(f"Found {len(links)} links on {src['name']}")

            for a in links:
                title = clean_text(a.get_text())
                href = a['href'].strip()

                if len(title) < 10 or href.startswith('javascript:') or href == '#':
                    continue

                key_id = re.sub(r'[^a-zA-Z0-9]', '', title).lower()[:30]
                if not key_id or key_id in db:
                    continue

                if not any(k in href.lower() or k in title.lower() for k in ['form', 'recruitment', 'vacancy', 'bharti', 'post', 'apply']):
                    continue

                full_url = urljoin(src['base'], href)
                print(f"⏳ Fetching post: {title}")
                post_data = extract_post_full_details(full_url, 'Latest Jobs', src['name'])

                if post_data and post_data.get('title'):
                    db[key_id] = post_data
                    new_posts_found += 1
                    print(f"✅ Added ({src['name']}): {post_data['title']}")

                if new_posts_found >= 15:
                    break

        except Exception as e:
            print(f"❌ Error scraping {src['name']}: {e}")

    save_database(db)
    print(f"\n🏁 Complete! Total new posts added in this run: {new_posts_found}")

if __name__ == '__main__':
    run_master_scraper()
