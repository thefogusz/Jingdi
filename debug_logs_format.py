import sqlite3
import os

db_path = "backend/stats.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT query, timestamp FROM api_logs WHERE query LIKE '%[Image Upload]%' ORDER BY id DESC LIMIT 5")
rows = cur.fetchall()
for row in rows:
    print(f"Timestamp: {row[1]} | Query: |{row[0]}|")
conn.close()
