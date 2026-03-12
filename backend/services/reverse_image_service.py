"""
Reverse Image Search Service — Google Cloud Vision
=================================================
Uses Google Cloud Vision (WEB_DETECTION) to find occurrences of an image on the web.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
GOOGLE_CLOUD_API_KEY = os.environ.get("GOOGLE_CLOUD_API_KEY", "")

def google_cloud_vision_web_detection(image_url: str) -> dict:
    if not image_url or not GOOGLE_CLOUD_API_KEY:
        return {"entities": [], "matching_pages": []}

    url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_CLOUD_API_KEY}"
    payload = {
        "requests": [
            {
                "image": {"source": {"imageUri": image_url}},
                "features": [{"type": "WEB_DETECTION", "maxResults": 15}]
            }
        ]
    }

    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code == 200:
            data = response.json()
            if not data.get("responses"):
                return {"entities": [], "matching_pages": []}
            web_detection = data["responses"][0].get("webDetection", {})
            entities = [entity["description"] for entity in web_detection.get("webEntities", []) if entity.get("description")]
            matching_pages = []
            for page in web_detection.get("pagesWithMatchingImages", []):
                if page.get("url"):
                    matching_pages.append({
                        "url": page["url"],
                        "title": page.get("pageTitle", "Unknown Page"),
                        "snippet": "Image found on this page.",
                        "pub_date": page.get("published_date", "") # Sometimes available in specific API versions
                    })
            return {"entities": entities, "matching_pages": matching_pages}
    except Exception as e:
        print(f"[Vision API] Exception: {e}")
    return {"entities": [], "matching_pages": []}

def reverse_image_search(image_url: str, is_global: bool = False) -> dict:
    if not image_url or not GOOGLE_CLOUD_API_KEY:
        return {"pages": [], "summary": "⚠️ Google Vision API Key missing."}

    vision_results = google_cloud_vision_web_detection(image_url)
    pages = vision_results.get("matching_pages", [])
    entities = vision_results.get("entities", [])
    search_query = " ".join(entities[:5]) if entities else "Unknown Image"
    summary = _build_summary(entities, pages)
    return {"pages": pages[:10], "summary": summary, "search_query": search_query}

def _build_summary(entities: list, pages: list) -> str:
    parts = ["🔍 **GOOGLE CLOUD VISION (WEB DETECTION) RESULTS:**"]
    if entities:
        parts.append(f"🧠 **Web Entities:** {', '.join(entities[:10])}")
    if pages:
        parts.append(f"\n📰 **Found the exact image on {len(pages)} web pages:**")
        for i, p in enumerate(pages[:8], 1):
            title = p.get("title") or "Unnamed Page"
            date_info = f" [{p['pub_date']}]" if p.get("pub_date") else ""
            parts.append(f"   {i}. [{title}]({p['url']}){date_info}")
    else:
        parts.append("\n⚠️ **No exact image matches found.**")
    return "\n".join(parts)
