import streamlit as st
import sqlite3
import pandas as pd
import urllib.parse
import os
import subprocess
import sys

# ------------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Gujarat Job Bridge",
    page_icon="💼",
    layout="wide"
)

DB_PATH = "jobs.db"

# ------------------------------------------------------------------
# DATABASE HELPER FUNCTIONS
# ------------------------------------------------------------------
def fetch_jobs_df(search_query="", source_filter="All"):
    try:
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT id, source, advt_no, title, department, location, last_date, apply_url FROM jobs WHERE 1=1"
        params = []
        
        if search_query:
            query += " AND (title LIKE ? OR department LIKE ? OR location LIKE ?)"
            wildcard = f"%{search_query}%"
            params.extend([wildcard, wildcard, wildcard])
            
        if source_filter != "All":
            query += " AND source = ?"
            params.append(source_filter)
            
        query += " ORDER BY id DESC"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database read error: {e}")
        return pd.DataFrame()

def insert_private_job(title, company, location, last_date, apply_url, advt_no="LOCAL-WALKIN"):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO jobs (source, advt_no, title, department, location, last_date, apply_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Private", advt_no, title, company, location, last_date, apply_url))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database write error: {e}")
        return False

# ------------------------------------------------------------------
# SIDEBAR CONTROL PANEL (SYNC BUTTON)
# ------------------------------------------------------------------
st.sidebar.title("⚙️ Control Panel")
st.sidebar.caption("Single-window government recruitment tracker")

st.sidebar.subheader("Live OJAS Sync")
st.sidebar.write("Pull active advertisements across departments directly from OJAS.")

if st.sidebar.button("🔄 Sync Latest OJAS Jobs", use_container_width=True, type="primary"):
    with st.sidebar.spinner("📡 Connecting to OJAS & updating listings..."):
        try:
            process = subprocess.run(
                [sys.executable, "scrape_ojas_final.py"],
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                st.sidebar.success("✅ OJAS jobs updated successfully!")
                st.rerun()
            else:
                st.sidebar.error("⚠️ Sync completed with warnings.")
                if process.stderr:
                    st.sidebar.caption(f"Log output: {process.stderr[:150]}...")
        except Exception as e:
            st.sidebar.error(f"❌ Failed to run scraper: {e}")

st.sidebar.divider()
st.sidebar.info("💡 **Tip:** Scraped OJAS jobs and manually added private jobs coexist together in `jobs.db`.")

# ------------------------------------------------------------------
# MAIN HEADER
# ------------------------------------------------------------------
st.title("💼 Gujarat Job Bridge")
st.caption("Single-Window Portal for Government Notifications & Local Opportunities in Gujarat")
st.divider()

if not os.path.exists(DB_PATH):
    st.warning("⚠️ `jobs.db` not found. Click **'Sync Latest OJAS Jobs'** in the sidebar to initialize your job database!")
    st.stop()

# ------------------------------------------------------------------
# SEARCH & FILTERS
# ------------------------------------------------------------------
col1, col2 = st.columns([3, 1])
with col1:
    search_term = st.text_input("🔍 Search jobs (e.g., Clerk, GSSSB, Gandhinagar, અમદાવાદ)...")
with col2:
    source_choice = st.selectbox("Filter Source", ["All", "OJAS", "Private"])

# TABS NAVIGATION
tab1, tab2, tab3 = st.tabs([
    "🏛️ Government Job Notices", 
    "💼 Private & Walk-in Opportunities", 
    "➕ Post Private Job (Admin)"
])

# ------------------------------------------------------------------
# CARD RENDERER
# ------------------------------------------------------------------
def render_job_cards(df):
    if df is None or df.empty:
        st.info("No matching job listings found in database.")
        return

    st.write(f"Showing **{len(df)}** active listings:")
    st.write("")
    
    for idx, row in df.iterrows():
        with st.container():
            c1, c2 = st.columns([3, 1])
            with c1:
                title = str(row.get('title', 'Job Notice'))
                dept = str(row.get('department', 'Organization'))
                loc = str(row.get('location', 'Gujarat'))
                advt = str(row.get('advt_no', 'N/A'))
                
                st.subheader(title)
                st.write(f"🏢 **Organization:** {dept}")
                st.write(f"📍 **Location:** {loc} | 📄 **Ref/Advt No:** {advt}")
            with c2:
                last_d = str(row.get('last_date', 'Check Notice'))
                st.metric(label="Last Date to Apply", value=last_d)
                
                target_url = str(row.get('apply_url', 'https://ojas.gujarat.gov.in'))
                if not target_url or target_url == "None":
                    target_url = "https://ojas.gujarat.gov.in"
                
                st.link_button("View & Apply ➡️", target_url, use_container_width=True)
                
                wa_message = f"Check out this job opening: {title} ({dept}). Apply here: {target_url}"
                encoded_msg = urllib.parse.quote(wa_message)
                wa_url = f"https://api.whatsapp.com/send?text={encoded_msg}"
                st.link_button("📲 Share on WhatsApp", wa_url, use_container_width=True)
                
            st.divider()

# TAB 1: GOVERNMENT JOBS
with tab1:
    df_govt = fetch_jobs_df(search_query=search_term, source_filter="OJAS" if source_choice == "All" else source_choice)
    render_job_cards(df_govt)

# TAB 2: PRIVATE JOBS
with tab2:
    df_private = fetch_jobs_df(search_query=search_term, source_filter="Private")
    render_job_cards(df_private)

# TAB 3: ADMIN JOB POSTING FORM
with tab3:
    st.subheader("📝 Post a Local / Private Job Vacancy")
    st.write("Use this form to add private sector hiring notices, walk-in interview details, or local business vacancies.")
    
    with st.form("admin_job_form", clear_on_submit=True):
        f_title = st.text_input("Job Title*", placeholder="e.g. Accountant, Site Engineer, Sales Executive")
        
        col_a, col_b = st.columns(2)
        with col_a:
            f_company = st.text_input("Company / Employer Name*", placeholder="e.g. Sunrise Solar Pvt Ltd")
            f_location = st.text_input("Location*", placeholder="e.g. Dahod / Ahmedabad / Remote")
        with col_b:
            f_last_date = st.text_input("Last Date to Apply*", placeholder="e.g. 15-09-2026 or Walk-in Daily")
            f_advt_no = st.text_input("Reference / Advt No (Optional)", value="LOCAL-WALKIN")
            
        f_apply_url = st.text_input("Apply Link or Contact URL*", placeholder="e.g. https://company.com/careers or https://wa.me/919999999999")
        
        submitted = st.form_submit_button("🚀 Publish Vacancy", use_container_width=True)
        
        if submitted:
            if not f_title or not f_company or not f_location or not f_last_date or not f_apply_url:
                st.error("⚠️ Please fill in all required fields marked with *.")
            else:
                success = insert_private_job(
                    title=f_title,
                    company=f_company,
                    location=f_location,
                    last_date=f_last_date,
                    apply_url=f_apply_url,
                    advt_no=f_advt_no
                )
                if success:
                    st.success(f"✅ Vacancy for '{f_title}' published successfully!")
                    st.rerun()