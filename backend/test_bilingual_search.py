import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\GUS\backend')

from dotenv import load_dotenv
load_dotenv(r'D:\GUS\backend\.env')
from services.search_service import extract_keywords, extract_english_keywords, search_web

query = 'ขุด Bitcoin จากอวกาศ! CEO Starcloud ประกาศแผนสุดบ้าที่ไม่เคยมีใครทำมาก่อน'
print('Thai keywords:', extract_keywords(query))
print('English keywords:', extract_english_keywords(query))
results = search_web(query)
print(f'Total sources: {len(results)}')
for r in results[:6]:
    print('-', r['title'][:80])
    print('  ', r['link'][:80])
