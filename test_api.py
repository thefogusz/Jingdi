import requests

def test_text(text):
    res = requests.post('http://localhost:8000/api/check-text', json={'text': text})
    try:
        data = res.json()
        print(f"Text: {text}")
        print(f"Score: {data.get('score')} - Sources length: {len(data.get('sources', []))}")
        print("---")
    except Exception as e:
        print(f"Failed to parse for {text}: {e}")

test_text('Elon Musk buys the moon.')
test_text('A new study claims eating 10kg of salt daily cures cancer')
