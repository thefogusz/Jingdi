import feedparser
import time
from bs4 import BeautifulSoup
import re

CACHE_TTL_SECONDS = 3600 * 2  # Cache feeds for 2 hours
_rss_cache = []
_last_fetch_time = 0

RSS_FEEDS = [
    {"name": "AFP Fact Check (TH)", "url": "https://factcheckthailand.afp.com/rss"},
    {"name": "Fact Crescendo (TH)", "url": "https://th.factcrescendo.com/feed/"},
    {"name": "Reuters Fact Check", "url": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best"},
    {"name": "Snopes", "url": "https://www.snopes.com/feed/"}
]

def clean_html(raw_html: str) -> str:
    if not raw_html: return ""
    return BeautifulSoup(raw_html, "html.parser").get_text(separator=" ").strip()

import concurrent.futures
import socket

def _fetch_single_feed(feed: dict) -> list:
    """Fetch and parse a single feed."""
    articles = []
    try:
        # Prevent feedparser from hanging indefinitely on slow servers
        socket.setdefaulttimeout(3.0) 
        parsed = feedparser.parse(feed["url"])
        if parsed.bozo and getattr(parsed.bozo_exception, 'getMessage', lambda: '')() != 'mismatched tag':
             pass # Some minor bozo formatting errors are fine, but ignore severe ones
        
        for entry in parsed.entries[:15]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
            
            if title and link:
                articles.append({
                    "source": feed["name"],
                    "title": title,
                    "link": link,
                    "summary": summary[:300] + "..." if len(summary) > 300 else summary
                })
    except Exception as e:
        print(f"Error fetching RSS {feed['name']}: {e}")
    
    return articles

def fetch_all_feeds() -> list:
    """Fetch and parse all RSS feeds concurrently into a standard format."""
    articles = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(RSS_FEEDS)) as executor:
        futures = {executor.submit(_fetch_single_feed, feed): feed for feed in RSS_FEEDS}
        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
                if res:
                    articles.extend(res)
            except Exception as exc:
                print(f"Feed generated an exception: {exc}")
                
    return articles

def get_cached_rss() -> list:
    """Get articles from cache, fetch if expired."""
    global _rss_cache, _last_fetch_time
    now = time.time()
    if not _rss_cache or (now - _last_fetch_time) > CACHE_TTL_SECONDS:
        print("[RSS] Fetching fresh RSS feeds...")
        _rss_cache = fetch_all_feeds()
        _last_fetch_time = now
    return _rss_cache

def search_rss_precheck(query: str, keywords: str) -> list:
    """
    Check if the user query or keywords strongly match any recent fact-checks in the RSS feeds.
    Returns matched articles to inject into LLM as priority context.
    """
    articles = get_cached_rss()
    if not articles:
        return []

    # Prepare search tokens (lowercased)
    tokens = [t.lower() for t in keywords.split() if len(t) >= 3]
    if not tokens:
        tokens = [t.lower() for t in query.split() if len(t) >= 4]

    matches = []
    for article in articles:
        text_to_search = (article["title"] + " " + article["summary"]).lower()
        
        # Count how many keyword tokens are in the article text
        match_count = sum(1 for token in tokens if token in text_to_search)
        
        # If we match at least 2 strong tokens (or 1 if there's only 1 token)
        required_matches = min(2, len(tokens))
        if match_count >= required_matches and required_matches > 0:
            matches.append(article)
    
    # Return top 3 strongest matches
    return matches[:3]

