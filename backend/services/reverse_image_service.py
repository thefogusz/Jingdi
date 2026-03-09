"""
Reverse Image Search Service — DDG Image Search
=================================================
Runs DuckDuckGo image search using keywords provided by the caller
(already extracted by Gemini Vision in vision_service.py).

No second Gemini Vision call here — keywords come from vision_result.
"""

import io
import json
from PIL import Image


def ddg_image_search(query: str) -> list:
    """
    Search DuckDuckGo images for the given query.
    Returns source page URLs of news sites using similar images.
    Uses the same duckduckgo_search library already installed — no API key needed.

    Returns: [{"url": str, "title": str, "snippet": str}, ...]
    """
    if not query.strip():
        return []
    try:
        from duckduckgo_search import DDGS
        results = []
        seen_urls = set()

        with DDGS() as ddgs:
            for item in ddgs.images(query, max_results=15):
                page_url = item.get("url", "")
                title    = item.get("title", "")
                source   = item.get("source", "")

                if page_url and page_url not in seen_urls:
                    results.append({
                        "url":     page_url,
                        "title":   title or source,
                        "snippet": source,
                    })
                    seen_urls.add(page_url)

        return results[:10]

    except Exception as e:
        print(f"[DDG Image Search] Error: {e}")
        return []


def reverse_image_search(keywords: list, is_global: bool = False) -> dict:
    """
    Run DuckDuckGo image search with the provided keywords.
    Keywords are extracted by Gemini Vision in vision_service.py (one Gemini call).

    Returns:
        pages   — list of {url, title, snippet}
        summary — Grok-ready provenance text block
    """
    if not keywords:
        return {"pages": [], "summary": ""}

    search_query = " ".join(keywords[:6])
    pages = ddg_image_search(search_query)

    summary = _build_summary(keywords, is_global, pages, search_query)
    return {"pages": pages, "summary": summary, "search_query": search_query}


def _build_summary(keywords: list, is_global: bool, pages: list, search_query: str) -> str:
    parts = []

    if is_global:
        parts.append("🌐 INTERNATIONAL / GLOBAL story — search in ENGLISH.")
    else:
        parts.append("🇹🇭 Possibly LOCAL Thai story — search Thai + English sources.")

    if keywords:
        parts.append(f'🔑 English keywords from image: {", ".join(keywords)}')
        parts.append(f'   → DuckDuckGo image search query: "{search_query}"')

    if pages:
        parts.append(f'\n📰 DuckDuckGo image search found {len(pages)} page(s) using similar images:')
        for i, p in enumerate(pages[:6], 1):
            title = p.get("title") or p["url"]
            parts.append(f'   {i}. [{title}]({p["url"]})')
    else:
        parts.append("\n⚠️ No URL matches found via DuckDuckGo image search.")

    return "\n".join(parts)
