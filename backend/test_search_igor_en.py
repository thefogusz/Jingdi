import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from services.search_service import search_web, extract_keywords

# Testing with English keywords to see if recall improves for Bali news
query = "Bali police murder Igor DNA human parts"
print("Keywords Extracted:", extract_keywords(query))
print("Search Results:", search_web(query))
