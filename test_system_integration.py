import sys
import os
import io
import json
from PIL import Image

# Force UTF-8 for Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.gemini_pool import get_next_client
from services.vision_service import analyze_images_with_vision
from services.llm_service import analyze_text_claim
from services.reverse_image_service import reverse_image_search
from dotenv import load_dotenv

load_dotenv('backend/.env')

def test_gemini_connection():
    print("--- Testing Gemini 3 Connection ---")
    client = get_next_client()
    if not client:
        print("FAILED: Failed to get Gemini client")
        return False
    try:
        # Simple test with gemini-3-flash-preview
        res = client.models.generate_content(model='gemini-3-flash-preview', contents="Hello, are you Gemini 3? Reply in Thai briefly.")
        print(f"PASS: Gemini 3 Response: {res.text.strip()}")
        return True
    except Exception as e:
        print(f"ERROR: Gemini 3 Error: {e}")
        return False

def test_vision_analysis():
    print("\n--- Testing Vision Analysis (Gemini 3) ---")
    # Create a small dummy red square image
    img = Image.new('RGB', (100, 100), color = 'red')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    image_bytes = buf.getvalue()
    
    try:
        result = analyze_images_with_vision([image_bytes])
        # Format JSON with ensure_ascii=False for Thai
        pretty_res = json.dumps(result, indent=2, ensure_ascii=False)
        print(f"PASS: Vision Analysis Result: {pretty_res}")
        return "analysis" in result
    except Exception as e:
        print(f"ERROR: Vision Analysis Error: {e}")
        return False

def test_reverse_search():
    print("\n--- Testing Google Reverse Search (Cloud Vision) ---")
    # Using a known public image URL for testing
    test_url = "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"
    try:
        result = reverse_image_search(test_url)
        summary = result.get('summary', '')
        print(f"PASS: Reverse Search Summary: {summary[:200]}...")
        return "summary" in result
    except Exception as e:
        print(f"ERROR: Reverse Search Error: {e}")
        return False

if __name__ == "__main__":
    c_ok = test_gemini_connection()
    v_ok = test_vision_analysis()
    r_ok = test_reverse_search()
    
    print("\n--- Final Test Summary ---")
    print(f"Gemini 3: {'PASS' if c_ok else 'FAIL'}")
    print(f"Vision Analysis: {'PASS' if v_ok else 'FAIL'}")
    print(f"Reverse Search: {'PASS' if r_ok else 'FAIL'}")
    
    if c_ok and v_ok and r_ok:
        print("\nALL SYSTEMS OPERATIONAL WITH GEMINI 3!")
    else:
        print("\nSOME SYSTEMS FAILED. Check logs above.")
        sys.exit(1)
