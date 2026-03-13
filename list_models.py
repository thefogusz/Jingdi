import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from services.gemini_pool import get_next_client
from dotenv import load_dotenv

load_dotenv('backend/.env')

def list_models():
    client = get_next_client()
    if not client:
        print("Failed to get client")
        return
    
    try:
        print("Listing available models...")
        for model in client.models.list():
            print(f"Name: {model.name}, DisplayName: {model.display_name}, Supported: {model.supported_actions}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
