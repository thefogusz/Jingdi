import database
import os
from dotenv import load_dotenv
load_dotenv()

def check_stats():
    stats = database.get_dashboard_stats()
    print(f"R2 Public URL in stats: {stats.get('r2_public_url')}")
    print(f"R2 Bucket in stats: {stats.get('r2_bucket')}")

if __name__ == "__main__":
    check_stats()
