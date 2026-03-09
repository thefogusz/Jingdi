import os
from google import genai

_keys = []
_index = 0

def init_pool():
    global _keys
    keys_str = os.getenv("GEMINI_API_KEYS")
    single_key = os.getenv("GEMINI_API_KEY")
    if keys_str:
        _keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    elif single_key:
        _keys = [single_key.strip()]

def get_next_client():
    global _index, _keys
    if not _keys:
        init_pool()
    
    if not _keys:
        return None
        
    key = _keys[_index % len(_keys)]
    _index += 1
    return genai.Client(api_key=key)
