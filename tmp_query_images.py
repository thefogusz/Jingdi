import sqlite3
import os

db_path = "backend/stats.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT query FROM api_logs WHERE query LIKE '%[Image Upload]%' ORDER BY id DESC LIMIT 5")
rows = cur.fetchall()
for row in rows:
    print(row[0])
conn.close()
