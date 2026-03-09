import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from services.search_service import search_web, extract_keywords

# Search specifically for Bright TV's coverage to see if it's findable
query = "Bright TV ตร.บาหลีรวบแก๊งอุ้มฆ่า 'อิกอร์'"
print("Keywords Extracted:", extract_keywords(query))
print("Search Results:", search_web(query))
