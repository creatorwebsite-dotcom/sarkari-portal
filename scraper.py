import os
import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

DB_FILE = "jobs_database.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_key(text):
    return re.sub(r'[^a-zA-Z0-9]', '', text.lower())[:30]

def load_existing_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def extract_deep_details(post_url, source_name):
    try:
        res = requests.get(post_url, headers=HEADERS, timeout=12)
        if res.status_code != 200:
            return None
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text()

        # Dates
        start_d = re.search(r'(?:Apply Begin|Start Date|Notification Date|Released)\s*[:\-]?\s*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})', text, re.I)
        last_d = re.search(r'(?:Last Date|Apply Last|End Date)\s*[:\-]?\s*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})', text, re.I)
        exam_d = re.search(r'(?:Exam Date|Date of Exam)\s*[:\-]?\s*([A-Za-z0-9\s\/\-]+202[5-7])', text, re.I)

        # Fee
        gen_f = re.search(r'(?:General|Gen|OBC|EWS)\s*[:\-]?\s*(?:₹|Rs\.?)?\s*([0-9]{1,4}\/-?)', text, re.I)
        sc_f = re.search(r'(?:SC|ST|PH)\s*[:\-]?\s*(?:₹|Rs\.?)?\s*([0-9]{1,4}\/-?|0\/-?|Free)', text, re.I)

        # Age
        min_a = re.search(r'(?:Minimum Age|Min Age)\s*[:\-]?\s*([0-9]{1,2}\s*Years?)', text, re.I)
        max_a = re.search(r'(?:Maximum Age|Max Age)\s*[:\-]?\s*([0-9]{1,2}\s*Years?)', text, re.I)

        # 6-Gateway Links
        action_links = {
            "apply_online": "",
            "download_notification": "",
            "download_admit_card": "",
            "download_answer_key": "",
            "check_cutoff": "",
            "official_website": ""
        }

        for a in soup.find_all("a", href=True):
            href = urljoin(post_url, a['href'])
            t = a.get_text().strip().lower()

            if not action_links["download_notification"] and (any(k in t for k in ["download notification", "rulebook", "advt", "notice pdf"]) or (".pdf" in href.lower() and "notice" in href.lower())):
                action_links["download_notification"] = href
            if not action_links["apply_online"] and any(k in t for k in ["apply online", "online registration", "candidate login", "apply now"]):
                action_links["apply_online"] = href
            if not action_links["download_admit_card"] and any(k in t for k in ["download admit card", "hall ticket", "call letter"]):
                action_links["download_admit_card"] = href
            if not action_links["download_answer_key"] and any(k in t for k in ["download answer key", "model answer", "objection link"]):
                action_links["download_answer_key"] = href
            if not action_links["check_cutoff"] and any(k in t for k in ["download result", "cutoff", "cut off", "score card", "merit list"]):
                action_links["check_cutoff"] = href
            if not action_links["official_website"] and any(k in t for k in ["official website", "official portal", "home page"]):
                action_links["official_website"] = href

        if not action_links["official_website"]:
            action_links["official_website"] = post_url

        return {
            "important_dates": {
                "apply_start": start_d.group(1) if start_d else "Available Online",
                "apply_last": last_d.group(1) if last_d else "Check Notification",
                "fee_last": last_d.group(1) if last_d else "Check Notification",
                "exam_date": exam_d.group(1).strip() if exam_d else "As per schedule"
            },
            "application_fee": {
                "gen_other_state": gen_f.group(1) if gen_f else "₹ 500/-",
                "sc_st_obc_ews": sc_f.group(1) if sc_f else "₹ 250/-",
                "portal_charge": "Extra as applicable"
            },
            "age_limit": {
                "min_age": min_a.group(1) if min_a else "18 Years",
                "max_age": max_a.group(1) if max_a else "35 Years"
            },
            "action_links": action_links
        }
    except Exception:
        return None

def detect_category(title):
    t = title.lower()
    if any(k in t for k in ["answer key", "key", "objection"]): return "Answer Key"
    if any(k in t for k in ["result", "scorecard", "merit list", "cutoff"]): return "Result"
    if any(k in t for k in ["admit card", "hall ticket", "call letter", "exam date"]): return "Admit Card"
    if any(k in t for k in ["syllabus"]): return "Syllabus"
    if any(k in t for k in ["admission", "counseling"]): return "Admission"
    return "Latest Jobs"

def scrape_source(base_url, source_name, existing_db):
    print(f"Scraping {source_name}...")
    try:
        res = requests.get(base_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.find_all("a", href=True):
            title = a.get_text().strip()
            link = urljoin(base_url, a['href'])
            if len(title) > 12 and not any(k in link for k in ["facebook", "telegram", "whatsapp", "twitter"]):
                key = clean_key(title)
                # First fetch priority: Agar post already kisi pehli site se aa gayi to overwrite nahi hogi
                if key not in existing_db:
                    cat = detect_category(title)
                    deep_info = extract_deep_details(link, source_name)
                    if deep_info:
                        existing_db[key] = {
                            "title": title,
                            "category": cat,
                            "source": source_name,
                            "url": link,
                            **deep_info
                        }
    except Exception as e:
        print(f"Error in {source_name}: {e}")

if __name__ == "__main__":
    db = load_existing_db()

    # Priority Order: 1. Rojgar Result -> 2. Sarkari Result -> 3. Free Job Alert
    scrape_source("https://rojgarresult.com/", "Rojgar Result", db)
    scrape_source("https://sarkariresult.com.cm/", "Sarkari Result", db)
    scrape_source("https://www.freejobalert.com/", "Free Job Alert", db)

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    print(f"Sync complete. Total unique records: {len(db)}")
