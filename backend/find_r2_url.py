import sqlite3
import os

db_path = "d:/Work/Jingdi/backend/stats.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT query FROM api_logs WHERE query LIKE '%http%' LIMIT 50")
    results = cur.fetchall()
    for r in results:
        print(r[0])
    conn.close()
else:
    print("No stats.db found")
