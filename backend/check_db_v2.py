import database
import json
from datetime import datetime

def check_recent_logs():
    print("Checking 10 most recent logs from DB...")
    stats = database.get_dashboard_stats() # This usually returns summary
    # Actually let's just query directly
    conn = database._get_conn()
    cur = conn.cursor()
    
    query = "SELECT timestamp, endpoint, query, status FROM api_logs ORDER BY timestamp DESC LIMIT 10"
    database._execute(cur, query)
    
    rows = cur.fetchall()
    for row in rows:
        print(f"[{row[0]}] {row[1]} - {row[2]} ({row[3]})")

if __name__ == "__main__":
    check_recent_logs()
