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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def clean_text(txt):
    return re.sub(r'\s+', ' ', txt).strip() if txt else ''

def run():
    db = {}
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                db = json.loads(content) if content else {}
        except Exception as e:
            print(f"Read error: {e}")
            db = {}

    # Guaranteed Base Post (Always added)
    db['mpesbsubedarsteno2026'] = {
        'title': 'MPESB Subedar Steno, ASI Online Form 2026',
        'url': 'https://esb.mp.gov.in',
        'category': 'Latest Jobs',
        'source': 'Official Board',
        'important_dates': {
            'apply_start': '24/09/2026',
            'apply_last': '08/10/2026',
            'fee_last': '08/10/2026',
            'correction_last': '13/10/2026',
            'exam_date': 'November 2026'
        },
        'application_fee': {
            'gen_other_state': '500/-',
            'sc_st_obc_ews': '250/-',
            'portal_charge': '60/-'
        },
        'age_limit': {
            'min_age': '18 Years',
            'max_age': '33-38 Years (As per rules)'
        },
        'vacancy_details': [
            ['Subedar (Stenographer)', '150', 'Graduation with Steno Diploma / CPCT'],
            ['Assistant Sub Inspector (LDC)', '505', '12th Pass with 1 Yr Computer Diploma & CPCT']
        ],
        'action_links': {
            'apply_online': 'https://esb.mponline.gov.in',
            'download_notification': 'https://esb.mp.gov.in/Rulebooks/RB_2026/Subedar_Steno_2026_Rulebook.pdf',
            'official_website': 'https://esb.mp.gov.in'
        },
        'stored_files': {
            'notification_pdf': ''
        }
    }

    # Websites se fresh data
    sources = [
        {'name': 'Rojgar Result', 'base': 'https://rojgarresult.com/', 'url': 'https://rojgarresult.com/'},
        {'name': 'Sarkari Result', 'base': 'https://sarkariresult.com.cm/', 'url': 'https://sarkariresult.com.cm/'}
    ]

    for src in sources:
        try:
            r = requests.get(src['url'], headers=HEADERS, timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    title = clean_text(a.get_text())
                    href = a['href'].strip()
                    if len(title) > 12 and any(k in href.lower() for k in ['online', 'form', 'recruitment', 'vacancy', 'apply']):
                        slug = re.sub(r'[^a-zA-Z0-9]', '', title).lower()[:30]
                        if slug and slug not in db:
                            db[slug] = {
                                'title': title,
                                'url': urljoin(src['base'], href),
                                'category': 'Latest Jobs',
                                'source': src['name']
                            }
                            print(f"Added: {title}")
        except Exception as e:
            print(f"Error scraping {src['name']}: {e}")

    # File ko disk par save karein
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f"SUCCESS: {len(db)} records written to {DATABASE_FILE}")

if __name__ == '__main__':
    run()
