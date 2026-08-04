import sys
import socket
import requests
import urllib3
from bs4 import BeautifulSoup
from database import init_db, save_jobs

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.stdout.reconfigure(encoding='utf-8')

# Prevent recursive monkey-patching of socket.getaddrinfo
if not getattr(socket, '_ipv4_patched', False):
    _orig_getaddrinfo = socket.getaddrinfo
    def allowed_gai_family(*args, **kwargs):
        return [r for r in _orig_getaddrinfo(*args, **kwargs) if r[0] == socket.AF_INET]
    socket.getaddrinfo = allowed_gai_family
    socket._ipv4_patched = True

BASE_URL = "https://hc-ojas.gujarat.gov.in"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,gu;q=0.8",
    "Connection": "keep-alive"
}

def parse_tables(soup, dept_name="High Court of Gujarat"):
    extracted = []
    tables = soup.find_all('table')
    for table in tables:
        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) >= 2:
                advt_no = cols[0].text.strip()
                title = cols[1].text.strip()
                last_date = cols[2].text.strip() if len(cols) > 2 else "Check Notice"
                
                link_tag = row.find('a', href=True)
                apply_url = BASE_URL
                if link_tag:
                    href = link_tag['href']
                    apply_url = href if href.startswith('http') else f"{BASE_URL}/{href.lstrip('/')}"

                if title and len(title) > 3 and "Advt" not in advt_no and "ONE TIME" not in title and "Sr.No" not in advt_no:
                    extracted.append({
                        "source": "HC-OJAS",
                        "advt_no": advt_no,
                        "title": title,
                        "department": dept_name,
                        "location": "Gujarat",
                        "last_date": last_date,
                        "apply_url": apply_url
                    })
    return extracted

def run_hc_scraper():
    print("==================================================")
    print("⚖️ GUJARAT HIGH COURT OJAS SCRAPER")
    print("==================================================\n")

    session = requests.Session()
    session.headers.update(HEADERS)
    all_jobs = []

    print("🌐 Step 1: Navigating to High Court OJAS Homepage...")
    try:
        init_res = session.get(BASE_URL, timeout=15, verify=False)
    except Exception as e:
        print(f"❌ Connection error to High Court root: {e}")
        return []

    if init_res.status_code != 200:
        print(f"❌ High Court Homepage HTTP {init_res.status_code}")
        return []

    root_soup = BeautifulSoup(init_res.text, 'html.parser')
    advt_link_tag = root_soup.find('a', href=lambda h: h and 'AdvtList.aspx' in h)
    
    if advt_link_tag and advt_link_tag.get('href'):
        href = advt_link_tag['href']
        advt_url = href if href.startswith('http') else f"{BASE_URL}/{href.lstrip('/')}"
        print(f"   └── Found dynamic advertisement endpoint: {advt_url}")
    else:
        advt_url = f"{BASE_URL}/AdvtList.aspx"
        print(f"   └── Fallback advertisement endpoint: {advt_url}")

    print("🌐 Step 2: Requesting High Court Advertisement List Page...")
    session.headers.update({"Referer": BASE_URL})
    
    try:
        res = session.get(advt_url, timeout=20, verify=False)
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return []

    soup = BeautifulSoup(res.text, 'html.parser')
    page_title = soup.title.string.strip() if soup.title else "No Title"
    print(f"   └── Response Page Title: '{page_title}'")

    # Direct Table Parsing (Main Page)
    initial_jobs = parse_tables(soup, "High Court of Gujarat")
    if initial_jobs:
        print(f"   └── ✅ Found {len(initial_jobs)} advertisement(s) directly on main page!")
        all_jobs.extend(initial_jobs)
    else:
        print("   └── No active advertisements currently posted on main page.")

    # Optional Dropdown Handling
    select_elem = soup.find('select')
    if select_elem:
        select_name = select_elem.get('name') or select_elem.get('id')
        options = select_elem.find_all('option')
        
        valid_options = []
        for opt in options:
            val = opt.get('value', '').strip()
            txt = opt.text.strip()
            if val and val not in ['0', '-1'] and "Select" not in txt and "---" not in txt:
                valid_options.append((val, txt))

        if valid_options:
            print(f"📋 Step 3: Querying {len(valid_options)} category dropdown options...\n")
            for idx, (val, dept_name) in enumerate(valid_options):
                form_data = {
                    hidden.get('name'): hidden.get('value', '')
                    for hidden in soup.find_all('input', type='hidden')
                    if hidden.get('name')
                }
                form_data['__EVENTTARGET'] = select_name
                form_data['__EVENTARGUMENT'] = ''
                form_data[select_name] = val

                session.headers.update({"Referer": advt_url})
                try:
                    post_res = session.post(advt_url, data=form_data, timeout=15, verify=False)
                    if post_res.status_code == 200:
                        post_soup = BeautifulSoup(post_res.text, 'html.parser')
                        dept_jobs = parse_tables(post_soup, dept_name)
                        if dept_jobs:
                            all_jobs.extend(dept_jobs)
                except Exception as err:
                    print(f"   └── ⚠️ Postback failed: {err}")

    # Deduplicate extracted listings
    unique_jobs = {job['advt_no']: job for job in all_jobs}.values()
    return list(unique_jobs)

def main():
    init_db()
    jobs = run_hc_scraper()
    print("\n==================================================")
    print(f"✅ Extracted {len(jobs)} total High Court advertisements!")
    print("==================================================\n")
    if jobs:
        save_jobs(jobs)

if __name__ == "__main__":
    main()