import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

xai_key = os.getenv("XAI_API_KEY")
print(f"XAI Key found: {'Yes' if xai_key else 'No'}")

client = OpenAI(
    api_key=xai_key,
    base_url="https://api.x.ai/v1"
)

print("\n--- Available Models ---")
try:
    models = client.models.list()
    for m in models.data:
        print(f"  {m.id}")
except Exception as e:
    print(f"Error listing models: {e}")

# Try a quick call with likely model names
test_models = ["grok-2", "grok-2-1212", "grok-2-mini", "grok-3", "grok-3-mini", "grok-turbo"]
for model in test_models:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=5
        )
        print(f"\n✅ '{model}' works! -> {resp.choices[0].message.content}")
        break
    except Exception as e:
        print(f"❌ '{model}': {str(e)[:80]}")
