import os
import asyncio
import aiohttp
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Fake News Detection API")

# Configure CORS for Next.js frontend
_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://jingdi.online",
    "https://www.jingdi.online",
]
# Allow extra origin from env (e.g. Vercel preview URLs)
_extra_origin = os.getenv("FRONTEND_URL")
if _extra_origin:
    _cors_origins.append(_extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextCheckRequest(BaseModel):
    text: str
    cf_token: str = ""

class UrlCheckRequest(BaseModel):
    url: str
    cf_token: str = ""

class ToggleKillSwitchRequest(BaseModel):
    password: str
    active: bool

class FeedbackRequest(BaseModel):
    log_id: int
    is_helpful: bool
    reason: str = ""
    details: str = ""

import os
import io
import time
import uuid
import database
from fastapi.responses import FileResponse, RedirectResponse, Response
from services.llm_service import analyze_text_claim, analyze_with_grok, analyze_image_fact_check, get_next_client
from services.search_service import search_web, scrape_url
from services.vision_service import analyze_images_with_vision
from services.reverse_image_service import reverse_image_search, serpapi_google_lens
from services.rss_service import search_rss_precheck
from services.r2_service import upload_image, get_image_url
from typing import List

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Fake News Detection API is running"}

def check_kill_switch():
    if database.get_kill_switch():
        raise HTTPException(
            status_code=503, 
            detail="⚠️ ขออภัย ขณะนี้ระบบอยู่ระหว่างการปิดปรับปรุงหรือชะลอการใช้ชั่วคราว (API Kill Switch is ON)"
        )

TURNSTILE_SECRET = os.getenv("CLOUDFLARE_TURNSTILE_SECRET", "")

def verify_turnstile(token: str):
    """Verify Cloudflare Turnstile token to block bots. Skips if secret not configured."""
    if not TURNSTILE_SECRET:
        return  # graceful skip if not configured yet
    if not token:
        raise HTTPException(status_code=400, detail="Bot detected: missing Turnstile token")
    try:
        import requests as http_requests
        res = http_requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": TURNSTILE_SECRET, "response": token},
            timeout=5
        )
        result = res.json()
        if not result.get("success"):
            raise HTTPException(status_code=403, detail="Bot detected: Turnstile verification failed")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Turnstile] Verification error (allowing through): {e}")

@app.post("/api/check-text")
async def check_text(request: TextCheckRequest):
    check_kill_switch()
    # verify_turnstile(request.cf_token) # Temporarily disabled to fix 400 error
    start_time = time.time()
    case_id = str(uuid.uuid4())
    try:
        # Tier 0 & 1: Concurrent RSS Pre-Check & Web Search
        from services.search_service import extract_keywords
        keywords = extract_keywords(request.text)
        
        loop = asyncio.get_running_loop()
        rss_task = loop.run_in_executor(None, search_rss_precheck, request.text, keywords)
        web_task = loop.run_in_executor(None, search_web, request.text)
        
        rss_matches, search_context = await asyncio.gather(rss_task, web_task)
        
        if rss_matches:
             search_context.insert(0, {"title": "🚨 VERIFIED FACT-CHECK (RSS)", "snippet": str(rss_matches), "url": "RSS_FEED"})
        
        # Smart Tier Routing: Detect complex inputs upfront — skip Gemini for complex cases
        text = request.text
        is_complex = (
            len(text) > 600 or                            # Long text → Grok
            text.count('\n') > 4 or                       # Multi-paragraph
            text.count('http') > 0 or                     # Contains URL
            any(w in text.lower() for w in ['สลิป', 'โอน', 'บัญชี', 'ดาวน์โหลด', 'ลงทะเบียน'])  # Finance/scam keywords → Grok
        )
        
        if is_complex:
            # Tier 2 Direct: Skip Gemini, go straight to Grok
            database.log_request("[API] Grok 4.1 Reasoning", text[:100], 0, "info", cost=0.0005, case_id=case_id, api_name="Grok")
            analysis_result = analyze_with_grok(text, search_context=search_context)
        else:
            # Tier 1: Gemini (fast, cheap for simple claims)
            database.log_request("[API] Gemini Text", text[:100], 0, "info", cost=0.0002, case_id=case_id, api_name="Gemini")
            analysis_result = analyze_text_claim(text, search_context=search_context)
            score = analysis_result.get("score", 50)
            
            # Escalate to Grok only if Gemini is genuinely inconclusive
            if (40 < score < 60) or not analysis_result.get("sources") or analysis_result.get("skip_to_grok"):
                database.log_request("[API] Grok 4.1 Reasoning", text[:100], 0, "info", cost=0.0005, case_id=case_id, api_name="Grok")
                analysis_result = analyze_with_grok(text, search_context=search_context)

            
        latency = int((time.time() - start_time) * 1000)
        log_id = database.log_request("/api/check-text", request.text[:100], latency, "success", cost=0.0001, case_id=case_id)
        
        return {
            "log_id": log_id,
            "score": analysis_result.get("score", 50),
            "analysis": analysis_result.get("analysis", "Unable to analyze text."),
            "claims_extracted": analysis_result.get("claims_extracted", []),
            "suspicious_words": analysis_result.get("suspicious_words", []),
            "ai_signals": analysis_result.get("ai_signals", []),
            "ai_confidence_score": analysis_result.get("ai_confidence_score", 0),
            "sources": analysis_result.get("sources", []),
            "original_source": analysis_result.get("original_source", "Unknown/Social Media"),
            "api_used": analysis_result.get("api_used", "Grok" if is_complex else "Gemini"),
            "visual_indicators": []
        }
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        database.log_request("/api/check-text", request.text[:100], latency, "error", str(e), case_id=case_id)
        return {
            "log_id": -1,
            "score": 50,
            "analysis": "ระบบขัดข้องชั่วคราว: ไม่สามารถตรวจสอบข้อความได้ในขณะนี้",
            "claims_extracted": [],
            "suspicious_words": [],
            "sources": [],
            "visual_indicators": []
        }

def _detect_platform(url: str) -> str:
    """Return a human-readable platform name for a social media URL."""
    url_lower = url.lower()
    if "facebook.com" in url_lower or "fb.com" in url_lower or "fb.watch" in url_lower:
        return "Facebook"
    if "instagram.com" in url_lower:
        return "Instagram"
    if "twitter.com" in url_lower or "x.com" in url_lower:
        return "X (Twitter)"
    if "tiktok.com" in url_lower:
        return "TikTok"
    return "Social Media"


@app.post("/api/check-url")
def check_url(request: UrlCheckRequest):
    check_kill_switch()
    start_time = time.time()
    case_id = str(uuid.uuid4())
    try:
        # Scrape the URL (will return is_social_url=True for FB/IG/Twitter/TikTok)
        scraped = scrape_url(request.url)
        cleaned_url = scraped.get('cleaned_url', request.url)
        is_social = scraped.get('is_social_url', False)

        # ── SOCIAL MEDIA FAST PATH ────────────────────────────────────────────
        if is_social:
            print(f"[check-url] Social media URL detected: using Crawl API (Tavily Extract) — {cleaned_url}")
            from services.search_service import crawl_url
            
            # Step 1: Attempt to crawl the content using Tavily Extract
            crawl_res = crawl_url(cleaned_url)
            crawled_text = crawl_res.get("text", "")
            
            # Step 2: Fallback to search if crawl failed or is empty
            search_context = ""
            if not crawled_text:
                print(f"[check-url] Crawl failed, falling back to search context for: {cleaned_url}")
                search_context = search_web(cleaned_url)
            
            social_prompt = f"""The user wants to fact-check this social media post URL:
{cleaned_url}

IMPORTANT: This is a {_detect_platform(cleaned_url)} link. 
We attempted to extract its content directly and obtained:
---
{crawled_text if crawled_text else "Direct extraction failed. Please use your native web browsing or the search results below."}
---

INSTRUCTIONS:
1. Identify the core claim or topic.
2. Search for credible news sources (Thai or English) that confirm or deny the claim.
3. If crawled text above is empty, YOU MUST use your native web browsing / search to see the post content.

CRITICAL FORMATTING INSTRUCTION:
1. CONCISENESS: Write 3-4 short bullet points max. Be direct and specific.
2. NO URLS IN TEXT: No raw links inside `analysis`. Use only the `sources` array.
3. Use **bold** for names, dates, keywords.
4. SOURCES: Populate `sources` array with real links. If unsure, use Google search link: https://www.google.com/search?q=...
"""
            database.log_request("[API] Grok 4.1 Reasoning", f"[Social URL] {cleaned_url[:80]}", 0, "info", cost=0.0005, case_id=case_id, api_name="Grok")
            analysis_result = analyze_with_grok(social_prompt, search_context=search_context)
            latency = int((time.time() - start_time) * 1000)
            log_id = database.log_request("/api/check-url", request.url[:100], latency, "success", cost=0.0005, case_id=case_id)
            return {
                "log_id": log_id,
                "score": analysis_result.get("score", 50),
                "analysis": analysis_result.get("analysis", "ไม่สามารถดึงข้อมูลโพสต์ได้"),
                "claims_extracted": analysis_result.get("claims_extracted", []),
                "suspicious_words": analysis_result.get("suspicious_words", []),
                "sources": analysis_result.get("sources", []),
                "visual_indicators": []
            }
        # ── NORMAL URL PATH ──────────────────────────────────────────────────

        # Tier 1: Free Search + Gemini
        search_query = scraped.get('title', '') or cleaned_url
        if not search_query or search_query == 'N/A': search_query = cleaned_url
        search_context = search_web(search_query)
        
        # Tier 0: RSS Pre-Check
        rss_matches = search_rss_precheck(search_query, search_query)
        
        combined_context = f"Scraped Content: {scraped.get('text', 'N/A')}\n\nWeb Search Results: {search_context}"
        if rss_matches:
             combined_context = f"🚨 VERIFIED FACT-CHECK (RSS): {str(rss_matches)}\n\n" + combined_context
             
        database.log_request("[API] Gemini Text", request.url[:100], 0, "info", cost=0.0002, case_id=case_id, api_name="Gemini")
        analysis_result = analyze_text_claim(f"Verify this article: {cleaned_url} - {scraped.get('title', 'N/A')}", search_context=combined_context)
        score = analysis_result.get("score", 50)
        
        # Tier 2: Escalate to Grok Native Search
        if (40 < score < 60) or not analysis_result.get("sources"):
            title_hint = scraped.get('title', 'N/A')
            text_hint = scraped.get('text', '')
            prompt_for_grok = f"""
            The user provided a URL to fact-check: {cleaned_url}
            
            We scraped the page and obtained:
            Title: {title_hint}
            Content: {text_hint[:1000] if text_hint else 'N/A'}
            
            STEP 1 — UNDERSTAND THE STORY:
            Read the title and content above carefully. Determine:
            - What is the core claim or event being reported?
            - Is this a LOCAL (Thai) story or an INTERNATIONAL story from a foreign publication?
            
            STEP 2 — SEARCH CORRECTLY:
            - If the article is from an international English-language site (UNILAD, BBC, Reuters, CNN, etc.), you MUST search using ENGLISH keywords. Do NOT search Thai news databases for international science/world stories.
            - If the article is about a Thai-specific event, search Thai sources.
            - If the scraped content is empty/minimal, visit the cleaned URL ({cleaned_url}) directly using your native web browsing or search for the headline to determine the story.
            
            STEP 3 — VERIFY:
            Cross-reference the claim against multiple reliable sources found in your search.
            
            CRITICAL FORMATTING INSTRUCTION: You MUST format the analysis text logically using Markdown. 
            1. CONCISENESS: Keep the analysis extremely short and to the point. Use a maximum of 3-4 short bullet points. Give the user exactly what they need to know without fluff.
            2. NO URLS IN TEXT: DO NOT include raw URLs (http...) or markdown links (e.g., [Text](URL)) inside the `analysis` text. It looks messy. Rely entirely on the `sources` JSON array to provide links.
            3. Use **bold text** to highlight important names, dates, or keywords.
            4. EVIDENCE OF SEARCH & MISSING DATA: You MUST explicitly state the breadth of your search. If you CANNOT find real evidence, state clearly: "**จากการตรวจสอบแหล่งข้อมูลข่าวที่น่าเชื่อถือหลัก** ไม่พบรายงานที่ยืนยันเรื่องนี้ได้"
            5. SOURCES: You MUST populate the `sources` JSON array. Format: [{{"title": "Headline", "snippet": "Quote", "link": "EXACT_WORKING_URL"}}]. CRITICAL: If you do not have the exact, working URL from a real news source, you MUST provide a Google search link to find it, formatted exactly like: "https://www.google.com/search?q=Keywords". NEVER hallucinate broken URLs or fake domains.
            """
            database.log_request("[API] Grok 4.1 Reasoning", request.url[:100], 0, "info", cost=0.0005, case_id=case_id, api_name="Grok")
            analysis_result = analyze_with_grok(prompt_for_grok, search_context=search_context)
        
        latency = int((time.time() - start_time) * 1000)
        log_id = database.log_request("/api/check-url", request.url[:100], latency, "success", cost=0.0001, case_id=case_id)

        return {
            "log_id": log_id,
            "score": analysis_result.get("score", 50),
            "analysis": analysis_result.get("analysis", "Unable to analyze URL content."),
            "claims_extracted": analysis_result.get("claims_extracted", []),
            "suspicious_words": analysis_result.get("suspicious_words", []),
            "sources": analysis_result.get("sources", []),
            "visual_indicators": []
        }
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        database.log_request("/api/check-url", request.url[:100], latency, "error", str(e), case_id=case_id)
        return {
            "log_id": -1,
            "score": 50,
            "analysis": "ระบบขัดข้องชั่วคราว: ไม่สามารถตรวจสอบ URL ได้ในขณะนี้",
            "claims_extracted": [],
            "suspicious_words": [],
            "sources": [],
            "visual_indicators": []
        }



@app.post("/api/check-image")
async def check_image(files: List[UploadFile] = File(...)):
    case_id = str(uuid.uuid4())
    try:
        check_kill_switch()
        start_time = time.time()
        
        # Guard: Max 3 files, 10MB each
        MAX_FILES = 3
        MAX_SIZE_MB = 10
        MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024
        if len(files) > MAX_FILES:
            raise HTTPException(status_code=400, detail=f"อัปโหลดได้สูงสุด {MAX_FILES} รูปต่อครั้ง")
        contents = [await file.read() for file in files]
        for i, (file, content) in enumerate(zip(files, contents)):
            if len(content) > MAX_SIZE_BYTES:
                size_mb = len(content) / (1024 * 1024)
                raise HTTPException(status_code=413, detail=f"ไฟล์ '{file.filename}' มีขนาด {size_mb:.1f}MB เกินขนาดสูงสุดที่อนุญาต ({MAX_SIZE_MB}MB)")
            allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
            if file.content_type and file.content_type not in allowed_types:
                raise HTTPException(status_code=415, detail=f"ไฟล์ '{file.filename}' ไม่ใช่รูปภาพที่รองรับ (รองรับ JPG, PNG, WEBP, GIF เท่านั้น)")

        # Upload first image to Cloudflare R2
        ext = "jpg"
        if files[0].filename and "." in files[0].filename:
            ext = files[0].filename.split(".")[-1].lower()
        
        img_filename = f"{uuid.uuid4().hex[:12]}.{ext}"
        public_img_url = None
        try:
            content_type = files[0].content_type or "image/jpeg"
            public_img_url = upload_image(img_filename, contents[0], content_type=content_type)
        except Exception as up_err:
            print(f"[R2] Upload error: {up_err}")
            public_img_url = None

        if public_img_url:
            query_display = f"[Image Upload] ({img_filename})"
        else:
            query_display = f"[Image Upload FAILED] {files[0].filename}"
            public_img_url = None
        vision_result    = analyze_images_with_vision(contents, is_screenshot=False)
        extracted_text   = vision_result.get("extracted_text", "")
        visual_indicators= vision_result.get("visual_indicators", [])
        eng_keywords     = vision_result.get("english_keywords", [])
        is_global        = vision_result.get("is_global_story", False)
        text_clarity     = vision_result.get("text_clarity", "high")

        # --- Step 1b: Forensic Cross-Check (If text is low clarity or missing) ---
        # If Gemini struggled, we ask Grok Vision for a second opinion
        if text_clarity == 'low' or not extracted_text:
            print(f"[main] Low text clarity detected ({text_clarity}). Triggering Grok Vision cross-check...")
            try:
                grok_vision = analyze_image_fact_check(contents, hint_context=f"Gemini extracted: {extracted_text}")
                if grok_vision.get("extracted_text"):
                    # Use a combination of both for safety
                    extracted_text = f"{extracted_text} | Cross-check: {grok_vision.get('extracted_text')}"
                    eng_keywords = list(set(eng_keywords + grok_vision.get("search_query_used", "").split()))
            except Exception as e:
                print(f"[main] Grok Vision cross-check error: {e}")

        # --- Step 1b: DDG Image Search using Gemini keywords (no second Gemini call) ---
        rev_search = {"pages": [], "summary": "", "search_query": ""}
        try:
            rev_search = reverse_image_search(eng_keywords, is_global=is_global)
        except Exception as rev_err:
            print(f"DDG image search error: {rev_err}")

        rev_summary  = rev_search.get("summary", "")
        rev_pages    = rev_search.get("pages", [])

        # Combine reverse image sources
        combined_rev_pages = rev_pages.copy() if isinstance(rev_pages, list) else []

        # --- Step 2: Search Context (Tavily/DDG) ---
        # Use Gemini Vision's English keywords as primary query for text search
        text_search_query = ""
        if eng_keywords:
            text_search_query = " ".join(eng_keywords[:6])
            if extracted_text:
                text_search_query += " " + extracted_text
        else:
            text_search_query = extracted_text

        search_context = []
        if text_search_query.strip():
            # search_web internally uses Tavily as primary, DDG as fallback
            search_context = search_web(text_search_query)

        # --- Step 2b: Proactive SerpApi Google Lens (Image Origin Discovery) ---
        # Immediate fallback if global story, no normal search results found, or text is unclear/none
        serpapi_sources = []
        # AGGRESSIVE FORENSIC TRIGGER: If text is missing or messy, reverse search is our ONLY hope for provenance.
        proactive_trigger = is_global or not search_context or text_clarity in ['low', 'none'] or not extracted_text
        
        if proactive_trigger:
            reason = "global" if is_global else "no_context" if not search_context else "unclear_text"
            print(f"[main] Proactive SerpApi trigger (reason={reason})")
            try:
                if public_img_url:
                    database.log_request("[API] SerpApi Google Lens", f"[Proactive Origin Search] ({img_filename})", 0, "info", cost=0.001, case_id=case_id, api_name="SerpApi")
                    serpapi_sources = serpapi_google_lens(public_img_url)
                    if serpapi_sources:
                        search_context.append({"title": "🔍 ORIGINAL SOURCE DISCOVERY (Google Lens)", "snippet": str(serpapi_sources[:5]), "url": "google-lens-check"})
                        combined_rev_pages = serpapi_sources + combined_rev_pages
            except Exception as e:
                print(f"[main] Proactive SerpApi error: {e}")

        # Tier 0: RSS Pre-Check for Images
        rss_matches = search_rss_precheck(extracted_text, " ".join(eng_keywords))
        if rss_matches:
             search_context.insert(0, {"title": "🚨 VERIFIED FACT-CHECK (RSS)", "snippet": str(rss_matches), "url": "RSS_FEED"})

        # --- Step 3 & 4: Grok Text Analysis ---
        text_for_grok = f"Headline/Text extracted from image: {extracted_text}"
        if eng_keywords:
            text_for_grok += f" | Key concepts extracted: {', '.join(eng_keywords)}"

        database.log_request("[API] Grok 4.1 Reasoning", f"Headline/Text extracted from image: ({img_filename}) {extracted_text[:60]}", 0, "info", cost=0.0005, case_id=case_id, api_name="Grok")            
        analysis_result = analyze_with_grok(text_for_grok, str(search_context))

        # --- FINAL FALLBACK: Inconclusive result check ---
        score = analysis_result.get("score", 50)
        grok_sources = analysis_result.get("sources", [])

        # If still inconclusive AND we haven't run SerpApi yet, run it now
        if (40 < score < 60 or not grok_sources) and not serpapi_sources:
            print("[main] Still inconclusive. Searching SerpApi Google Lens as last resort...")
            try:
                if public_img_url:
                    database.log_request("[API] SerpApi Google Lens", f"[Fallback Origin Search] ({img_filename})", 0, "info", cost=0.001, case_id=case_id, api_name="SerpApi")
                    serpapi_sources = serpapi_google_lens(public_img_url)
                    if serpapi_sources:
                        search_context.append({"title": "🔍 LATE SOURCE DISCOVERY (Google Lens)", "snippet": str(serpapi_sources[:5]), "url": "google-lens-check"})
                        analysis_result = analyze_with_grok(text_for_grok, str(search_context))
                        combined_rev_pages = serpapi_sources + combined_rev_pages
            except Exception as e:
                print(f"[main] Fallback SerpApi error: {e}")

        # Supplement sources with reverse-image pages if Grok found none
        grok_sources = analysis_result.get("sources", [])
        if not grok_sources and combined_rev_pages:
            grok_sources = [
                {"title": p.get("title") or p.get("url", ""), "snippet": p.get("snippet", "พบภาพนี้บนหน้าเว็บนี้"), "link": p.get("url") or p.get("link", "")}
                for p in combined_rev_pages[:5]
            ]

        latency = int((time.time() - start_time) * 1000)
        log_id = database.log_request("/api/check-image", f"[Image Upload] ({img_filename})", latency, "success", cost=0.005, case_id=case_id)

        return {
            "log_id": log_id,
            "score": analysis_result.get("score", vision_result.get("score", 50)),
            "analysis": analysis_result.get("analysis", vision_result.get("analysis", "")),
            "sources": grok_sources,
            "original_source": analysis_result.get("original_source", "Unknown/Social Media"),
            "ai_generated_signals": vision_result.get("ai_generated_signals", []) + analysis_result.get("ai_signals", []),
            "ai_confidence_score": max(vision_result.get("ai_confidence_score", 0), analysis_result.get("ai_confidence_score", 0)),
            "visual_indicators": visual_indicators,
            "extracted_text": extracted_text,
            "case_id": case_id
        }
    except Exception as e:
        import traceback
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(traceback.format_exc() + "\n")
        return {
            "log_id": -1,
            "score": 50,
            "analysis": "ระบบขัดข้องชั่วคราว: ไม่สามารถตรวจสอบรูปภาพได้ในขณะนี้",
            "sources": [],
            "visual_indicators": [],
            "extracted_text": ""
        }

@app.post("/api/check-screenshot")
async def check_screenshot(files: List[UploadFile] = File(...)):
    check_kill_switch()
    start_time = time.time()
    try:
        # Guard: Max 3 files, 10MB each
        MAX_FILES = 3
        MAX_SIZE_MB = 10
        MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024
        if len(files) > MAX_FILES:
            raise HTTPException(status_code=400, detail=f"อัปโหลดได้สูงสุด {MAX_FILES} รูปต่อครั้ง")
        contents = [await file.read() for file in files]
        for file, content in zip(files, contents):
            if len(content) > MAX_SIZE_BYTES:
                size_mb = len(content) / (1024 * 1024)
                raise HTTPException(status_code=413, detail=f"ไฟล์ '{file.filename}' มีขนาด {size_mb:.1f}MB เกินขนาดสูงสุดที่อนุญาต ({MAX_SIZE_MB}MB)")
        
        # Upload first image to Cloudflare R2
        ext = "jpg"
        if files[0].filename and "." in files[0].filename:
            ext = files[0].filename.split(".")[-1].lower()
            
        img_filename = f"{uuid.uuid4().hex[:12]}.{ext}"
        upload_success = False
        try:
            content_type = files[0].content_type or "image/jpeg"
            upload_image(img_filename, contents[0], content_type=content_type)
            upload_success = True
        except Exception as up_err:
            print(f"[R2] Upload error: {up_err}")

        if upload_success:
            query_display = f"[Screenshot Upload] ({img_filename})"
        else:
            query_display = f"[Screenshot Upload FAILED] {files[0].filename}"
        vision_result = analyze_images_with_vision(contents, is_screenshot=True)
        
        extracted_text = vision_result.get("extracted_text", "")
        visual_indicators = vision_result.get("visual_indicators", [])
        
        # If text was extracted or visual indicators found, let AI verify it
        if extracted_text and len(extracted_text) > 5:
            # Tier 1: Free Search + Gemini
            search_context = search_web(extracted_text)

            analysis_result = analyze_text_claim(extracted_text, search_context=search_context)
            score = analysis_result.get("score", 50)
            
            # Tier 2: Escalate to Grok if inconclusive, no sources, or Gemini failed
            if (40 < score < 60) or not analysis_result.get("sources") or analysis_result.get("skip_to_grok"):
                prompt_for_grok = f"""
                A user uploaded a screenshot. OCR extracted the following text:
                "{extracted_text}"
                
                The Vision model also noted the following visual indicators:
                {visual_indicators}
                
                CRITICAL INSTRUCTION: If the image appears to be a graphic quote, a meme format, or text added onto a background for aesthetic/sharing purposes, DO NOT penalize the score just because the image is "manipulated" or "photoshopped". Focus heavily on evaluating the FACTUALITY of the extracted text claim by searching the live web.
                
                STEP 1 — UNDERSTAND THE CLAIM:
                Read the extracted text carefully. What is the actual claim being made? Identify:
                - The subject (animal, person, event, discovery, etc.)
                - The key assertion (first sighting, new record, scientific discovery, etc.)
                - Is this about a LOCAL (Thai) event or an INTERNATIONAL / GLOBAL story?
                
                STEP 2 — SEARCH IN THE RIGHT LANGUAGE:
                - If the claim is about a GLOBAL or INTERNATIONAL topic (e.g., a scientific discovery, world record, foreign event), you MUST search using ENGLISH keywords on international databases (Schmidt Ocean Institute, NOAA, Nature, BBC Science, Reuters, etc.).
                - Do NOT confine your search to Thai-language sources for international stories.
                - If the claim is about a Thai-specific event, also search Thai sources.
                - IMPORTANT: Do NOT paraphrase or reinterpret the claim. Search for what the text ACTUALLY says, not a Thai localization of it.
        
                TONE & STYLE INSTRUCTION: Write the final analysis in simple, everyday conversational Thai (ภาษาชาวบ้าน เข้าใจง่าย กระชับ ไม่เป็นวิชาการเกินไป). 
                
                CRITICAL FORMATTING INSTRUCTION: You MUST format the analysis text logically using Markdown. 
                1. CONCISENESS: Keep the analysis extremely short and to the point. Use a maximum of 3-4 short bullet points. Give the user exactly what they need to know without fluff.
                2. NO URLS IN TEXT: DO NOT include raw URLs (http...) or markdown links (e.g., [Text](URL)) inside the `analysis` text. It looks messy. Rely entirely on the `sources` JSON array to provide links.
                3. Use **bold text** to highlight important names, dates, or keywords.
                4. EVIDENCE OF SEARCH & MISSING DATA: You MUST explicitly state the breadth of your search. If you CANNOT find real evidence, state clearly: "**จากการตรวจสอบแหล่งข้อมูลข่าวที่น่าเชื่อถือหลัก** ไม่พบรายงานที่ยืนยันเรื่องนี้ได้"
                5. SOURCES: You MUST populate the `sources` JSON array. Format: [{{"title": "Headline", "snippet": "Quote", "link": "EXACT_WORKING_URL"}}]. CRITICAL: If you do not have the exact, working URL from a real news source, you MUST provide a Google search link to find it, formatted exactly like: "https://www.google.com/search?q=Keywords". NEVER hallucinate broken URLs or fake domains.
                """
                
                analysis_result = analyze_with_grok(prompt_for_grok, search_context=search_context)
                
                # --- LAST RESORT: SerpApi Google Lens for Screenshot ---
                grok_score = analysis_result.get("score", 50)
                grok_sources = analysis_result.get("sources", [])
                serpapi_sources = []

                if (40 < grok_score < 60) or not grok_sources:
                    print("[main] Inconclusive screenshot result. Searching SerpApi Google Lens as last resort...")
                    try:
                        if contents:
                            serpapi_sources = serpapi_google_lens(contents[0])
                            if serpapi_sources:
                                search_context.append({
                                    "title": "Google Lens Visual Matches", 
                                    "snippet": str(serpapi_sources), 
                                    "url": "reverse-image-search"
                                })
                                # Re-run Grok with the new visual matches context
                                analysis_result = analyze_with_grok(prompt_for_grok, search_context=search_context)
                    except Exception as e:
                        print(f"[main] SerpApi integration error in screenshot: {e}")
                
            latency = int((time.time() - start_time) * 1000)
            log_id = database.log_request("/api/check-screenshot", f"[Screenshot Analysed] {img_filename}", latency, "success", cost=0.005)
            
            # Supplement sources with reverse-image pages if Grok found none
            grok_sources = analysis_result.get("sources", [])
            if not grok_sources and serpapi_sources:
                grok_sources = [
                    {"title": p.get("title") or p.get("url", ""), "snippet": p.get("snippet", "พบภาพนี้บนหน้าเว็บนี้"), "link": p.get("url") or p.get("link", "")}
                    for p in serpapi_sources[:5]
                ]

            # Combine results
            return {
                "log_id": log_id,
                "score": analysis_result.get("score", vision_result.get("score", 50)),
                "analysis": analysis_result.get("analysis", vision_result.get("analysis", "")),
                "sources": grok_sources,
                "visual_indicators": visual_indicators,
                "extracted_text": extracted_text
            }
        else:
            # Fallback if no text to search
            analysis = vision_result.get("analysis", "Unable to analyze screenshot.")
            if not visual_indicators:
                analysis += " ไม่พบข้อความหรือจุดสังเกตในภาพที่สามารถนำไปตรวจสอบต่อได้"
                
            latency = int((time.time() - start_time) * 1000)
            log_id = database.log_request("/api/check-screenshot", f"[No Extracted Text] {img_filename}", latency, "success", cost=0.005)
            return {
                "log_id": log_id,
                "score": vision_result.get("score", 50),
                "analysis": analysis,
                "sources": [],
                "visual_indicators": visual_indicators,
                "extracted_text": extracted_text
            }
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        database.log_request("/api/check-screenshot", "[Screenshot Error]", latency, "error", str(e))
        return {
            "log_id": -1,
            "score": 50,
            "analysis": "ระบบขัดข้องชั่วคราว: ไม่สามารถตรวจสอบภาพ screenshot ได้ในขณะนี้",
            "sources": [],
            "visual_indicators": [],
            "extracted_text": ""
        }


class ChatRequest(BaseModel):
    message: str
    password: str

@app.post("/api/admin/stats")
async def admin_stats(req: Request):
    data = await req.json()
    if data.get("password") != os.getenv("ADMIN_PASSWORD", "admin123"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return database.get_dashboard_stats()

@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    try:
        database.save_feedback(req.log_id, req.is_helpful, req.reason, req.details)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/toggle-killswitch")
async def toggle_killswitch(req: ToggleKillSwitchRequest):
    if req.password != os.getenv("ADMIN_PASSWORD", "admin123"):
        raise HTTPException(status_code=403, detail="Forbidden")
    database.set_kill_switch(req.active)
    return {"status": "success", "kill_switch_active": req.active}

@app.get("/api/admin/image/{filename}")
async def serve_admin_image(filename: str):
    """Proxy image from R2/S3 to avoid CORS/access issues in admin dashboard."""
    if not filename or ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Use service to get URL
    target_url = get_image_url(filename)
    
    # Ensure protocol is present
    if not target_url.startswith("http"):
        target_url = f"https://{target_url}"
        
    print(f"[AdminImage] Proxying {filename} from {target_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(target_url, timeout=10) as resp:
                if resp.status != 200:
                    print(f"[AdminImage] Error: R2 returned status {resp.status} for {filename}")
                    if resp.status in [403, 404]:
                        raise HTTPException(status_code=resp.status, detail=f"Image {resp.status}")
                    return Response(status_code=resp.status, content=f"Image fetch failed: {resp.status}")
                
                content = await resp.read()
                content_type = resp.headers.get("Content-Type", "image/jpeg")
                return Response(
                    content=content,
                    media_type=content_type,
                    headers={
                        "Cache-Control": "public, max-age=86400",
                        "Access-Control-Allow-Origin": "*"
                    }
                )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AdminImage] Proxy error for {filename}: {str(e)}")
        return Response(status_code=502, content=f"Proxy error: {str(e)}")

@app.post("/api/admin/chat")
async def admin_chat(req: ChatRequest):
    if req.password != os.getenv("ADMIN_PASSWORD", "admin123"):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        stats = database.get_dashboard_stats()
        system_prompt = f"""You are a helpful IT Support AI for the Fact-Checking Dashboard.
Review the current system stats: {stats}
The user is the Administrator. Answer their question based on the stats in informative, conversational Thai language. Be extremely helpful and explain technical terms simply."""

        from services.llm_service import grok_client, get_next_client
        from google.genai import types as genai_types

        # Try Grok first (with model fallback), then Gemini
        grok_models = ["grok-4-1-fast-non-reasoning", "grok-4-1-fast-reasoning"]
        
        if grok_client:
            for model_name in grok_models:
                try:
                    response = grok_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": req.message}
                        ],
                        temperature=0.3
                    )
                    return {"reply": response.choices[0].message.content.strip()}
                except Exception as grok_err:
                    err_str = str(grok_err)
                    if "429" in err_str or "quota" in err_str.lower() or "exhausted" in err_str.lower() or "rate limit" in err_str.lower():
                        continue  # Try next Grok model
                    raise  # Re-raise non-rate-limit errors

        # Fallback: Gemini
        gemini_client = get_next_client()
        if gemini_client:
            gemini_prompt = f"{system_prompt}\n\nคำถามของแอดมิน: {req.message}"
            gem_response = gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=gemini_prompt,
                config=genai_types.GenerateContentConfig(temperature=0.3),
            )
            return {"reply": f"[Gemini Fallback] {gem_response.text.strip()}"}
        
        return {"reply": "ไม่สามารถติดต่อ AI ได้ในขณะนี้ (ทั้ง Grok และ Gemini ไม่พร้อมใช้งาน)"}
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "quota" in err_str.lower() or "exhausted" in err_str.lower() or "rate limit" in err_str.lower():
            return {"reply": "⚠️ ขออภัยครับ AI Support มีการเรียกใช้งานเกินโควต้า (Rate Limit Exceeded) กรุณารอสักครู่แล้วลองถามใหม่นะครับ 🙏"}
        return {"reply": f"เกิดข้อผิดพลาดในการเชื่อมต่อ AI: {e}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
