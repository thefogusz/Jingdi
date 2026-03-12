import requests
from bs4 import BeautifulSoup
import time
import os
import json
import concurrent.futures
from services.gemini_pool import get_next_client

def _scrape_with_cloudflare(url: str) -> str:
    """Use Cloudflare Browser Rendering to scrape JS-heavy sites."""
    # API configuration from env
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    
    if not account_id or not api_token:
        print("[Cloudflare Scraper] Missing credentials. Skipping.")
        return ""

    cf_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/screenshot"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    # We use 'html' instead of 'screenshot' if supported, or just use rendering to get text
    # Note: Cloudflare doesn't have a direct 'text' endpoint, but we can use the rendering service
    # via workers or specific APIs if available. For this project we assume a helper worker or 
    # similar logic.
    
    try:
        # Placeholder for real CF rendering call logic
        # For now, we simulate success or fallback if actual API differs
        res = requests.post(
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/google/gemma-7b-it-lora",
            headers=headers,
            json={"prompt": f"Extract text from this URL: {url}"},
            timeout=15
        )
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
    """Scrape basic text content from a URL with social media workarounds."""
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

    # --- Strip known tracking/redirect params ---
    TRACKING_PARAMS = {"fbclid", "utm_source", "utm_medium", "utm_campaign",
                       "utm_term", "utm_content", "ref", "_fb_noscript"}
    cleaned_url = url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # --- Social Media Workarounds ---
        if "twitter.com" in domain or "x.com" in domain:
            new_domain = domain.replace("twitter.com", "vxtwitter.com").replace("x.com", "vxtwitter.com")
            cleaned_url = urlunparse(parsed._replace(netloc=new_domain))
            print(f"[Scraper] X/Twitter detected. Using workaround: {cleaned_url}")
        elif "facebook.com" in domain and "m.facebook.com" not in domain:
            # Use mobile subdomain for FB - often bypasses heavy JS/modals and has better SEO meta tags
            new_domain = "m.facebook.com"
            cleaned_url = urlunparse(parsed._replace(netloc=new_domain))
            print(f"[Scraper] Facebook detected. Using mobile workaround: {cleaned_url}")
        else:
            qs = parse_qs(parsed.query, keep_blank_values=True)
            cleaned_qs = {k: v for k, v in qs.items()
                          if k not in TRACKING_PARAMS and not k.startswith("aem_")}
            cleaned_url = urlunparse(parsed._replace(query=urlencode(cleaned_qs, doseq=True)))
    except Exception:
        cleaned_url = url

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
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
                # Meta Extraction Cascade
                og_title = soup.find("meta", property="og:title") or soup.find("meta", name="twitter:title")
                og_desc = soup.find("meta", property="og:description") or soup.find("meta", name="twitter:description")
                
                if og_title and not title:
                    title = og_title.get("content", "").strip()
                if og_desc:
                    og_text = og_desc.get("content", "").strip()
                    if og_text:
                        text = og_text
                        
                # Special Case: If it's a social link and we STILL have nothing, use the title as text
                if (not text or len(text) < 20) and title:
                    text = f"Content restricted or hidden. Title hint: {title}"

        return {"title": title, "text": text[:5000], "cleaned_url": cleaned_url}
    except Exception as e:
        print(f"[Scraper] Error scraping {cleaned_url}: {e}")
        return {"error": str(e), "text": "", "title": "", "cleaned_url": cleaned_url}

def search_web(query: str, case_id: str = None) -> list:
    """Core search function using Tavily AI (Search Grounding)."""
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        print("[Search] TAVILY_API_KEY not found.")
        return []

    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": tavily_api_key,
            "query": query,
            "search_depth": "advanced",
            "include_domains": [],
            "exclude_domains": []
        }
        res = requests.post(url, json=payload, timeout=15)
        res.raise_for_status()
        data = res.json()
        
        import database
        database.log_request("[API] Tavily Search", query[:100], 0, "info", cost=0.003, case_id=case_id, api_name="Tavily")
        
        results = []
        for r in data.get("results", []):
            results.append({
                "title": r.get("title", "No Title"),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")
            })
        return results
    except Exception as e:
        print(f"[Search] Tavily error: {e}")
        return []

def extract_keywords(text: str) -> str:
    """Extract key search terms from text using Gemini."""
    client = get_next_client()
    if not client:
        return text[:100]
    
    try:
        prompt = f"Extract 5-7 core search keywords in Thai and English from this text for fact-checking. Return only the keywords separated by spaces: {text[:500]}"
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"[Search] Keyword extraction error: {e}")
        return text[:100]
