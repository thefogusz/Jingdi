import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from services.search_service import search_web
from services.llm_service import analyze_with_grok

# This simulates the EXACT user query that failed previously
query = "Bright TV ตร.บาหลีรวบแก๊งอุ้มฆ่า 'อิกอร์' ยัน DNA มัดชัดชิ้นส่วนมนุษย์เกลื่อนหาด ล่าหมายแดงอีก 6 ราย"

print("Step 1: Running High-Recall Search...")
search_results = search_web(query)
print(f"Found {len(search_results)} potential sources.")
for i, s in enumerate(search_results[:3]):
    print(f"[{i}] {s['title']} -> {s['link']}")

print("\nStep 2: Processing with Grok (this uses the updated source-trusting prompt)...")
# We test just the search recall first to see if Bright TV is in the mix
bright_tv_found = any("facebook.com" in s['link'] and "brighttv" in s['link'].lower() for s in search_results)
instagram_found = any("instagram.com" in s['link'] and "brighttv" in s['link'].lower() for s in search_results)

if bright_tv_found or instagram_found:
    print("SUCCESS: Search found the official social media posts from Bright TV.")
else:
    print("FAILURE: Search still missed the official social media posts.")
