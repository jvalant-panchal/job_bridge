import sys
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from database import init_db, save_jobs

sys.stdout.reconfigure(encoding='utf-8')

def scrape_ojas_live_advertisements():
    init_db()
    
    print("==================================================")
    print("🚀 OJAS SILENT BACKGROUND SCRAPER")
    print("==================================================\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9,gu;q=0.8"
            }
        )
        page = context.new_page()
        
        # Step 1: Establish Session via AdvtList directly or Homepage
        print("1. Connecting to OJAS portal...")
        target_url = "https://ojas.gujarat.gov.in/AdvtList.aspx?type=l9A312A22a"
        
        try:
            # 'commit' returns instantly as soon as HTTP response headers arrive
            page.goto(target_url, wait_until="commit", timeout=30000)
            page.wait_for_timeout(4000)
        except Exception as e:
            print(f"⚠️ Direct load notice: {e}. Retrying homepage session...")
            try:
                page.goto("https://ojas.gujarat.gov.in/", wait_until="commit", timeout=30000)
                page.wait_for_timeout(3000)
                page.goto(target_url, wait_until="commit", timeout=30000)
                page.wait_for_timeout(3000)
            except Exception as retry_err:
                print(f"❌ Could not connect to OJAS server: {retry_err}")
                browser.close()
                return

        # Step 2: Locate Department Dropdown with retry
        print("2. Locating Department Dropdown...")
        try:
            page.wait_for_selector("select[name*='Dept'], select[id*='Dept'], select", timeout=15000)
        except Exception:
            print("⚠️ Dropdown selector wait timed out. Checking current page content...")

        select_locator = page.locator("select[name*='Dept'], select[id*='Dept'], select").first
        
        if select_locator.count() == 0:
            print("❌ Department dropdown not found. OJAS portal may be down or blocking automated requests.")
            browser.close()
            return

        print("✅ Department Dropdown Loaded Successfully!\n")
        
        options = select_locator.locator("option").all_inner_texts()
        total_depts = len(options)
        print(f"📋 Found {total_depts} departments in OJAS dropdown list.\n")

        scraped_jobs = []

        for idx in range(1, total_depts):
            dept_name = options[idx].strip()
            
            if not dept_name or "Select" in dept_name or "---" in dept_name:
                continue

            print(f"[{idx}/{total_depts-1}] Scraping Department: {dept_name}...")
            
            try:
                select_locator.select_option(index=idx)
                page.wait_for_timeout(2500)
                
                soup = BeautifulSoup(page.content(), 'html.parser')
                tables = soup.find_all('table')
                dept_jobs_found = 0
                
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            advt_no = cols[0].text.strip()
                            title = cols[1].text.strip()
                            last_date = cols[2].text.strip() if len(cols) > 2 else "Check Notice"
                            
                            link_tag = row.find('a', href=True)
                            apply_url = "https://ojas.gujarat.gov.in"
                            if link_tag:
                                href = link_tag['href']
                                apply_url = href if href.startswith('http') else f"https://ojas.gujarat.gov.in/{href.lstrip('/')}"

                            if title and len(title) > 3 and "Advt" not in advt_no and "ONE TIME" not in title and "OTR" not in title:
                                scraped_jobs.append({
                                    "source": "OJAS",
                                    "advt_no": advt_no,
                                    "title": title,
                                    "department": dept_name,
                                    "location": "Gujarat",
                                    "last_date": last_date,
                                    "apply_url": apply_url
                                })
                                dept_jobs_found += 1
                                
                print(f"   └── Found {dept_jobs_found} live vacancy(ies)")

            except Exception as dept_err:
                print(f"   ⚠️ Skipping {dept_name}: {dept_err}")

        browser.close()

        print("\n==================================================")
        print(f"✅ SUCCESS: Extracted {len(scraped_jobs)} live OJAS advertisements!")
        print("==================================================\n")

        if scraped_jobs:
            save_jobs(scraped_jobs)

if __name__ == "__main__":
    scrape_ojas_live_advertisements()