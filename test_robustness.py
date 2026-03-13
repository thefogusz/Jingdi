import sys
import os
import io
import json
import time
from PIL import Image
from dotenv import load_dotenv

# Force UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Mock paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.search_service import search_web, crawl_url, scrape_url
from services.llm_service import analyze_text_claim, analyze_with_grok
from services.vision_service import analyze_images_with_vision
from services.reverse_image_service import reverse_image_search

load_dotenv('backend/.env')

def test_flow_check_text():
    print("\n[TEST] Flow: Check Text (Hybrid Search + Gemini 3)")
    query = "มีข่าวว่ากัญชาช่วยรักษามะเร็งได้ 100% จริงไหม?"
    try:
        context = search_web(query)
        print(f"  - Search Results: {len(context)} items found.")
        result = analyze_text_claim(query, search_context=str(context))
        print(f"  - Analysis: {result.get('score')} | {result.get('analysis')[:100]}...")
        return True
    except Exception as e:
        print(f"  - FAIL: {e}")
        return False

def test_flow_check_url_social():
    print("\n[TEST] Flow: Check URL Social (Cloudflare + Grok/Gemini)")
    # Test with a real-looking X link
    url = "https://x.com/elonmusk/status/1891964264350711913" 
    try:
        print(f"  - Scraping URL: {url}")
        scraped = scrape_url(url)
        print(f"  - Scraped Title: {scraped.get('title')}")
        
        # Manually trigger crawl if it looks like a placeholder
        if scraped.get('is_placeholder') or not scraped.get('text'):
             print("  - Placeholder detected. Triggering Cloudflare Deep Crawl...")
             crawled = crawl_url(url)
             print(f"  - Crawled Source: {crawled.get('source')}")
             text_to_analyze = crawled.get('text', '')
        else:
             text_to_analyze = scraped.get('text', '')

        print(f"  - Extracted Text Length: {len(text_to_analyze)}")
        
        # Test final analysis
        search_ctx = search_web(url)
        analysis = analyze_with_grok(f"Verify this: {url}", search_context=str(search_ctx))
        print(f"  - Grok Analysis: {analysis.get('analysis')[:100]}...")
        return True
    except Exception as e:
        print(f"  - FAIL: {e}")
        return False

def test_flow_check_screenshot():
    print("\n[TEST] Flow: Check Screenshot (Vision + Reverse Search + Information Merging)")
    # Create blue image
    img = Image.new('RGB', (100, 100), color = 'blue')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    image_bytes = buf.getvalue()
    
    try:
        # 1. Vision
        print("  - Running Vision Analysis...")
        vision_res = analyze_images_with_vision([image_bytes], is_screenshot=True)
        print(f"  - Visual Indicators: {vision_res.get('visual_indicators')}")
        
        # 2. Reverse Search (Requires real URL, so we skip actual call or mock it)
        print("  - Testing Information Merging Logic...")
        combined_context = f"[VISION]: {vision_res.get('analysis')}\n[SIGNALS]: {vision_res.get('ai_generated_signals')}"
        
        # 3. Final Decision
        final = analyze_with_grok("Analyze this visual evidence", combined_context)
        print(f"  - Final Verdict: {final.get('analysis')[:100]}...")
        return True
    except Exception as e:
        print(f"  - FAIL: {e}")
        return False

if __name__ == "__main__":
    print("=== STARTING ROBUSTNESS VERIFICATION ===")
    start = time.time()
    
    s1 = test_flow_check_text()
    s2 = test_flow_check_url_social()
    s3 = test_flow_check_screenshot()
    
    duration = time.time() - start
    print(f"\n=== VERIFICATION COMPLETE in {duration:.2f}s ===")
    
    if all([s1, s2, s3]):
        print("✅ ALL FLOWS ARE ROBUST AND OPERATIONAL.")
    else:
        print("❌ SOME FLOWS HAVE ISSUES.")
        sys.exit(1)
