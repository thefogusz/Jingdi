import sys
import io
import os
from dotenv import load_dotenv
from google import genai

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
load_dotenv()

keys_str = os.getenv("GEMINI_API_KEYS")
keys = [k.strip() for k in keys_str.split(",")] if keys_str else []

print(f"Testing {len(keys)} keys...")
for i, key in enumerate(keys):
    print(f"--- Key {i} ---")
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents="say hello"
        )
        print("Success:", response.text.strip())
    except Exception as e:
        print("Error:", str(e))
