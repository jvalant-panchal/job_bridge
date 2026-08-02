import sqlite3

DB_NAME = "jobs.db"

def get_db_connection():
    """Returns a connection object to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            advt_no TEXT,
            title TEXT,
            department TEXT,
            location TEXT,
            last_date TEXT,
            apply_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, advt_no, title) ON CONFLICT REPLACE
        )
    ''')
    conn.commit()
    conn.close()

def save_jobs(jobs_list):
    """Saves a list of job dictionaries into the database."""
    if not jobs_list:
        return
    
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for job in jobs_list:
        cursor.execute('''
            INSERT OR REPLACE INTO jobs (source, advt_no, title, department, location, last_date, apply_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            job.get("source", "Unknown"),
            job.get("advt_no", ""),
            job.get("title", ""),
            job.get("department", ""),
            job.get("location", "Gujarat"),
            job.get("last_date", ""),
            job.get("apply_url", "")
        ))
        
    conn.commit()
    conn.close()