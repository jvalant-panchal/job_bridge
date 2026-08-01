import sqlite3

def init_db():
    conn = sqlite3.connect('jobs.db')
    cursor = conn.cursor()
    
    # 1. Create table with apply_url column included
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            advt_no TEXT UNIQUE,
            title TEXT NOT NULL,
            department TEXT,
            location TEXT,
            last_date TEXT,
            apply_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Migration: Add apply_url column if database table already exists from a previous run
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN apply_url TEXT")
    except sqlite3.OperationalError:
        # Column already exists, safe to ignore
        pass

    conn.commit()
    conn.close()

def save_jobs(jobs_list):
    conn = sqlite3.connect('jobs.db')
    cursor = conn.cursor()
    
    new_count = 0
    for job in jobs_list:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO jobs (source, advt_no, title, department, location, last_date, apply_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                job.get('source', 'OJAS'),
                job.get('advt_no'),
                job.get('title'),
                job.get('department'),
                job.get('location', 'Gujarat'),
                job.get('last_date'),
                job.get('apply_url', 'https://ojas.gujarat.gov.in')
            ))
            if cursor.rowcount > 0:
                new_count += 1
        except Exception as e:
            print(f"Error inserting job: {e}")
            
    conn.commit()
    conn.close()
    print(f"--- DATABASE STATUS: Saved {new_count} new job(s) ---")

if __name__ == "__main__":
    init_db()
    print("Database schema updated with apply_url successfully!")