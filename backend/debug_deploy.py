import os
import sys
import requests
import subprocess
from dotenv import load_dotenv

load_dotenv()

RENDER_API_KEY = os.getenv("RENDER_API")
RENDER_SERVICE_ID = "srv-d6nkp1nkijhs739mp1k0" # Jingdi Backend

def get_render_logs():
    """Fetch recent logs from Render using the API."""
    if not RENDER_API_KEY:
        return "RENDER_API key is missing in .env"
    
    # Render API for logs (using the service events or current output)
    # Note: Render doesn't have a direct 'logs' endpoint like Vercel, 
    # but we can get deployment logs or use the log stream if needed.
    # For now, we'll fetch the latest service events which often contain log summaries.
    url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/events"
    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Accept": "application/json"
    }
    
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            events = r.json()
            output = "--- Render Recent Events ---\n"
            for item in events[:10]:
                event = item.get("event", {})
                timestamp = event.get("timestamp", "N/A")
                etype = event.get("type", "Unknown")
                details = event.get("details", {})
                msg = details.get("deployStatus") or details.get("buildStatus") or etype
                output += f"[{timestamp}] {etype}: {msg}\n"
            return output
        else:
            return f"Error fetching Render events: {r.status_code} {r.text}"
    except Exception as e:
        return f"Exception fetching Render logs: {e}"

def get_vercel_logs():
    """Fetch logs using Vercel CLI."""
    try:
        # We use cmd /c for Windows execution policy issues
        result = subprocess.run(
            ["cmd", "/c", "vercel", "logs", "--limit", "20"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.getcwd(), "..") # Run from root
        )
        if result.returncode == 0:
            return "--- Vercel Recent Logs ---\n" + result.stdout
        else:
            return "--- Vercel Logs Error ---\n" + result.stderr + "\nNote: Make sure you ran 'vercel login' and 'vercel link'."
    except Exception as e:
        return f"Exception running Vercel CLI: {e}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1].lower()
        if target == "render":
            print(get_render_logs())
        elif target == "vercel":
            print(get_vercel_logs())
        else:
            print("Usage: python debug_deploy.py [render|vercel]")
    else:
        print(get_render_logs())
        print("\n")
        print(get_vercel_logs())
