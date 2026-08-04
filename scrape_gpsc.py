import sys
import socket

# FORCE IPV4 RESOLUTION GLOBALLY (Fixes [Errno 101] Network is unreachable)
old_getaddrinfo = socket.getaddrinfo
def allowed_gai_family(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]
socket.getaddrinfo = allowed_gai_family

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from database import init_db, save_jobs

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

GPSC_URL = "https://gpsc-ojas.gujarat.gov.in/AdvtList.aspx?type=l9A312A22a"

def parse_gpsc_tables(soup, dept_name="GPSC Executive"):
    extracted = []
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                advt_no = cols[0].text.strip()
                title = cols[1].text.strip()
                last_date = cols[2].text.strip() if len(cols) > 2 else "Check Notice"
                link_tag = row.find('a', href=True)
                apply_url = "https://gpsc-ojas.gujarat.gov.in"
                if link_tag:
                    href = link_tag['href']
                    apply_url = href if href.startswith('http') else f"https://gpsc-ojas.gujarat.gov.in/{href.lstrip('/')}"

                if title and len(title) > 3 and "Advt" not in advt_no and "ONE TIME" not in title:
                    extracted.append({
                        "source": "GPSC",
                        "advt_no": advt_no,
                        "title": title,
                        "department": dept_name,
                        "location": "Gujarat",
                        "last_date": last_date,
                        "apply_url": apply_url
                    })
    return extracted

def scrape_gpsc_http():
    print("⚡ Engine 1: Querying GPSC via HTTP (IPv4 Forced)...")
    session = requests.Session()
    session.headers.update(HEADERS)
    resp = session.get(GPSC_URL, timeout=20, verify=False)
    if resp.status_code != 200:
        raise Exception(f"HTTP status {resp.status_code}")
    soup = BeautifulSoup(resp.text, 'html.parser')
    return parse_gpsc_tables(soup)

def scrape_gpsc_playwright():
    print("🎭 Engine 2: Fallback to Headless Playwright Browser for GPSC...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(user_agent=HEADERS["User-Agent"], ignore_https_errors=True)
        page = context.new_page()
        page.set_default_navigation_timeout(60000)
        page.goto(GPSC_URL, wait_until="domcontentloaded", timeout=60000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        jobs = parse_gpsc_tables(soup)
        browser.close()
        return jobs

def scrape_gpsc_live_advertisements():
    init_db()
    print("==================================================")
    print("🏛️ GPSC SILENT BACKGROUND SCRAPER")
    print("==================================================\n")
    jobs = []
    try:
        jobs = scrape_gpsc_http()
    except Exception as e:
        print(f"⚠️ Engine 1 Notice: {e}. Switching to Engine 2...")
        try:
            jobs = scrape_gpsc_playwright()
        except Exception as pw_e:
            print(f"❌ Engine 2 Failure: {pw_e}")

    print(f"\n✅ SUCCESS: Extracted {len(jobs)} live GPSC advertisements!")
    if jobs:
        save_jobs(jobs)

if __name__ == "__main__":
    scrape_gpsc_live_advertisements()