import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from services.search_service import search_web, extract_keywords

query = "ตร.บาหลีรวบแก๊งอุ้มฆ่า 'อิกอร์' ยัน DNA มัดชัดชิ้นส่วนมนุษย์เกลื่อนหาด ล่าหมายแดงอีก 6 ราย"
kw = extract_keywords(query)
print("Keywords Extracted:", kw)
print("Search Results:", search_web(query))
