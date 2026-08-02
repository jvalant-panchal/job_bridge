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

HC_OJAS_URL = "https://hc-ojas.gujarat.gov.in/AdvtList.aspx?type=l9A312A22a"

def parse_hc_tables(soup, dept_name="High Court of Gujarat"):
    """Extract job listings from Gujarat High Court OJAS table."""
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
                apply_url = "https://hc-ojas.gujarat.gov.in"
                if link_tag:
                    href = link_tag['href']
                    apply_url = href if href.startswith('http') else f"https://hc-ojas.gujarat.gov.in/{href.lstrip('/')}"

                if title and len(title) > 3 and "Advt" not in advt_no and "ONE TIME" not in title and "OTR" not in title:
                    extracted.append({
                        "source": "HC-OJAS",
                        "advt_no": advt_no,
                        "title": title,
                        "department": f"Judiciary / Courts ({dept_name})" if "High Court" not in dept_name else dept_name,
                        "location": "Gujarat",
                        "last_date": last_date,
                        "apply_url": apply_url
                    })
    return extracted

def scrape_hc_http():
    """Engine 1: Fast HTTP session query for HC-OJAS."""
    print("⚡ Engine 1: Querying HC-OJAS WebForms Endpoint via HTTP...")
    session = requests.Session()
    session.headers.update(HEADERS)
    
    resp = session.get(HC_OJAS_URL, timeout=15)
    if resp.status_code != 200:
        raise Exception(f"HC-OJAS HTTP response status {resp.status_code}")

    soup = BeautifulSoup(resp.text, 'html.parser')
    all_jobs = parse_hc_tables(soup, "High Court / District Judiciary")

    dept_select = soup.find('select')
    if dept_select:
        viewstate = soup.find('input', {'id': '__VIEWSTATE'})
        eventvalidation = soup.find('input', {'id': '__EVENTVALIDATION'})
        options = dept_select.find_all('option')
        
        for idx, opt in enumerate(options):
            dept_val = opt.get('value', '')
            dept_name = opt.text.strip()
            
            if not dept_val or "Select" in dept_name or "---" in dept_name:
                continue

            print(f"[{idx}/{len(options)-1}] Querying HC-OJAS Category: {dept_name}...")
            
            form_data = {
                '__VIEWSTATE': viewstate['value'] if viewstate else '',
                '__EVENTVALIDATION': eventvalidation['value'] if eventvalidation else '',
                '__EVENTTARGET': dept_select.get('name', 'ddlDept'),
                dept_select.get('name', 'ddlDept'): dept_val
            }
            
            try:
                post_resp = session.post(HC_OJAS_URL, data=form_data, timeout=10)
                if post_resp.status_code == 200:
                    post_soup = BeautifulSoup(post_resp.text, 'html.parser')
                    dept_jobs = parse_hc_tables(post_soup, dept_name)
                    all_jobs.extend(dept_jobs)
                    print(f"   └── Found {len(dept_jobs)} vacancy(ies)")
            except Exception as e:
                print(f"   ⚠️ Category query skipped: {e}")

    return all_jobs

def scrape_hc_playwright():
    """Engine 2: Playwright fallback for HC-OJAS."""
    print("\n🎭 Engine 2: Fallback to Headless Playwright Browser for HC-OJAS...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(user_agent=HEADERS["User-Agent"])
        page = context.new_page()
        
        page.goto(HC_OJAS_URL, wait_until="commit", timeout=30000)
        page.wait_for_timeout(3000)
        
        soup = BeautifulSoup(page.content(), 'html.parser')
        scraped_jobs = parse_hc_tables(soup, "High Court / District Judiciary")
        
        select_locator = page.locator("select[name*='Dept'], select[id*='Dept'], select").first
        if select_locator.count() > 0:
            options = select_locator.locator("option").all_inner_texts()
            for idx in range(1, len(options)):
                dept_name = options[idx].strip()
                if not dept_name or "Select" in dept_name or "---" in dept_name:
                    continue
                    
                try:
                    select_locator.select_option(index=idx)
                    page.wait_for_timeout(2500)
                    dept_soup = BeautifulSoup(page.content(), 'html.parser')
                    dept_jobs = parse_hc_tables(dept_soup, dept_name)
                    scraped_jobs.extend(dept_jobs)
                except Exception:
                    continue

        browser.close()
        return scraped_jobs

def scrape_hc_ojas_live_advertisements():
    init_db()
    
    print("==================================================")
    print("⚖️ GUJARAT HIGH COURT OJAS SILENT SCRAPER")
    print("==================================================\n")
    
    scraped_jobs = []
    
    try:
        scraped_jobs = scrape_hc_http()
    except Exception as err:
        print(f"⚠️ Engine 1 Notice: {err}. Switching to Engine 2...")
        try:
            scraped_jobs = scrape_hc_playwright()
        except Exception as pw_err:
            print(f"❌ Engine 2 Failure: {pw_err}")

    print("\n==================================================")
    print(f"✅ SUCCESS: Extracted {len(scraped_jobs)} live HC-OJAS advertisements!")
    print("==================================================\n")

    if scraped_jobs:
        save_jobs(scraped_jobs)

if __name__ == "__main__":
    scrape_hc_ojas_live_advertisements()