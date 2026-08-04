import streamlit as st
import pandas as pd
import sqlite3
from database import get_db_connection, save_jobs

# Streamlit Page Configuration
st.set_page_config(
    page_title="Gujarat Job Bridge",
    page_icon="🌉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Sleek Professional Look
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    .metric-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
    }
    .portal-card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 20px;
        border-left: 5px solid #1e88e5;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# DATABASE UTILITIES
# ---------------------------------------------------------
def load_jobs_df():
    """Fetch all saved jobs from SQLite database."""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM jobs ORDER BY id DESC", conn)
    except Exception:
        df = pd.DataFrame(columns=["id", "source", "advt_no", "title", "department", "location", "last_date", "apply_url"])
    finally:
        conn.close()
    return df

# ---------------------------------------------------------
# NAVIGATION & HEADER
# ---------------------------------------------------------
st.title("🌉 Gujarat Job Bridge")
st.caption("Centralized Government & Private Opportunities Across Gujarat")

# Top Navigation Tabs
tab_jobs, tab_exams, tab_admin = st.tabs([
    "💼 Live Vacancies", 
    "📢 Exam Notifications & Answer Keys", 
    "⚙️ Admin Portal"
])

# =========================================================
# TAB 1: LIVE JOB VACANCIES
# =========================================================
with tab_jobs:
    df = load_jobs_df()
    
    # Filter Sidebar
    st.sidebar.header("🔍 Filter Vacancies")
    
    sources = ["All"] + list(df["source"].unique()) if not df.empty else ["All"]
    selected_source = st.sidebar.selectbox("Filter Source", sources)
    
    search_query = st.sidebar.text_input("Search Job Title / Dept", "")
    
    filtered_df = df.copy()
    if selected_source != "All":
        filtered_df = filtered_df[filtered_df["source"] == selected_source]
        
    if search_query:
        filtered_df = filtered_df[
            filtered_df["title"].str.contains(search_query, case=False, na=False) |
            filtered_df["department"].str.contains(search_query, case=False, na=False)
        ]
        
    # Metrics Summary across all sources
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Active Jobs", len(df))
    m2.metric("OJAS State", len(df[df["source"] == "OJAS"]) if not df.empty else 0)
    m3.metric("GPSC Officers", len(df[df["source"] == "GPSC"]) if not df.empty else 0)
    m4.metric("High Court", len(df[df["source"] == "HC-OJAS"]) if not df.empty else 0)
    m5.metric("GSERC Teaching", len(df[df["source"] == "GSERC"]) if not df.empty else 0)
    
    st.divider()
    
    # Jobs Display Table
    if filtered_df.empty:
        st.info("No job listings found matching your search criteria.")
    else:
        st.dataframe(
            filtered_df[["source", "advt_no", "title", "department", "last_date", "apply_url"]],
            column_config={
                "source": "Source",
                "advt_no": "Advt No.",
                "title": "Job Designation",
                "department": "Department / Board",
                "last_date": "Last Date to Apply",
                "apply_url": st.column_config.LinkColumn("Apply Link", display_text="Apply Now 🔗")
            },
            hide_index=True,
            width="stretch"
        )

# =========================================================
# TAB 2: EXAM NOTIFICATIONS & ANSWER KEYS
# =========================================================
with tab_exams:
    st.header("📢 Candidate Resource Hub")
    st.write("Direct access to official Exam Schedules, Hall Tickets (Call Letters), Provisional/Final Answer Keys, and Results.")
    
    # Direct Official Action Bar
    st.subheader("⚡ Quick Official Launchers")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.link_button("🎟️ OJAS Call Letters", "https://ojas.gujarat.gov.in/PrintCallLetter.aspx?opt=MAIN", width="stretch")
    with col2:
        st.link_button("🏛️ GPSC Answer Keys", "https://gpsc.gujarat.gov.in/AnswerKey?opt=MAIN", width="stretch")
    with col3:
        st.link_button("📜 GSSSB Official Updates", "https://gsssb.gujarat.gov.in/News.htm", width="stretch")
    with col4:
        st.link_button("🔍 Check OJAS Results", "https://ojas.gujarat.gov.in/AdvtList.aspx?type=l9A312A22a", width="stretch")
        
    st.divider()
    
    # Board-Specific Resource Sections
    board_choice = st.radio("Select Recruitment Board", ["All Boards", "GSSSB (Subordinate Services)", "GPSC (Public Service)", "OJAS Central Portal"], horizontal=True)
    
    # Section 1: GSSSB Updates
    if board_choice in ["All Boards", "GSSSB (Subordinate Services)"]:
        st.markdown("""
        <div class="portal-card">
            <h3>📑 GSSSB (Gujarat Subordinate Service Selection Board)</h3>
            <p><strong>Common Exams:</strong> CCE (Combined Competitive Exam), Head Clerk, Senior Clerk, Police Sub-Inspector, Junior Clerk.</p>
        </div>
        """, unsafe_allow_html=True)
        
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("##### 🔑 Answer Keys & Objections")
            st.write("Submit OMR objections and view official provisional answer keys directly on GSSSB.")
            st.link_button("Open GSSSB Answer Key Portal 🔗", "https://gsssb.gujarat.gov.in/")
        with g2:
            st.markdown("##### 🎫 Hall Ticket & CBRT Exam City")
            st.write("Check Computer-Based Recruitment Test (CBRT) schedule and download call letters.")
            st.link_button("Download GSSSB Call Letter 🔗", "https://ojas.gujarat.gov.in/PrintCallLetter.aspx?opt=MAIN")

    # Section 2: GPSC Updates
    if board_choice in ["All Boards", "GPSC (Public Service)"]:
        st.markdown("""
        <div class="portal-card" style="border-left-color: #388e3c;">
            <h3>🏛️ GPSC (Gujarat Public Service Commission)</h3>
            <p><strong>Common Exams:</strong> Class 1/2 Executive Officers, Chief Officer, STI, Dy.SO, Assistant Professor, RFO.</p>
        </div>
        """, unsafe_allow_html=True)
        
        p1, p2 = st.columns(2)
        with p1:
            st.markdown("##### 📝 Question Papers & Key Objections")
            st.write("Download Preliminary/Mains question papers and official suggestion form for answer keys.")
            st.link_button("GPSC Exam Papers & Keys 🔗", "https://gpsc.gujarat.gov.in/")
        with p2:
            st.markdown("##### 📊 Final Results & Interview Schedules")
            st.write("Check prelims qualifying marks, interview dates, and final recommendation lists.")
            st.link_button("GPSC Results Portal 🔗", "https://gpsc-ojas.gujarat.gov.in/")

    # Candidate Guide Box
    st.info("💡 **Candidate Tip:** Always keep your **Confirmation Number** and **Date of Birth (DD/MM/YYYY)** handy when downloading Call Letters or submitting Answer Key objections on OJAS/GPSC portals.")

# =========================================================
# TAB 3: ADMIN PORTAL
# =========================================================
with tab_admin:
    st.header("⚙️ Admin Management Portal")
    st.write("Manually add local/private job postings to `jobs.db`.")
    
    with st.form("add_job_form", clear_on_submit=True):
        f_source = st.selectbox("Job Source", ["Private", "Local Dahod", "Contractual", "OJAS Manual"])
        f_advt = st.text_input("Advt / Reference No.", "PVT-2026-001")
        f_title = st.text_input("Job Title / Designation", placeholder="e.g. Solar Installation Engineer")
        f_dept = st.text_input("Company / Organization Name", placeholder="e.g. Dahod Solar Tech Pvt Ltd")
        f_location = st.text_input("Job Location", "Gujarat")
        f_date = st.text_input("Last Date to Apply", "31/12/2026")
        f_url = st.text_input("Application / Contact URL", "https://")
        
        submitted = st.form_submit_button("➕ Save Job Posting")
        
        if submitted:
            if f_title and f_dept:
                save_jobs([{
                    "source": f_source,
                    "advt_no": f_advt,
                    "title": f_title,
                    "department": f_dept,
                    "location": f_location,
                    "last_date": f_date,
                    "apply_url": f_url
                }])
                st.success(f"✅ Successfully added '{f_title}' to jobs.db!")
                st.rerun()
            else:
                st.error("Please fill in both Job Title and Company/Department name.")