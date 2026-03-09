import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from services.search_service import search_web, extract_keywords

query = "อิหร่านเผชิญ ฝนสีดำ หลังอิสราเอลถล่มคลังน้ำมัน วันนี้ (8 มีนาคม) CNN รายงานบรรยากาศในกรุงเตหะราน"
kw = extract_keywords(query)
print("Keywords Extracted:", kw)
print("Search Results:", search_web(query))
