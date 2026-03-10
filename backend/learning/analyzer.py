import sys
import os
import json

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

def extract_learning_data(limit=50):
    """
    Extracts 'interesting' cases for the AI to learn from:
    1. Negative user feedback.
    2. Inconclusive scores (40-60).
    3. Errors.
    """
    data = {
        "negative_feedback": [],
        "inconclusive_cases": [],
        "errors": []
    }
    
    try:
        conn = database._get_conn()
        cur = conn.cursor()
        
        # 1. Negative Feedback
        database._execute(cur, '''
            SELECT f.timestamp, f.reason, f.details, a.query, a.endpoint, a.case_id, a.id
            FROM user_feedback f
            LEFT JOIN api_logs a ON f.log_id = a.id
            WHERE f.is_helpful = 0
            ORDER BY f.id DESC LIMIT %s
        ''', (limit,))
        for r in cur.fetchall():
            data["negative_feedback"].append({
                "time": r[0], "reason": r[1], "details": r[2],
                "query": r[3], "endpoint": r[4], "case_id": r[5], "log_id": r[6]
            })
            
        # 2. Inconclusive Cases (based on common query patterns or latency spikes)
        # Note: We don't store the 'score' directly in api_logs yet, 
        # but we can look for specific endpoints that often need escalation.
        database._execute(cur, '''
            SELECT timestamp, endpoint, query, latency_ms, status, case_id
            FROM api_logs
            WHERE status = 'success' AND (query LIKE '%?%' OR latency_ms > 5000)
            ORDER BY id DESC LIMIT %s
        ''', (limit,))
        for r in cur.fetchall():
            data["inconclusive_cases"].append({
                "time": r[0], "endpoint": r[1], "query": r[2],
                "latency": r[3], "status": r[4], "case_id": r[5]
            })
            
        # 3. Actual Errors
        database._execute(cur, '''
            SELECT timestamp, endpoint, query, error_message, case_id
            FROM api_logs
            WHERE status = 'error'
            ORDER BY id DESC LIMIT %s
        ''', (limit,))
        for r in cur.fetchall():
            data["errors"].append({
                "time": r[0], "endpoint": r[1], "query": r[2],
                "error": r[3], "case_id": r[4]
            })
            
        cur.close()
        conn.close()
        return data
    except Exception as e:
        print(f"Extraction error: {e}")
        return data

if __name__ == "__main__":
    results = extract_learning_data()
    print(json.dumps(results, indent=2, ensure_ascii=False))
