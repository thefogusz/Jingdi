import os
import requests
import concurrent.futures
from bs4 import BeautifulSoup
from services.gemini_pool import get_next_client
import database

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "") # Reusing existing account ID variable name if set
if not CLOUDFLARE_ACCOUNT_ID:
    CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")

def search_tavily(query: str, max_results: int = 10, case_id: str = None) -> list:
    """Search using Tavily AI Search API — extracts full content, no scraping needed."""
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
            results.append({
                "title": item.get("title", ""),
                "link": item.get("url", ""),
                "snippet": item.get("content", "")[:300],
            })
        print(f"[Tavily] Found {len(results)} results for: {query[:60]}")
        if case_id:
            database.log_request("[API] Tavily AI Search", query[:100], 0, "info", cost=0.0001, case_id=case_id, api_name="Tavily")
        return results
    except Exception as e:
        print(f"[Tavily] Exception: {e}")
        return []



def _run_gemini(client, prompt: str) -> str:
    """Run gemini with automatic flash-lite fallback on rate limit."""
    try:
        res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            res = client.models.generate_content(model='gemini-2.5-flash-lite', contents=prompt)
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


def search_web(query: str, case_id: str = None) -> list:
    """Search the web using Thai + English keywords in parallel for maximum coverage."""
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

        if "facebook.com/share" in query.lower() or "fb.watch" in query.lower():
            if not target_site:
                thai_keywords = f"Facebook {thai_keywords}"

        # 1. Wikipedia (global context)
        sources = search_wikipedia(query)

        # 2. Google News Thai
        news_rss_th = search_google_news(query, lang='th', country='TH')
        sources.extend([s for s in news_rss_th if not any(e['link'] == s['link'] for e in sources)])

        # 2b. Google News English (catches international stories)
        if english_keywords:
            news_rss_en = search_google_news(query, lang='en', country='US')
            sources.extend([s for s in news_rss_en if not any(e['link'] == s['link'] for e in sources)])

        # 3. Tavily AI Search (Primary) — Thai & English in PARALLEL
        seen_links = {s['link'] for s in sources}

        if TAVILY_API_KEY:
            futures_map = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures_map['th'] = executor.submit(search_tavily, thai_keywords, 6, case_id)
                if english_keywords:
                    futures_map['en'] = executor.submit(search_tavily, english_keywords, 6, case_id)

            for key, future in futures_map.items():
                try:
                    for item in future.result(timeout=12):
                        if item["link"] and item["link"] not in seen_links:
                            sources.append(item)
                            seen_links.add(item["link"])
                except Exception as e:
                    print(f"[Tavily/{key}] Error: {e}")

        # Fallback: DuckDuckGo if Tavily key not set OR Tavily returned nothing
        if not TAVILY_API_KEY or len(sources) < 3:
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    if target_site:
                        try:
                            site_results = list(ddgs.text(f"{target_site} {thai_keywords}", region='th-th', max_results=5))
                            for item in site_results:
                                link = item.get("url") or item.get("href", "")
                                if link and link not in seen_links:
                                    sources.append({"title": item.get("title", ""), "link": link, "snippet": item.get("body", "")})
                                    seen_links.add(link)
                        except Exception:
                            pass

                    try:
                        gen_results = list(ddgs.text(thai_keywords, region='th-th', max_results=8))
                        for item in gen_results:
                            link = item.get("url") or item.get("href", "")
                            if link and link not in seen_links:
                                sources.append({"title": item.get("title", ""), "link": link, "snippet": item.get("body", "")})
                                seen_links.add(link)
                    except Exception:
                        pass

                    if english_keywords:
                        try:
                            en_results = list(ddgs.text(english_keywords, region='wt-wt', max_results=8))
                            for item in en_results:
                                link = item.get("url") or item.get("href", "")
                                if link and link not in seen_links:
                                    sources.append({"title": item.get("title", ""), "link": link, "snippet": item.get("body", "")})
                                    seen_links.add(link)
                        except Exception:
                            pass
            except Exception as e:
                print(f"[DDG Fallback] Error: {e}")

        return sources[:15]
    except Exception as e:
        print(f"Search API Error: {e}")
        return [{"title": "Search Failed", "link": "#", "snippet": str(e)}]



def _scrape_with_cloudflare(url: str) -> str:
    """Fallback scraper for JS-heavy sites using Cloudflare Browser Rendering API."""
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
        return ""
        
    try:
        scrape_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/browser-rendering/scrape"
        headers = {
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url,
            "elements": [{"id": "body", "selector": "body"}]
        }
        
        print(f"[Cloudflare Scraper] Attempting to scrape JS-rendered site: {url}")
        res = requests.post(scrape_url, headers=headers, json=payload, timeout=20)
        
        if res.status_code == 200:
            data = res.json()
            elements_data = data.get("result", [])
            if elements_data and isinstance(elements_data, list):
                results = elements_data[0].get("results", [])
                if results and isinstance(results, list):
                    html_content = results[0].get("html", "")
                    
                    if html_content:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        # Target common text containers first for cleaner extraction
                        paragraphs = soup.find_all(['p', 'h1', 'h2', 'h3', 'article', 'span', 'div'])
                        extracted_text = " ".join([p.get_text() for p in paragraphs]).strip()
                        
                        # Fallback to full body text if specific tags were empty
                        if len(extracted_text) < 100:
                            extracted_text = soup.get_text(separator=' ', strip=True)
                            
                            
                        print(f"[Cloudflare Scraper] Success. Extracted {len(extracted_text)} characters.")
                        import database
                        # Cloudflare Browser Rendering API pricing is $0.009 per response
                        database.log_request("[API] Cloudflare Scraper", url[:100], 0, "info", cost=0.009, case_id=None, api_name="Cloudflare")
                        return extracted_text
    except Exception as e:
        print(f"[Cloudflare Scraper] Error: {e}")
        
    return ""


def scrape_url(url: str) -> dict:
    """Scrape basic text content from a URL.
    
    Improvements:
    - Strips Facebook/tracking params (fbclid, aem_*, utm_*) before fetching
      so JS-rendered pages like UNILAD resolve cleanly.
    - Falls back to og:description meta tag when <p> body is empty
      (common for JS-heavy sites like UNILAD, Reddit, etc.).
    """
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

    # --- Strip known tracking/redirect params ---
    TRACKING_PARAMS = {"fbclid", "utm_source", "utm_medium", "utm_campaign",
                       "utm_term", "utm_content", "ref", "_fb_noscript"}
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        # Remove any param whose key starts with a tracking prefix OR is in the exact set
        cleaned_qs = {k: v for k, v in qs.items()
                      if k not in TRACKING_PARAMS and not k.startswith("aem_")}
        cleaned_url = urlunparse(parsed._replace(query=urlencode(cleaned_qs, doseq=True)))
    except Exception:
        cleaned_url = url  # If parsing fails, use original

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(cleaned_url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        # Primary title: <title> tag
        title = soup.title.string.strip() if soup.title else ""

        # Primary body: <p> tags
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text() for p in paragraphs]).strip()

        # Fallback for JS-rendered sites: use CF API and then OG meta tags
        if len(text) < 100:
            cf_text = _scrape_with_cloudflare(cleaned_url)
            if len(cf_text) > 200:
                text = cf_text
            else:
                og_title = soup.find("meta", property="og:title")
                og_desc = soup.find("meta", property="og:description")
                if og_title and not title:
                    title = og_title.get("content", "").strip()
                if og_desc:
                    og_text = og_desc.get("content", "").strip()
                    if og_text:
                        text = og_text  # At minimum we have a summary for Grok to work with

        return {"title": title, "text": text[:5000], "cleaned_url": cleaned_url}
    except Exception as e:
        return {"error": str(e), "text": "", "title": "", "cleaned_url": cleaned_url}
