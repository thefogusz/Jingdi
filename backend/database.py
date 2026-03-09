import os
import datetime
import json

# ─── PostgreSQL via psycopg2 ───────────────────────────────────────────────
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL")  # Railway injects this automatically

def _is_sqlite():
    return not DATABASE_URL

def _get_conn():
    if _is_sqlite():
        # Fallback to sqlite if no Postgres URL is provided
        import sqlite3
        return sqlite3.connect("stats.db")
    
    return psycopg2.connect(DATABASE_URL)

def _execute(cur, query: str, args=None):
    if _is_sqlite():
        query = query.replace('%s', '?').replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
    if args:
        cur.execute(query, args)
    else:
        cur.execute(query)


def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    _execute(cur, '''
        CREATE TABLE IF NOT EXISTS api_logs (
            id SERIAL PRIMARY KEY,
            timestamp TEXT,
            endpoint TEXT,
            query TEXT,
            latency_ms INTEGER,
            status TEXT,
            error_message TEXT,
            estimated_cost_usd REAL,
            case_id TEXT,
            api_name TEXT
        )
    ''')
    _execute(cur, '''
        CREATE TABLE IF NOT EXISTS user_feedback (
            id SERIAL PRIMARY KEY,
            log_id INTEGER,
            is_helpful BOOLEAN,
            reason TEXT,
            details TEXT,
            timestamp TEXT,
            FOREIGN KEY(log_id) REFERENCES api_logs(id)
        )
    ''')
    _execute(cur, '''
        CREATE TABLE IF NOT EXISTS system_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()


def log_request(endpoint: str, query: str, latency_ms: int, status: str,
                error_message: str = "", cost: float = 0.0,
                case_id: str = None, api_name: str = None) -> int:
    try:
        conn = _get_conn()
        cur = conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        
        query_str = '''
            INSERT INTO api_logs
                (timestamp, endpoint, query, latency_ms, status, error_message,
                 estimated_cost_usd, case_id, api_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        
        args = (timestamp, endpoint, query, latency_ms, status, error_message, cost, case_id, api_name)

        if _is_sqlite():
            _execute(cur, query_str, args)
            log_id = cur.lastrowid
        else:
            _execute(cur, query_str + " RETURNING id", args)
            log_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return log_id
    except Exception as e:
        print(f"Database logging error: {e}")
        return 0


def save_feedback(log_id: int, is_helpful: bool, reason: str = "", details: str = ""):
    try:
        conn = _get_conn()
        cur = conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        _execute(cur, '''
            INSERT INTO user_feedback (log_id, is_helpful, reason, details, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        ''', (log_id, is_helpful, reason, details, timestamp))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Feedback logging error: {e}")


def get_dashboard_stats():
    try:
        conn = _get_conn()
        cur = conn.cursor()

        _execute(cur, "SELECT COUNT(*) FROM api_logs WHERE status != 'info'")
        total_requests = cur.fetchone()[0]

        _execute(cur, "SELECT SUM(estimated_cost_usd) FROM api_logs")
        total_cost = cur.fetchone()[0] or 0.0

        _execute(cur, "SELECT COUNT(*) FROM api_logs WHERE status = 'success'")
        success_count = cur.fetchone()[0]
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 100

        _execute(cur, """
            SELECT timestamp, endpoint, error_message
            FROM api_logs WHERE status = 'error'
            ORDER BY id DESC LIMIT 5
        """)
        recent_errors = [{"time": r[0], "endpoint": r[1], "error": r[2]}
                         for r in cur.fetchall()]

        _execute(cur, """
            SELECT endpoint, COUNT(*), SUM(estimated_cost_usd)
            FROM api_logs GROUP BY endpoint
        """)
        api_breakdown = [
            {"endpoint": r[0], "requests": r[1], "cost": round(float(r[2] or 0), 4)}
            for r in cur.fetchall()
        ]

        _execute(cur, """
            SELECT api_name, COUNT(*), SUM(estimated_cost_usd)
            FROM api_logs
            WHERE api_name IS NOT NULL AND api_name != ''
            GROUP BY api_name
            ORDER BY SUM(estimated_cost_usd) DESC
        """)
        api_brand_totals = [
            {"brand": r[0], "calls": r[1], "cost": round(float(r[2] or 0), 4)}
            for r in cur.fetchall()
        ]

        cur.close()
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
            "recent_feedback": get_recent_feedback(),
            "api_breakdown": api_breakdown,
            "api_brand_totals": api_brand_totals,
            "cases": get_cases_api_breakdown()
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {
            "total_requests": 0, "total_cost_usd": 0, "success_rate_percent": 100,
            "recent_errors": [], "system_health": {"database": "Error", "gemini_api": "Unknown", "web_search": "Unknown"},
            "kill_switch_active": False, "recent_traffic": [], "recent_feedback": []
        }


def get_recent_feedback(limit: int = 15):
    try:
        conn = _get_conn()
        cur = conn.cursor()
        _execute(cur, '''
            SELECT f.timestamp, f.is_helpful, f.reason, f.details, a.query, a.endpoint
            FROM user_feedback f
            LEFT JOIN api_logs a ON f.log_id = a.id
            ORDER BY f.id DESC LIMIT %s
        ''', (limit,))
        feedback = []
        for r in cur.fetchall():
            feedback.append({
                "time": r[0], "is_helpful": bool(r[1]),
                "reason": r[2] or "-", "details": r[3] or "-",
                "query": r[4] or "-", "endpoint": r[5] or "-"
            })
        cur.close()
        conn.close()
        return feedback
    except Exception as e:
        print(f"Error fetching feedback: {e}")
        return []


def get_recent_traffic(limit: int = 20):
    try:
        conn = _get_conn()
        cur = conn.cursor()
        _execute(cur, '''
            SELECT timestamp, endpoint, query, estimated_cost_usd, status
            FROM api_logs
            WHERE (case_id IS NULL OR case_id = '') AND (api_name IS NULL OR api_name = '')
            ORDER BY id DESC LIMIT %s
        ''', (limit,))
        traffic = []
        for r in cur.fetchall():
            traffic.append({
                "time": r[0], "endpoint": r[1],
                "query": r[2] if r[2] else "-",
                "cost": round(float(r[3] or 0), 6),
                "status": r[4]
            })
        cur.close()
        conn.close()
        return traffic
    except Exception as e:
        print(f"Error fetching traffic: {e}")
        return []


def get_cases_api_breakdown(limit: int = 20):
    try:
        conn = _get_conn()
        cur = conn.cursor()
        _execute(cur, '''
            SELECT case_id, MIN(timestamp), MAX(timestamp),
                   SUM(estimated_cost_usd),
                   MAX(CASE WHEN status='success' THEN 1 ELSE 0 END),
                   MAX(query)
            FROM api_logs
            WHERE case_id IS NOT NULL AND case_id != ''
            GROUP BY case_id
            ORDER BY MIN(timestamp) DESC
            LIMIT %s
        ''', (limit,))
        cases_raw = cur.fetchall()

        cases = []
        for row in cases_raw:
            case_id, ts_start, ts_end, total_cost, succeeded, query = row
            _execute(cur, '''
                SELECT api_name, status, estimated_cost_usd
                FROM api_logs WHERE case_id = %s ORDER BY id ASC
            ''', (case_id,))
            apis = [
                {"name": r[0] or "Unknown", "status": r[1],
                 "cost": round(float(r[2] or 0), 4)}
                for r in cur.fetchall()
            ]
            cases.append({
                "case_id": case_id, "time": ts_start,
                "query": query or "-", "apis": apis,
                "total_cost": round(float(total_cost or 0), 4),
                "success": bool(succeeded)
            })
        cur.close()
        conn.close()
        return cases
    except Exception as e:
        print(f"Error fetching case breakdown: {e}")
        return []


def set_kill_switch(active: bool):
    try:
        conn = _get_conn()
        cur = conn.cursor()
        _execute(cur, '''
            INSERT INTO system_state (key, value) VALUES ('kill_switch', %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        ''', (json.dumps(active),))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Kill switch error: {e}")


def get_kill_switch() -> bool:
    try:
        conn = _get_conn()
        cur = conn.cursor()
        _execute(cur, "SELECT value FROM system_state WHERE key = 'kill_switch'")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return json.loads(row[0]) if row else False
    except Exception:
        return False


# Initialize on import
try:
    init_db()
except Exception as e:
    print(f"Failed to initialize database: {e}")
