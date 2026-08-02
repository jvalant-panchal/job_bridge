import sys
import time
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

def parse_job_tables(soup, dept_name="Government of Gujarat"):
    """Utility function to extract job rows from HTML soup."""
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
                apply_url = "https://ojas.gujarat.gov.in"
                if link_tag:
                    href = link_tag['href']
                    apply_url = href if href.startswith('http') else f"https://ojas.gujarat.gov.in/{href.lstrip('/')}"

                if title and len(title) > 3 and "Advt" not in advt_no and "ONE TIME" not in title and "OTR" not in title:
                    extracted.append({
                        "source": "OJAS",
                        "advt_no": advt_no,
                        "title": title,
                        "department": dept_name,
                        "location": "Gujarat",
                        "last_date": last_date,
                        "apply_url": apply_url
                    })
    return extracted

def scrape_via_http():
    """Engine 1: Ultra-fast HTTP session scraping (Primary)."""
    print("⚡ Engine 1: Initiating Direct HTTP WebForms Scraper...")
    session = requests.Session()
    session.headers.update(HEADERS)
    
    url = "https://ojas.gujarat.gov.in/AdvtList.aspx?type=l9A312A22a"
    resp = session.get(url, timeout=15)
    
    if resp.status_code != 200:
        raise Exception(f"HTTP response code {resp.status_code}")

    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Parse ASP.NET Hidden Form Fields
    viewstate = soup.find('input', {'id': '__VIEWSTATE'})
    eventvalidation = soup.find('input', {'id': '__EVENTVALIDATION'})
    dept_select = soup.find('select')
    
    if not dept_select:
        raise Exception("Department dropdown not found in HTML response.")

    options = dept_select.find_all('option')
    total_depts = len(options)
    print(f"📋 Found {total_depts} departments via HTTP Engine.\n")
    
    all_jobs = []
    
    # Check default page jobs first
    default_jobs = parse_job_tables(soup, "General / All Departments")
    all_jobs.extend(default_jobs)

    # Postback to each department in session
    for idx in range(1, min(total_depts, 15)):  # Top active departments
        dept_val = options[idx].get('value', '')
        dept_name = options[idx].text.strip()
        
        if not dept_val or "Select" in dept_name or "---" in dept_name:
            continue

        print(f"[{idx}/{total_depts-1}] Querying Department: {dept_name}...")
        
        form_data = {
            '__VIEWSTATE': viewstate['value'] if viewstate else '',
            '__EVENTVALIDATION': eventvalidation['value'] if eventvalidation else '',
            '__EVENTTARGET': dept_select.get('name', 'ddlDept'),
            dept_select.get('name', 'ddlDept'): dept_val
        }
        
        try:
            post_resp = session.post(url, data=form_data, timeout=10)
            if post_resp.status_code == 200:
                post_soup = BeautifulSoup(post_resp.text, 'html.parser')
                dept_jobs = parse_job_tables(post_soup, dept_name)
                all_jobs.extend(dept_jobs)
                print(f"   └── Found {len(dept_jobs)} vacancy(ies)")
        except Exception as e:
            print(f"   ⚠️ Dept query skipped: {e}")

    return all_jobs

def scrape_via_playwright():
    """Engine 2: Headless Playwright Fallback (Secondary)."""
    print("\n🎭 Engine 2: Fallback to Headless Playwright Browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(user_agent=HEADERS["User-Agent"])
        page = context.new_page()
        
        target_url = "https://ojas.gujarat.gov.in/AdvtList.aspx?type=l9A312A22a"
        page.goto(target_url, wait_until="commit", timeout=30000)
        page.wait_for_timeout(3000)
        
        select_locator = page.locator("select[name*='Dept'], select[id*='Dept'], select").first
        if select_locator.count() == 0:
            browser.close()
            return []

        options = select_locator.locator("option").all_inner_texts()
        total_depts = len(options)
        scraped_jobs = []

        for idx in range(1, total_depts):
            dept_name = options[idx].strip()
            if not dept_name or "Select" in dept_name or "---" in dept_name:
                continue
                
            try:
                select_locator.select_option(index=idx)
                page.wait_for_timeout(2000)
                soup = BeautifulSoup(page.content(), 'html.parser')
                dept_jobs = parse_job_tables(soup, dept_name)
                scraped_jobs.extend(dept_jobs)
            except Exception:
                continue

        browser.close()
        return scraped_jobs

def scrape_ojas_live_advertisements():
    init_db()
    
    print("==================================================")
    print("🚀 OJAS SILENT DUAL-ENGINE SCRAPER")
    print("==================================================\n")
    
    scraped_jobs = []
    
    # Try Fast Engine First
    try:
        scraped_jobs = scrape_via_http()
    except Exception as http_err:
        print(f"⚠️ Engine 1 Notice: {http_err}. Switching to Engine 2...")
        try:
            scraped_jobs = scrape_via_playwright()
        except Exception as pw_err:
            print(f"❌ Engine 2 Failure: {pw_err}")

    print("\n==================================================")
    print(f"✅ SUCCESS: Extracted {len(scraped_jobs)} total OJAS advertisements!")
    print("==================================================\n")

    if scraped_jobs:
        save_jobs(scraped_jobs)

if __name__ == "__main__":
    scrape_ojas_live_advertisements()