import database
import json

def check_more_logs():
    print("Checking 50 most recent logs from DB...")
    conn = database._get_conn()
    cur = conn.cursor()
    
    query = "SELECT timestamp, endpoint, query, status FROM api_logs ORDER BY timestamp DESC LIMIT 50"
    database._execute(cur, query)
    
    rows = cur.fetchall()
    for row in rows:
        # Avoid printing full queries to avoid encode errors if it contains Thai
        q_snippet = str(row[2])[:50].replace('\n', ' ')
        print(f"[{row[0]}] {row[1]} - {q_snippet} ({row[3]})")

if __name__ == "__main__":
    check_more_logs()
