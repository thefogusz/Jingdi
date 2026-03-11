"""
Reverse Image Search Service — Google Cloud Vision
=================================================
Uses Google Cloud Vision (WEB_DETECTION) to find the absolute earliest
occurrences of an image on the web, bypassing unreliable DDG/SerpApi.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
GOOGLE_CLOUD_API_KEY = os.environ.get("GOOGLE_CLOUD_API_KEY", "")

def google_cloud_vision_web_detection(image_url: str) -> dict:
    """
    Perform a reverse image search using Google Cloud Vision Web Detection.
    Args:
        image_url: The URL of the image (e.g., from Cloudflare R2).
    Returns:
        A dictionary containing parsed web entities, full matching images, 
        and pages containing matching images.
    """
    if not image_url or not GOOGLE_CLOUD_API_KEY:
        print("[Vision API] Missing URL or API Key")
        return {"entities": [], "matching_pages": []}

    print(f"\n[Vision API] Searching Google Vision with Image URL: {image_url}")
    
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
            
            # Extract Web Entities (What Google thinks the image is about)
            entities = []
            for entity in web_detection.get("webEntities", []):
                if entity.get("description"):
                    entities.append(entity["description"])
            
            # Extract pages where the image was found
            matching_pages = []
            for page in web_detection.get("pagesWithMatchingImages", []):
                if page.get("url"):
                    title = page.get("pageTitle", "Unknown Page")
                    # Clean up Google's weird formatting in titles if needed
                    matching_pages.append({
                        "url": page["url"],
                        "title": title,
                        "snippet": f"Image found on this page."
                    })
                    
            print(f"[Vision API] Found {len(entities)} entities, {len(matching_pages)} matching pages")
            return {
                "entities": entities,
                "matching_pages": matching_pages
            }
        else:
            print(f"[Vision API] Error status {response.status_code}: {response.text[:200]}")
            
    except Exception as e:
        print(f"[Vision API] Exception during search: {e}")
        
    return {"entities": [], "matching_pages": []}

def reverse_image_search(image_url: str, is_global: bool = False) -> dict:
    """
    Run Google Cloud Vision reverse search.
    Returns:
        pages   — list of {url, title, snippet}
        summary — Provenance text block for Gemini/Grok
    """
    if not image_url or not GOOGLE_CLOUD_API_KEY:
        return {"pages": [], "summary": "⚠️ Google Vision API Key missing or Invalid Image URL."}

    vision_results = google_cloud_vision_web_detection(image_url)
    pages = vision_results.get("matching_pages", [])
    entities = vision_results.get("entities", [])
    
    # We don't have search_query directly from Vision API like we did DDG
    search_query = " ".join(entities[:5]) if entities else "Unknown Image"

    summary = _build_summary(entities, pages)
    return {"pages": pages[:10], "summary": summary, "search_query": search_query}

def _build_summary(entities: list, pages: list) -> str:
    parts = []

    parts.append("🔍 **GOOGLE CLOUD VISION (WEB DETECTION) RESULTS:**")

    if entities:
        parts.append(f"🧠 **Web Entities (Identified Concepts):** {', '.join(entities[:10])}")

    if pages:
        parts.append(f"\n📰 **Found the exact image on {len(pages)} web pages:**")
        for i, p in enumerate(pages[:8], 1):
            title = p.get("title") or "Unnamed Page"
            parts.append(f"   {i}. [{title}]({p['url']})")
    else:
        parts.append("\n⚠️ **No exact image matches found on the public web.**")

    return "\n".join(parts)
