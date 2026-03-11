import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
from google import genai
from google.genai import types
from openai import OpenAI

from .gemini_pool import get_next_client
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def verify_url(url: str) -> bool:
    """Check if a URL is alive, being lenient to anti-bot protections."""
    if not url or not url.startswith("http"):
        return False
        
    lower_url = url.lower()
    # Explicitly block x.com / twitter.com since they don't resolve properly without auth
    if "x.com/" in lower_url or "twitter.com/" in lower_url:
        return False
        
    # Block explicitly hallucinated placeholder domains
    if "example.com" in lower_url or "your-search-keywords" in lower_url:
        return False
        
    # Be more lenient with social media/sharing links as they often fail HEAD requests but are valid
    if any(dm in lower_url for dm in ["facebook.com", "fb.watch", "instagram.com", "t.co", "bit.ly"]):
        return True
        
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Use GET with stream=True since some servers block HEAD requests
        res = requests.get(url, headers=headers, timeout=6.0, verify=False, allow_redirects=True, stream=True)
        res.close()
        
        # 403 Forbidden/406 Not Acceptable is common for scraper protection.
        # 400 Bad Request, 404 Not Found, 410 Gone, and 500+ Server Errors mean the link is dead/invalid.
        if res.status_code in [400, 404, 410] or res.status_code >= 500:
            return False
            
        return True
    except requests.exceptions.Timeout:
        # If it times out, it's either dead or too slow to be useful. Strict drop.
        return False
    except requests.exceptions.ConnectionError:
        # DNS failure or server completely refusing connection
        return False
    except Exception:
        # Strict drop on any other generic exception
        return False

# Initialize Grok
xai_api_key = os.getenv("XAI_API_KEY")
grok_client = OpenAI(
    api_key=xai_api_key,
    base_url="https://api.x.ai/v1",
) if xai_api_key else None

def analyze_text_claim(text: str, search_context: str = "") -> dict:
    """Analyze a text claim using Gemini, optionally with DuckDuckGo search context."""
    gemini_client = get_next_client()
    if not gemini_client:
        return {
            "score": 50,
            "analysis": "Gemini API Keys not configured. Please set GEMINI_API_KEYS in backend/.env.",
            "claims_extracted": [],
            "suspicious_words": [],
            "sources": []
        }

    current_date = datetime.now().strftime("%Y-%m-%d")
    current_year_th = datetime.now().year + 543
    
    prompt = f"""
    Current Date: {current_date} (พ.ศ. {current_year_th})
    
    We are trying to verify the following text or claim:
    "{text}"
    
    Below is some initial context (if any) we found regarding this claim:
    ---
    {search_context if search_context else "No initial search context provided."}
    ---
    
    CRITICAL INSTRUCTION: You MUST use your Google Search tool to find the ORIGIN of this claim. Do not hallucinate. 
    If you find the exact source or a credible debunking, provide a definitive score (0-10, or 90-100). 
    If the search results are irrelevant or inconclusive, give a score between 40-60.
    
    TONE & STYLE INSTRUCTION: Write the `analysis` section in simple, everyday Thai language (ภาษาชาวบ้าน เข้าใจง่าย กระชับ).
    
    CRITICAL FORMATTING INSTRUCTION: 
    1. CONCISENESS: Keep the analysis extremely short and to the point. Max 3-4 bullet points.
    2. NO URLS IN TEXT: DO NOT include raw URLs in the `analysis` text.
    3. Use **bold text** to highlight important names, dates, or keywords.
    4. CITE YOUR SEARCH: Explicitly state what you searched for and what you found (or didn't find).
    
    Provide a JSON response with the following keys:
    - score: An integer from 0 to 100.
    - analysis: A clear, concise explanation in Thai. 
    - claims_extracted: A list of the main factual claims made in the text (in Thai).
    - suspicious_words: A list of emotionally manipulative or sensationalist words used in the text (in Thai).
    - sources: An array of source objects [{{'title': '...', 'snippet': '...', 'link': '...'}}] from your Google Search.
    
    Return ONLY valid JSON.
    """

    for attempt in range(4):
        gemini_client = get_next_client()
        if not gemini_client:
            return {
                "score": 50,
                "analysis": "Gemini API Keys not configured. Please set GEMINI_API_KEYS in backend/.env.",
                "claims_extracted": [],
                "suspicious_words": [],
                "sources": []
            }
            
        try:
            try:
                response = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                        tools=[{"google_search": {}}]
                    ),
                )
            except Exception as inner_e:
                if "429" in str(inner_e) or "RESOURCE_EXHAUSTED" in str(inner_e):
                    # Fallback to lite version if 2.5-flash limit is hit
                    response = gemini_client.models.generate_content(
                        model='gemini-2.5-flash-lite',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1,
                            tools=[{"google_search": {}}]
                        ),
                    )
                else:
                    raise inner_e
                    
            parsed = json.loads(response.text)
            
            # Rigorous Source Sanitization and Active Verification
            valid_sources = []
            for s in parsed.get("sources", []):
                if not isinstance(s, dict): continue
                link = s.get("link", "")
                
                if isinstance(link, str) and verify_url(link):
                    valid_sources.append(s)
                elif "title" in s and "snippet" in s:
                    s["link"] = "" # Erase invalid/dead links so UI doesn't show broken button
                    valid_sources.append(s)
            parsed["sources"] = valid_sources
            
            try:
                import database
                database.log_request("[API] Gemini Text", text[:50], 0, "success", cost=0.0002, api_name="Gemini")
            except Exception:
                pass
                
            return parsed
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < 3:
                    continue # Try next API key
                clean_error = "ระบบขัดข้องชั่วคราว: ขณะนี้โควต้า AI ตรวจสอบข้อความเต็มทุกระบบ (Rate Limit) รบกวนรอประมาณ 1 นาทีแล้วลองใหม่อีกครั้งนะครับ 🙏"
            else:
                clean_error = f"Error during Gemini analysis: {error_msg}"
                
            if attempt == 3 or ("429" not in error_msg and "RESOURCE_EXHAUSTED" not in error_msg):
                return {
                    "score": 50,
                    "analysis": clean_error,
                    "claims_extracted": [],
                    "suspicious_words": [],
                    "sources": [],
                    "skip_to_grok": True
                }
    
    return {
        "score": 50,
        "analysis": "Unknown error during text analysis.",
        "claims_extracted": [],
        "suspicious_words": [],
        "sources": [],
        "skip_to_grok": True
    }


def analyze_with_grok(text: str, search_context: str = "") -> dict:
    """Analyze a text prompt using Grok 4.1 Fast Reasoning with optional external context."""
    if not grok_client:
        return {
            "score": 50,
            "analysis": "XAI_API_KEY not configured. Please set XAI_API_KEY in backend/.env.",
            "claims_extracted": [],
            "suspicious_words": [],
            "sources": []
        }

    current_date = datetime.now().strftime("%Y-%m-%d")
    current_year_th = datetime.now().year + 543
    
    prompt = f"""
    Current Date: {current_date} (พ.ศ. {current_year_th})
    Analyze the following text or claim using a **Digital Forensics** approach:
    "{text}"
    
    Below is the web search and image provenance context found:
    ---
    {search_context if search_context else "No search context provided."}
    ---
    
    ROLE: You are a Digital Forensic Investigator. Your goal is to identify the **ORIGIN (Provenance)** and **CREDIBILITY** of this story.
    
    FORENSIC STEPS:
    1. **IDENTIFY FIRST SOURCE**: Try to determine who posted this first. Look for timestamps or 'oldest' search results. Is it a credible news outlet or an anonymous social media user?
    2. **EVALUATE AUTHORITY**: If the source is an individual, are they a known influencer/authority or a random account? Check the 'weight' of the source.
    3. **CHECK CONSENSUS**: Is this story being reported across multiple independent, high-trust outlets? If only social media is talking about it, check the 'Consensus'—are people in comments calling it out or sharing it as fact? 
    4. **CROSS-VERIFY IMAGE**: If image context (SerpApi/Lens) is provided, verify if the image is being used out of context (e.g. old photo used for new news).
    
    CRITICAL INSTRUCTION: Analyze the claim using ONLY the provided context and confirmed historical facts. 
    1. **TOPIC RELEVANCE CHECK**: Before analyzing, ask: "Do these search results talk about the SAME ACTION or EVENT as the claim?" (e.g. if the claim is about "withdrawing money", do NOT use search results about "interest rates" to debunk it).
    2. **STRICT ANCHORING**: If search results are about a different topic, DISCARD THEM. State clearly: "**ไม่พบข้อมูลที่เกี่ยวข้องโดยตรงกับเรื่อง [Topic] ในผลการค้นหา**" and analyze based on that absence.
    3. **NO HALLUCINATION**: NEVER invent events, dates, or citations. If you find no evidence, state it clearly.
    4. **OBJECTIVITY**: Do not bias towards finding "Fake News". 
    
    TONE & STYLE INSTRUCTION: Write the `analysis` section in professional but simple Thai. Focus on the word "**ต้นตอ**" (Origin) and "**ความน่าเชื่อถือ**" (Credibility).
    
    CRITICAL FORMATTING INSTRUCTION: 
    - CONCISENESS: Max 3-4 short bullet points.
    - NO URLS IN TEXT: Use the `sources` array for links.
    - Use **bold text** for names/dates.
    - EXPLICIT CONCLUSION: Clearly state the level of trust and why.
    
    Provide a JSON response with the following keys:
    - score: An integer from 0 to 100 where 0 is definitively disproven misinformation and 100 is highly credible with evidence. Use scores like 40-60 if no evidence is found either way.
    - analysis: A clear, easy-to-read explanation in conversational Thai. YOU MUST explicitly cite the sources you used. If no sources found, explicitly state it as instructed above.
    - claims_extracted: A list of the main factual claims made in the text (in Thai).
    - suspicious_words: A list of emotionally manipulative or sensationalist words used in the text (in Thai).
    - sources: An array of objects for the actual live websites you checked. Format: [{{"title": "Headline", "snippet": "Short relevant quote", "link": "EXACT_WORKING_URL"}}]. 
      CRITICAL: You MUST include official social media posts (Facebook, Instagram, X) if they are from verified news outlets like Bright TV, Thai Rath, etc. These are VALUABLE primary sources.
      CRITICAL: If a source link is a Facebook 'share' link or 'fb.watch' link, TRUST it if the title or snippet clearly indicates it belongs to a reputable news agency.
      CRITICAL: If you do not have the exact, working URL from a real news source, you MUST provide a Google search link to find it, formatted exactly like: "https://www.google.com/search?q=Keywords". NEVER hallucinate broken URLs or fake domains.
    
    Return ONLY valid JSON. format: {{ "score": 0, "analysis": "...", "claims_extracted": [], "suspicious_words": [], "sources": [] }}
    """

    try:
        response = grok_client.chat.completions.create(
            model="grok-4-1-fast-reasoning",
            messages=[
                {"role": "system", "content": "You are a highly accurate fake news detection AI with access to the live internet. You MUST search the web to verify claims. You respond with valid JSON only in the format: {\"score\": 50, \"analysis\": \"...\", \"claims_extracted\": [], \"suspicious_words\": [], \"sources\": [{\"title\":\"\",\"snippet\":\"\",\"link\":\"\"}]}"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        parsed = json.loads(result_text)
        
        # Rigorous Source Sanitization and Active Verification
        valid_sources = []
        for s in parsed.get("sources", []):
            if not isinstance(s, dict): continue
            link = s.get("link", "")
            
            if isinstance(link, str) and verify_url(link):
                valid_sources.append(s)
            elif "title" in s and "snippet" in s:
                s["link"] = "" # Erase invalid/dead links
                valid_sources.append(s)
                
        parsed["sources"] = valid_sources
        
        try:
            import database
            database.log_request("[API] Grok 4.1 Reasoning", text[:50], 0, "success", cost=0.0005, api_name="Grok")
        except Exception:
            pass
            
        return parsed
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            raw = response.choices[0].message.content if 'response' in locals() else "Unknown"
        except:
            raw = "Failed to extract raw text"
            
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "rate limit" in error_msg.lower():
            clean_error = "ระบบขัดข้องชั่วคราว: ขณะนี้มีผู้ใช้งานเกินโควต้าของระบบสมองหลัก (Grok Rate Limit) รบกวนรอซักครู่แล้วลองใหม่อีกครั้งนะครับ 🙏"
        else:
            clean_error = f"API Error: {error_msg}. Raw reply: {raw}"
            
        return {
            "score": 50,
            "analysis": clean_error,
            "claims_extracted": [],
            "suspicious_words": [],
            "sources": []
        }


def analyze_image_fact_check(image_bytes_list: list, hint_context: str = "", log_filename: str = "") -> dict:
    '''Send images directly to Grok Vision + web search for one-shot fact-checking.
    Grok sees the actual image, reads Thai text itself, generates its own keywords,
    and searches the web. Bypasses the unreliable OCR pipeline.'''
    if not grok_client:
        return {"score": 50, "analysis": "XAI_API_KEY not configured.",
                "claims_extracted": [], "suspicious_words": [], "sources": []}
    import io, base64
    from PIL import Image as PILImage
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_year_th = datetime.now().year + 543
    content = []
    for img_bytes in image_bytes_list[:3]:
        try:
            img = PILImage.open(io.BytesIO(img_bytes))
            out = io.BytesIO()
            img.convert("RGB").save(out, format="JPEG", quality=85)
            b64 = base64.b64encode(out.getvalue()).decode()
            content.append({"type": "image_url",
                             "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        except Exception as e:
            print(f"[Image Fact Check] encode error: {e}")
    hint = f"Additional context: {hint_context}\n\n" if hint_context else ""
    prompt_text = (
        f"Current Date: {current_date} (พ.ศ. {current_year_th})\n\n"
        "You are a fact-checker with VISION and LIVE WEB SEARCH. The image above needs verification.\n\n"
        + hint
        + "=== PROVENANCE-FIRST FACT-CHECKING ===\n\n"
        "STEP 1 — READ THE IMAGE YOURSELF:\n"
        "Look carefully at ALL visible text (Thai and English).\n"
        "Thai news graphics often use a clickbait background photo. The real story is in the TEXT OVERLAY.\n"
        "Read the main HEADLINE text — that is what the story is actually about.\n\n"
        "STEP 2 — TRANSLATE THAI TEXT & SEARCH:\n"
        "Translate the Thai headline to English accurately. Be literal but correct.\n"
        "Use your English translation as the search query to find the original news source.\n\n"
        "STEP 3 — FIND & VERIFY ORIGINAL SOURCE:\n"
        "Which outlet FIRST published this? Is it credible? Multiple sources confirm same facts?\n"
        "If it's architectural (e.g. King Power Mahanakhon), recognize it's a design, not a disaster.\n\n"
        "STEP 4 — CHECK CLAIM ACCURACY & SOCIAL CONTEXT:\n"
        "Does the Thai caption accurately represent the original story?\n"
        "Was the image used out of context? If only social media is posting, analyze the sentiment.\n\n"
        "TONE: Simple conversational Thai.\n"
        "FORMAT: Max 3-4 bullet points. NO raw URLs in analysis. **Bold** key names.\n"
        "YOU MUST include your intermediate steps in the JSON so I can verify your work:\n"
        "- extracted_text: The exact Thai headline you read\n"
        "- translated_text: Your English translation of it\n"
        "- search_query_used: The exact search query you ran\n"
        'SOURCES: [{"title":"...","snippet":"...","link":"EXACT_URL"}] — original source first.'
    )
    content.append({"type": "text", "text": prompt_text})
    try:
        response = grok_client.chat.completions.create(
            model="grok-vision-beta",
            messages=[
                {"role": "system", "content": (
                    "You are a highly accurate fact-checker with vision and live web search. "
                    "IMPORTANT: Thai news graphics use clickbait BACKGROUND PHOTOS unrelated to the actual story. "
                    "The REAL STORY is always in the HEADLINE TEXT OVERLAY. "
                    "ALWAYS read all text in the image. Fact-check the HEADLINE, not the background photo. "
                    "KEY TERM: หมึกมหึมา = colossal squid (Mesonychoteuthis hamiltoni), "
                    "DIFFERENT from ปลาหมึกยักษ์ (giant squid = Architeuthis dux). "
                    "If text says 'ครั้งแรก' (first time) or 'ถิ่นที่อยู่ธรรมชาติ' (natural habitat), "
                    "this is a SCIENTIFIC DISCOVERY — search English scientific sources. "
                    "Respond with valid JSON only: "
                    '{"score":50,"extracted_text":"...","translated_text":"...","search_query_used":"...","analysis":"...","claims_extracted":[],'
                    '"suspicious_words":[],"sources":[{"title":"","snippet":"","link":""}]}'
                )},
                {"role": "user", "content": content}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        # Manually extract JSON from markdown if xAI responds with ```json ... ```
        response_text = response.choices[0].message.content.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        parsed = json.loads(response_text.strip())
        # avoid printing complex Thai chars to Windows console to prevent encoding errors
        # print(f"\n--- GROK FACT-CHECK DEBUG ---\nEXTRACTED: {parsed.get('extracted_text')}\n...")
        valid = []
        for s in parsed.get("sources", []):
            if not isinstance(s, dict): continue
            link = s.get("link", "")
            if isinstance(link, str) and verify_url(link): valid.append(s)
            elif "title" in s and "snippet" in s: s["link"] = ""; valid.append(s)
        parsed["sources"] = valid
        
        try:
            import database
            log_entry = f"Image processing ({log_filename})" if log_filename else "Image processing"
            database.log_request("[API] Grok Vision", log_entry, 0, "success", cost=0.0100, api_name="Grok")
        except Exception:
            pass
            
        return parsed
    except Exception as e:
        try:
            with open("xai_error.log", "a") as err_f:
                err_f.write(f"Grok Error: {str(e)}\\n")
        except: pass
        msg = ("ระบบขัดข้องชั่วคราว: Rate limit กรุณารอซักครู่ 🙏"
               if ("429" in str(e) or "rate limit" in str(e).lower()) else f"Error: {e}")
        return {"score": 50, "analysis": msg,
                "claims_extracted": [], "suspicious_words": [], "sources": []}
