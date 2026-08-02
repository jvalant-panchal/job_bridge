import sys
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from database import init_db, save_jobs

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,gu;q=0.8",
}

# Primary official URL for GSERC teaching recruitment
GSERC_URL = "https://gserc.in"

def parse_gserc_notices(soup):
    """Extract Vidhyasahayak and Shikshan Sahayak teaching advertisements."""
    extracted = []
    links = soup.find_all('a', href=True)
    
    keywords = ["vidhyasahayak", "shikshan sahayak", "bharti", "recruitment", "advertisement", "jherat", "gserc", "notice"]
    
    for idx, link in enumerate(links):
        title = link.text.strip()
        href = link['href']
        
        if title and len(title) > 6 and any(kw in title.lower() or kw in href.lower() for kw in keywords):
            apply_url = href if href.startswith('http') else f"https://gserc.in/{href.lstrip('/')}"
            
            extracted.append({
                "source": "GSERC",
                "advt_no": f"GSERC-2026-{idx+1:03d}",
                "title": title,
                "department": "GSERC / Education Department Gujarat",
                "location": "Gujarat",
                "last_date": "Check Notice PDF",
                "apply_url": apply_url
            })
            
    return extracted

def scrape_gserc_http():
    """Engine 1: Fast HTTP session parsing for GSERC School Recruitment."""
    print("⚡ Engine 1: Querying GSERC Portal (gserc.in) via HTTP...")
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        resp = session.get(GSERC_URL, timeout=12)
        if resp.status_code != 200:
            raise Exception(f"GSERC HTTP status {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')
        return parse_gserc_notices(soup)
    except Exception as err:
        raise Exception(f"HTTP request failed: {err}")

def scrape_gserc_playwright():
    """Engine 2: Playwright fallback for dynamic JavaScript elements."""
    print("🎭 Engine 2: Fallback to Headless Playwright Browser for GSERC...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(user_agent=HEADERS["User-Agent"])
        page = context.new_page()
        
        try:
            page.goto(GSERC_URL, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)
            soup = BeautifulSoup(page.content(), 'html.parser')
            jobs = parse_gserc_notices(soup)
        except Exception as pw_err:
            print(f"   ⚠️ Playwright navigation notice: {pw_err}")
            jobs = []
        finally:
            browser.close()
            
        return jobs

def scrape_gserc_live_advertisements():
    init_db()
    
    print("==================================================")
    print("🎓 GSERC & VIDHYASAHAYAK TEACHING SCRAPER")
    print("==================================================\n")
    
    scraped_jobs = []
    
    try:
        scraped_jobs = scrape_gserc_http()
    except Exception as err:
        print(f"⚠️ Engine 1 Notice: {err}. Switching to Engine 2...")
        try:
            scraped_jobs = scrape_gserc_playwright()
        except Exception as pw_err:
            print(f"❌ Engine 2 Failure: {pw_err}")

    print("\n==================================================")
    print(f"✅ SUCCESS: Extracted {len(scraped_jobs)} live Vidhyasahayak/GSERC notices!")
    print("==================================================\n")

    if scraped_jobs:
        save_jobs(scraped_jobs)

if __name__ == "__main__":
    scrape_gserc_live_advertisements()