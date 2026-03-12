import os
import requests
import concurrent.futures
from bs4 import BeautifulSoup
from services.gemini_pool import get_next_client

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

def search_tavily(query: str, max_results: int = 10) -> list:
    """Search using Tavily AI Search API."""
    if not TAVILY_API_KEY:
        return []
    try:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
            "max_results": max_results,
        }
        res = requests.post("https://api.tavily.com/search", json=payload, timeout=10)
        if res.status_code != 200:
            print(f"[Tavily] Error {res.status_code}: {res.text[:100]}")
            return []
        data = res.json()
        results = []
        for item in data.get("results", []):
            pub_date = item.get("published_date", "")
            results.append({
                "title": item.get("title", ""),
                "link": item.get("url", ""),
                "snippet": item.get("content", "")[:300],
                "pub_date": pub_date
            })
        print(f"[Tavily] Found {len(results)} results for: {query[:60]}")
        return results
    except Exception as e:
        print(f"[Tavily] Exception: {e}")
        return []


def crawl_url(url: str) -> dict:
    """Crawl a URL using Tavily Extract API to bypass bot protection/login walls."""
    if not TAVILY_API_KEY:
        return {"text": "", "error": "Tavily API Key not configured"}
    try:
        print(f"[Crawl] Using Tavily Extract for: {url}")
        payload = {
            "api_key": TAVILY_API_KEY,
            "urls": [url]
        }
        res = requests.post("https://api.tavily.com/extract", json=payload, timeout=15)
        if res.status_code != 200:
            return {"text": "", "error": f"Tavily Error {res.status_code}"}
        
        data = res.json()
        results = data.get("results", [])
        if not results:
            return {"text": "", "error": "No content extracted"}
            
        # Extract the content (usually returned as Markdown or text)
        content = results[0].get("raw_content", "")
        title = results[0].get("title", "") or "Extracted Page"
        
        return {
            "title": title,
            "text": content[:10000],  # Limit to 10k chars
            "error": None
        }
    except Exception as e:
        print(f"[Crawl] Exception: {e}")
        return {"text": "", "error": str(e)}



def _run_gemini(client, prompt: str) -> str:
    """Run gemini with automatic flash-lite fallback on rate limit."""
    try:
        res = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            res = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        else:
            raise e
    return res.text.strip().replace('"', '')


def extract_keywords(query: str) -> str:
    """Extract Thai-language search keywords (or mixed) from the query."""
    if len(query) < 20:
        return query
    try:
        client = get_next_client()
        if not client:
            return query[:50]
        prompt = f"""Extract 3-4 highly specific search keywords from this text.
        - If the text contains Thai names, locations, or organizations (like 'ตร.บาหลี', 'Bright TV'), KEEP them in Thai.
        - DO NOT translate proper names or local events to English unless it's a globally dominant English topic.
        - Text: '{query}'

        Return ONLY the keywords separated by spaces."""
        return _run_gemini(client, prompt)
    except Exception:
        return query[:50]


def extract_english_keywords(query: str) -> str:
    """Extract English-language search keywords for international coverage.
    
    Uses Gemini when available, with a reliable regex fallback that pulls
    English words, company names, and tech terms directly from the query.
    This is the key to finding international English sources from Thai headlines.
    """
    import re

    # --- Regex fallback: always works, no Gemini needed ---
    # Extract all English word sequences (catches: "Bitcoin", "Starcloud CEO", "SpaceX", etc.)
    english_tokens = re.findall(r'[A-Za-z][A-Za-z0-9]+(?:\s+[A-Za-z][A-Za-z0-9]+)*', query)
    regex_keywords = ' '.join(english_tokens[:6])  # first 6 tokens

    if len(query) < 10:
        return regex_keywords or query

    try:
        client = get_next_client()
        if not client:
            return regex_keywords or query[:50]
        prompt = f"""Translate and extract 4-6 concise English search keywords from this text.
        - Always output in English only.
        - Extract proper nouns, company names, technical terms, and key concepts.
        - Focus on making keywords that would find international news sources (CNN, BBC, Reuters, TechCrunch, PCMag etc.)
        - Text: '{query}'

        Return ONLY the English keywords separated by spaces."""
        result = _run_gemini(client, prompt)
        # Verify Gemini actually returned English (not Thai fallback)
        english_chars = len(re.findall(r'[A-Za-z]', result))
        thai_chars = len(re.findall(r'[\u0e00-\u0e7f]', result))
        if thai_chars > english_chars:
            # Gemini returned Thai - use regex fallback instead
            return regex_keywords or result
        return result
    except Exception:
        return regex_keywords  # Always return something useful



def search_wikipedia(query: str) -> list:
    """Fetch a quick summary from Wikipedia REST API for background context."""
    try:
        keywords = extract_keywords(query)
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={keywords}&utf8=&format=json&srlimit=1"
        res = requests.get(url, timeout=5)
        data = res.json()
        sources = []
        if 'query' in data and data['query']['search']:
            item = data['query']['search'][0]
            clean_snippet = BeautifulSoup(item['snippet'], "html.parser").get_text()
            sources.append({
                "title": f"Wikipedia: {item['title']}",
                "link": f"https://en.wikipedia.org/wiki/{item['title'].replace(' ', '_')}",
                "snippet": clean_snippet
            })
        return sources
    except Exception:
        return []


def search_google_news(query: str, lang: str = 'th', country: str = 'TH') -> list:
    """Fetch the latest headlines from Google News RSS."""
    try:
        from urllib.parse import quote_plus
        keywords = extract_keywords(query) if lang == 'th' else extract_english_keywords(query)
        if not keywords:
            return []
        encoded_query = quote_plus(keywords)
        ceid = f"{country}:{lang}"
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang}&gl={country}&ceid={ceid}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=5, verify=False)
        soup = BeautifulSoup(res.content, "xml")
        sources = []
        items = soup.find_all("item", limit=3)
        for item in items:
            title = item.title.text if item.title else ""
            link = item.link.text if item.link else ""
            pub_date = item.pubDate.text if item.pubDate else ""
            sources.append({
                "title": f"ข่าวล่าสุด: {title}",
                "link": link,
                "snippet": f"รายงานเมื่อ: {pub_date}"
            })
        return sources
    except Exception as e:
        print(f"Google News RSS Error ({lang}): {e}")
        return []


def _search_ddg(query: str, region: str = 'wt-wt', max_results: int = 10) -> list:
    """Helper to run DuckDuckGo search in a thread."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region=region, max_results=max_results))
            return [
                {
                    "title": item.get("title", ""),
                    "link": item.get("url") or item.get("href", ""),
                    "snippet": item.get("body", ""),
                    "pub_date": item.get("published", "") # DDG sometimes provides this
                }
                for item in results
            ]
    except Exception as e:
        print(f"[DDG] Error ({region}): {e}")
        return []

def search_social_context(query: str) -> list:
    """Search social media platforms (Reddit, X, FB, TikTok) for free using DDG site operators."""
    platforms = ["reddit.com", "x.com", "facebook.com", "tiktok.com"]
    social_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # We search with "comments" or "replies" to trigger discussion-heavy results
        futures = {
            executor.submit(_search_ddg, f"{query} (comments OR replies OR discussion) site:{platform}", 'wt-wt', 5): platform
            for platform in platforms
        }
        
        for future in concurrent.futures.as_completed(futures):
            platform = futures[future]
            try:
                results = future.result()
                for item in results:
                    item["source_platform"] = platform
                    social_results.append(item)
            except Exception as e:
                print(f"[Social Search] Error for {platform}: {e}")
                
    return social_results

def search_web(query: str) -> list:
    """Search the web using Thai + English keywords in parallel across multiple engines (Tavily + DDG)."""
    try:
        # Extract BOTH Thai and English keywords simultaneously
        thai_keywords = extract_keywords(query)
        english_keywords = extract_english_keywords(query)

        # 0. Source-Aware Enhancement
        known_sources = {
            "bright tv": "site:brighttv.co.th",
            "ไทยรัฐ": "site:thairath.co.th",
            "thairath": "site:thairath.co.th",
            "ข่าวสด": "site:khaosod.co.th",
            "khaosod": "site:khaosod.co.th",
            "มติชน": "site:matichon.co.th",
            "matichon": "site:matichon.co.th",
            "เดลินิวส์": "site:dailynews.co.th",
            "dailynews": "site:dailynews.co.th",
            "pptv": "site:pptvhd36.com"
        }

        target_site = ""
        for name, site in known_sources.items():
            if name in query.lower() or site.replace("site:", "") in query.lower():
                target_site = site
                break

        # 1. Start with Wikipedia & News (Fast pre-checks)
        sources = search_wikipedia(query)
        
        news_rss_th = search_google_news(query, lang='th', country='TH')
        sources.extend(news_rss_th)

        if english_keywords:
            news_rss_en = search_google_news(query, lang='en', country='US')
            sources.extend(news_rss_en)

        seen_links = {s['link'] for s in sources}

        # 2. Parallel AI Search (Tavily) + Privacy Search (DuckDuckGo)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            
            # A) Tavily AI Search
            if TAVILY_API_KEY:
                futures[executor.submit(search_tavily, thai_keywords, 8)] = "Tavily-TH"
                if english_keywords:
                    futures[executor.submit(search_tavily, english_keywords, 8)] = "Tavily-EN"
            
            # B) DuckDuckGo (Free/Scraped)
            ddg_thai_query = f"{target_site} {thai_keywords}" if target_site else thai_keywords
            futures[executor.submit(_search_ddg, ddg_thai_query, 'th-th', 10)] = "DDG-TH"
            if english_keywords:
                futures[executor.submit(_search_ddg, english_keywords, 'wt-wt', 10)] = "DDG-EN"
            
            # C) Social Media Context (Free)
            futures[executor.submit(search_social_context, thai_keywords)] = "Social-TH"

            # Collect results as they arrive
            for future in concurrent.futures.as_completed(futures):
                name = futures[future]
                try:
                    results = future.result(timeout=10)
                    for item in results:
                        link = item.get("link")
                        if link and link not in seen_links:
                            sources.append(item)
                            seen_links.add(link)
                except Exception as e:
                    print(f"[{name}] Task error: {e}")

        return sources[:15]
    except Exception as e:
        print(f"Search API Error: {e}")
        return [{"title": "Search Failed", "link": "#", "snippet": str(e)}]




SOCIAL_MEDIA_DOMAINS = {
    "facebook.com", "fb.com", "fb.watch",
    "instagram.com", "twitter.com", "x.com",
    "tiktok.com",
}

def _is_social_url(url: str) -> bool:
    """Check if URL is from a social media platform that blocks scraping."""
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        return any(host == d or host.endswith("." + d) for d in SOCIAL_MEDIA_DOMAINS)
    except Exception:
        return False


def scrape_url(url: str) -> dict:
    """Scrape basic text content from a URL.
    
    - Strips tracking params (fbclid, aem_*, utm_*) before fetching.
    - Falls back to og:description meta tag when <p> body is empty.
    - For social media URLs (Facebook, Instagram, Twitter, TikTok) that
      require login/JS, returns is_social_url=True so the caller can use
      Grok's native web browsing instead of direct scraping.
    """
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

    TRACKING_PARAMS = {"fbclid", "utm_source", "utm_medium", "utm_campaign",
                       "utm_term", "utm_content", "ref", "_fb_noscript"}
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        cleaned_qs = {k: v for k, v in qs.items()
                      if k not in TRACKING_PARAMS and not k.startswith("aem_")}
        cleaned_url = urlunparse(parsed._replace(query=urlencode(cleaned_qs, doseq=True)))
    except Exception:
        cleaned_url = url

    # Social media: skip scraping entirely, caller will use Grok
    if _is_social_url(cleaned_url):
        print(f"[scrape_url] Social media URL detected, skipping direct scrape: {cleaned_url}")
        return {
            "title": "Social Media Post",
            "text": "",
            "cleaned_url": cleaned_url,
            "is_social_url": True,
        }

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(cleaned_url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        title = soup.title.string.strip() if soup.title else ""
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text() for p in paragraphs]).strip()

        if len(text) < 100:
            og_title = soup.find("meta", property="og:title")
            og_desc = soup.find("meta", property="og:description")
            if og_title and not title:
                title = og_title.get("content", "").strip()
            if og_desc:
                og_text = og_desc.get("content", "").strip()
                if og_text:
                    text = og_text

        return {"title": title, "text": text[:5000], "cleaned_url": cleaned_url, "is_social_url": False}
    except Exception as e:
        return {"error": str(e), "text": "", "title": "", "cleaned_url": cleaned_url, "is_social_url": False}

