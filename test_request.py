import requests

url = "http://localhost:8000/api/check-text"
payload = {
    "text": "ขุด Bitcoin จากอวกาศ! CEO Starcloud ประกาศแผนสุดบ้าที่ไม่เคยมีใครทำมาก่อน",
    "has_image": False
}
try:
    res = requests.post(url, json=payload, timeout=30)
    print("Status:", res.status_code)
    try:
        import json
        with open("response.json", "w", encoding="utf-8") as f:
            json.dump(res.json(), f, indent=2, ensure_ascii=False)
        print("Saved to response.json")
    except Exception as je:
        print("JSON parse error:", je)
except Exception as e:
    print("Error:", e)
