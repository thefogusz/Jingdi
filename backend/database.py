import sqlite3
import datetime
import json
import os

DB_FILE = "stats.db"
STATE_FILE = "system_state.json"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            endpoint TEXT,
            query TEXT,
            latency_ms INTEGER,
            status TEXT,
            error_message TEXT,
            estimated_cost_usd REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id INTEGER,
            is_helpful BOOLEAN,
            reason TEXT,
            details TEXT,
            timestamp TEXT,
            FOREIGN KEY(log_id) REFERENCES api_logs(id)
        )
    ''')
    conn.commit()
    conn.close()

def log_request(endpoint: str, query: str, latency_ms: int, status: str, error_message: str = "", cost: float = 0.0) -> int:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO api_logs (timestamp, endpoint, query, latency_ms, status, error_message, estimated_cost_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, endpoint, query, latency_ms, status, error_message, cost))
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return log_id
    except Exception as e:
        print(f"Database logging error: {e}")
        return 0

def save_feedback(log_id: int, is_helpful: bool, reason: str = "", details: str = ""):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO user_feedback (log_id, is_helpful, reason, details, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (log_id, is_helpful, reason, details, timestamp))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Feedback logging error: {e}")

def get_dashboard_stats():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Total Requests
        cursor.execute("SELECT COUNT(*) FROM api_logs")
        total_requests = cursor.fetchone()[0]
        
        # Total Cost
        cursor.execute("SELECT SUM(estimated_cost_usd) FROM api_logs")
        total_cost = cursor.fetchone()[0] or 0.0
        
        # Success Rate
        cursor.execute("SELECT COUNT(*) FROM api_logs WHERE status = 'success'")
        success_count = cursor.fetchone()[0]
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 100
        
        # Recent Errors
        cursor.execute("SELECT timestamp, endpoint, error_message FROM api_logs WHERE status = 'error' ORDER BY id DESC LIMIT 5")
        recent_errors = [{"time": r[0], "endpoint": r[1], "error": r[2]} for r in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total_requests": total_requests,
            "total_cost_usd": round(float(total_cost), 4),
            "success_rate_percent": round(float(success_rate), 2),
            "recent_errors": recent_errors,
            "system_health": {
                "database": "Healthy",
                "gemini_api": "Healthy" if success_rate > 80 else "Degraded",
                "web_search": "Healthy"
            },
            "kill_switch_active": get_kill_switch(),
            "recent_traffic": get_recent_traffic(),
            "recent_feedback": get_recent_feedback()
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {
            "total_requests": 0, "total_cost_usd": 0, "success_rate_percent": 100,
            "recent_errors": [], "system_health": {"database": "Error", "gemini_api": "Unknown", "search": "Unknown"},
            "kill_switch_active": False, "recent_traffic": [], "recent_feedback": []
        }

def get_recent_feedback(limit: int = 15):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT f.timestamp, f.is_helpful, f.reason, f.details, a.query, a.endpoint
            FROM user_feedback f
            LEFT JOIN api_logs a ON f.log_id = a.id
            ORDER BY f.id DESC LIMIT ?
        ''', (limit,))
        
        feedback = []
        for r in cursor.fetchall():
            feedback.append({
                "time": r[0],
                "is_helpful": bool(r[1]),
                "reason": r[2] or "-",
                "details": r[3] or "-",
                "query": r[4] or "-",
                "endpoint": r[5] or "-"
            })
        conn.close()
        return feedback
    except Exception as e:
        print(f"Error fetching feedback: {e}")
        return []

def get_recent_traffic(limit: int = 20):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, endpoint, query, estimated_cost_usd, status
            FROM api_logs 
            ORDER BY id DESC LIMIT ?
        ''', (limit,))
        
        traffic = []
        for r in cursor.fetchall():
            traffic.append({
                "time": r[0],
                "endpoint": r[1],
                "query": r[2] if r[2] else "-",
                "cost": round(float(r[3] or 0), 6),
                "status": r[4]
            })
        conn.close()
        return traffic
    except Exception as e:
        print(f"Error fetching traffic: {e}")
        return []

def set_kill_switch(active: bool):
    with open(STATE_FILE, "w") as f:
        json.dump({"kill_switch_active": active}, f)

def get_kill_switch() -> bool:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                return state.get("kill_switch_active", False)
        except:
            return False
    return False

# Initialize on import
init_db()
