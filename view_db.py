import sqlite3
import sys

# Force terminal output to render Gujarati UTF-8 text properly
sys.stdout.reconfigure(encoding='utf-8')

def check_database():
    conn = sqlite3.connect('jobs.db')
    cursor = conn.cursor()
    
    # 1. Count total rows saved
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]
    print(f"\n================ TOTAL JOBS IN DB: {total_jobs} ================")
    
    # 2. Fetch and display all rows
    cursor.execute("SELECT id, source, advt_no, title, department, location, last_date FROM jobs")
    rows = cursor.fetchall()
    
    for row in rows:
        print(f"\n[ID: {row[0]}] | Source: {row[1]} | Advt No: {row[2]}")
        print(f"  Title: {row[3]}")
        print(f"  Department: {row[4]}")
        print(f"  Location: {row[5]} | Last Date: {row[6]}")
        print("-" * 60)
        
    conn.close()

if __name__ == "__main__":
    check_database()