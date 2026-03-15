import os
import asyncio
import aiohttp
import uuid
import time
import database
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv

from services.llm_service import analyze_text_claim, analyze_with_grok, analyze_image_fact_check, get_next_client
from services.cache_service import get_cache, make_cache_key, set_cache
from services.search_service import search_web, scrape_url, crawl_url, extract_keywords
from services.vision_service import analyze_images_with_vision
from services.reverse_image_service import reverse_image_search
from services.rss_service import search_rss_precheck
from services.r2_service import upload_image, get_image_url

load_dotenv()

app = FastAPI(title="Fake News Detection API")

TEXT_RESULT_TTL = int(os.getenv("TEXT_RESULT_TTL", "1800"))
URL_RESULT_TTL = int(os.getenv("URL_RESULT_TTL", "1800"))

# Configure CORS for Next.js frontend
_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://jingdi.online",
    "https://www.jingdi.online",
]
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

class ChatRequest(BaseModel):
    message: str
    password: str

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
    """Verify Cloudflare Turnstile token to block bots."""
    if not TURNSTILE_SECRET:
        return
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
async def check_text(payload: TextCheckRequest, request: Request):
    check_kill_switch()
    start_time = time.time()
    case_id = str(uuid.uuid4())
    try:
        text = payload.text
        cache_key = make_cache_key("check_text", text.strip())
        cached_result = get_cache(cache_key)
        if cached_result is not None:
            return cached_result

        # Tier 0 & 1: Concurrent RSS & Web Search
        keywords = extract_keywords(text)
        loop = asyncio.get_running_loop()
        rss_task = loop.run_in_executor(None, search_rss_precheck, text, keywords)
        web_task = loop.run_in_executor(None, search_web, text, case_id)
        
        rss_matches, search_context = await asyncio.gather(rss_task, web_task)
        if rss_matches:
             search_context.insert(0, {"title": "🚨 VERIFIED FACT-CHECK (RSS)", "snippet": str(rss_matches), "url": "RSS_FEED"})
        
        # Smart Tier Routing
        is_complex = (len(text) > 600 or text.count('\n') > 4 or 'http' in text or 
                      any(w in text.lower() for w in ['สลิป', 'โอน', 'บัญชี', 'ดาวน์โหลด', 'ลงทะเบียน']))
        
        if is_complex:
            database.log_request("[API] Grok 4.1 Reasoning", text[:100], 0, "info", cost=0.0005, case_id=case_id, api_name="Grok")
            analysis_result = analyze_with_grok(text, search_context=search_context)
        else:
            database.log_request("[API] Gemini Text", text[:100], 0, "info", cost=0.0002, case_id=case_id, api_name="Gemini")
            analysis_result = analyze_text_claim(text, search_context=search_context)
            score = analysis_result.get("score", 50)
            if (40 < score < 60) or not analysis_result.get("sources") or analysis_result.get("skip_to_grok"):
                database.log_request("[API] Grok 4.1 Reasoning", text[:100], 0, "info", cost=0.0005, case_id=case_id, api_name="Grok")
                analysis_result = analyze_with_grok(text, search_context=search_context)
            
        latency = int((time.time() - start_time) * 1000)
        ip_addr = request.client.host if request.client else "unknown"
        ua = request.headers.get("user-agent", "unknown")
        log_id = database.log_request("/api/check-text", str(text)[:100], latency, "success", cost=0.0001, case_id=case_id, ip_address=ip_addr, user_agent=ua)
        
        response_payload = {
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
        return set_cache(cache_key, response_payload, TEXT_RESULT_TTL)
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        database.log_request("/api/check-text", payload.text[:100], latency, "error", str(e), case_id=case_id)
        return {"log_id": -1, "score": 50, "analysis": "ระบบขัดข้องชั่วคราว: ไม่สามารถตรวจสอบข้อความได้ในขณะนี้", "sources": []}

def _detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "facebook.com" in url_lower or "fb.com" in url_lower or "fb.watch" in url_lower: return "Facebook"
    if "instagram.com" in url_lower: return "Instagram"
    if "twitter.com" in url_lower or "x.com" in url_lower: return "X (Twitter)"
    if "tiktok.com" in url_lower: return "TikTok"
    return "Social Media"

@app.post("/api/check-url")
def check_url(payload: UrlCheckRequest, request: Request):
    check_kill_switch()
    start_time = time.time()
    case_id = str(uuid.uuid4())
    try:
        cache_key = make_cache_key("check_url", payload.url.strip())
        cached_result = get_cache(cache_key)
        if cached_result is not None:
            return cached_result

        scraped = scrape_url(payload.url)
        cleaned_url = scraped.get('cleaned_url', payload.url)
        is_social = scraped.get('is_social_url', False)

        if is_social:
            permanent_url = scraped.get('permanent_url', cleaned_url)
            is_placeholder = scraped.get('is_placeholder', False)
            
            print(f"[check-url] Social media URL detected: {permanent_url} (is_placeholder={is_placeholder})")
            
            # If it's a placeholder (login wall), we MUST crawl
            crawl_res = crawl_url(permanent_url)
            
            crawled_text = crawl_res.get("text", "")
            crawled_title = crawl_res.get("title", "")
            
            # Fallback only if crawl actually failed OR if crawl returned something worse
            if not crawled_text or len(crawled_text) < 50:
                crawled_text = crawled_text or scraped.get("text", "")
                crawled_title = crawled_title or scraped.get("title", "")
            
            # Smart search query selection
            # Use the title if it's substantive, otherwise use a snippet of the text
            platform = _detect_platform(cleaned_url)
            search_query = cleaned_url
            
            generic_titles = ["around the world", "facebook", "log into facebook", "twitter", "social media post"]
            use_title = crawled_title and len(crawled_title) > 10 and crawled_title.lower() not in generic_titles
            
            if use_title:
                search_query = f"{crawled_title} {platform}"
            elif crawled_text and len(crawled_text) > 20:
                # Use first 100 chars of text as query
                search_query = crawled_text[:100].strip()
            
            search_context = search_web(search_query, case_id)
            
            social_prompt = f"""Fact-check this {platform} post: {cleaned_url}
Title/Headline: {crawled_title or 'N/A'}
Extracted Content: {crawled_text or 'Direct extraction failed. Use search grounding.'}

INSTRUCTION: 
1. Use the provided search context to verify the claims in the extracted content.
2. If extraction failed, identify the post content from the search snippets.
3. Determine if the news is real, fake, or missing context.
4. Format with 3-4 bullet points in Thai."""

            database.log_request("[API] Grok 4.1 Reasoning", f"[Social URL] {cleaned_url[:80]}", 0, "info", cost=0.0005, case_id=case_id, api_name="Grok")
            analysis_result = analyze_with_grok(social_prompt, search_context=str(search_context))
            
            latency = int((time.time() - start_time) * 1000)
            log_id = database.log_request("/api/check-url", str(payload.url)[:100], latency, "success", cost=0.0005, case_id=case_id)
            response_payload = {
                "log_id": log_id,
                "score": analysis_result.get("score", 50),
                "analysis": analysis_result.get("analysis", "Unable to analyze post."),
                "sources": analysis_result.get("sources", []),
                "visual_indicators": []
            }
            return set_cache(cache_key, response_payload, URL_RESULT_TTL)

        # Normal URL Path
        search_query = scraped.get('title', '') or cleaned_url
        search_context = search_web(search_query, case_id)
        combined_context = f"Scraped Content: {scraped.get('text', 'N/A')}\n\nSearch: {search_context}"
        analysis_result = analyze_text_claim(f"Verify article: {cleaned_url}", search_context=combined_context)
        
        if (40 < analysis_result.get("score", 50) < 60) or not analysis_result.get("sources"):
             analysis_result = analyze_with_grok(f"Verify story: {cleaned_url}", search_context=search_context)

        latency = int((time.time() - start_time) * 1000)
        log_id = database.log_request("/api/check-url", payload.url[:100], latency, "success", cost=0.0005, case_id=case_id)
        response_payload = {
            "log_id": log_id,
            "score": analysis_result.get("score", 50),
            "analysis": analysis_result.get("analysis", ""),
            "sources": analysis_result.get("sources", []),
            "visual_indicators": []
        }
        return set_cache(cache_key, response_payload, URL_RESULT_TTL)
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        database.log_request("/api/check-url", payload.url[:100], latency, "error", str(e), case_id=case_id)
        return {"log_id": -1, "score": 50, "analysis": "ระบบขัดข้องชั่วคราว", "sources": []}

@app.post("/api/check-image")
async def check_image(request: Request, files: List[UploadFile] = File(...)):
    case_id = str(uuid.uuid4())
    check_kill_switch()
    start_time = time.time()
    try:
        contents = [await file.read() for file in files]
        img_filename = f"{uuid.uuid4().hex[:12]}.jpg"
        public_img_url = upload_image(img_filename, contents[0])
        
        vision_result = analyze_images_with_vision(contents, is_screenshot=False)
        extracted_text = vision_result.get("extracted_text", "")
        visual_indicators = vision_result.get("visual_indicators", [])
        ai_signals = vision_result.get("ai_generated_signals", [])
        vision_analysis = vision_result.get("analysis", "")
        
        rev_search = reverse_image_search(public_img_url) if public_img_url else {}
        rev_summary = rev_search.get("summary", "")
        
        # Merge vision/reverse search into search context for text analyzer
        combined_context = f"[VISION ANALYSIS]: {vision_analysis}\n[VISUAL INDICATORS]: {', '.join(visual_indicators)}\n[AI SIGNALS]: {', '.join(ai_signals)}\n\n{rev_summary}"
        
        if extracted_text:
            search_context = search_web(extracted_text, case_id)
            full_context = f"{combined_context}\n\n[WEB SEARCH RESULTS]:\n{str(search_context)}"
            analysis_result = analyze_text_claim(f"Verify image claim: {extracted_text}", full_context)
            if (40 < analysis_result.get("score", 50) < 60) or not analysis_result.get("sources"):
                analysis_result = analyze_with_grok(f"Verify image: {extracted_text}", full_context)
        else:
            # No text in image - use high-reasoning model (Gemini 3/Grok) to analyze visual/reverse search results
            analysis_result = analyze_with_grok("วิเคราะห์ภาพจากสิ่งที่เห็นและประวัติภาพจาก Google", combined_context)
            
        latency = int((time.time() - start_time) * 1000)
        log_id = database.log_request("/api/check-image", f"[Image Upload] {img_filename}", latency, "success", cost=0.005, case_id=case_id)
        
        # Merge results for final output
        return {
            "log_id": log_id,
            "score": analysis_result.get("score", 50),
            "analysis": analysis_result.get("analysis", ""),
            "sources": analysis_result.get("sources", []),
            "extracted_text": extracted_text,
            "visual_indicators": visual_indicators,
            "ai_signals": ai_signals
        }
    except Exception as e:
        return {"log_id": -1, "score": 50, "analysis": f"เกิดข้อผิดพลาด: {str(e)}", "sources": []}

@app.post("/api/check-screenshot")
async def check_screenshot(request: Request, files: List[UploadFile] = File(...)):
    case_id = str(uuid.uuid4())
    check_kill_switch()
    start_time = time.time()
    try:
        contents = [await file.read() for file in files]
        img_filename = f"screenshot_{uuid.uuid4().hex[:12]}.jpg"
        public_img_url = upload_image(img_filename, contents[0])
        
        vision_result = analyze_images_with_vision(contents, is_screenshot=True)
        extracted_text = vision_result.get("extracted_text", "")
        visual_indicators = vision_result.get("visual_indicators", [])
        ai_signals = vision_result.get("ai_generated_signals", [])
        vision_analysis = vision_result.get("analysis", "")

        rev_search = reverse_image_search(public_img_url) if public_img_url else {}
        rev_summary = rev_search.get("summary", "")

        combined_context = f"[VISION ANALYSIS]: {vision_analysis}\n[VISUAL INDICATORS]: {', '.join(visual_indicators)}\n[AI SIGNALS]: {', '.join(ai_signals)}\n\n{rev_summary}"

        if extracted_text:
            search_context = search_web(extracted_text, case_id)
            full_context = f"{combined_context}\n\n[WEB SEARCH RESULTS]:\n{str(search_context)}"
            analysis_result = analyze_text_claim(f"Verify screenshot claim: {extracted_text}", full_context)
            if (40 < analysis_result.get("score", 50) < 60) or not analysis_result.get("sources"):
                analysis_result = analyze_with_grok(f"Verify screenshot: {extracted_text}", full_context)
        else:
            analysis_result = analyze_with_grok("วิเคราะห์ภาพจากสิ่งที่เห็นและประวัติภาพจาก Google", combined_context)

        latency = int((time.time() - start_time) * 1000)
        log_id = database.log_request("/api/check-screenshot", f"[Screenshot] {img_filename}", latency, "success", cost=0.005, case_id=case_id)
        
        return {
            "log_id": log_id,
            "score": analysis_result.get("score", 50),
            "analysis": analysis_result.get("analysis", ""),
            "sources": analysis_result.get("sources", []),
            "extracted_text": extracted_text,
            "visual_indicators": visual_indicators,
            "ai_signals": ai_signals
        }
    except Exception as e:
        return {"log_id": -1, "score": 50, "analysis": f"Error: {str(e)}", "sources": []}

@app.post("/api/admin/stats")
async def admin_stats(req: Request):
    data = await req.json()
    if data.get("password") != os.getenv("ADMIN_PASSWORD", "admin123"): raise HTTPException(status_code=403)
    return database.get_dashboard_stats()

@app.post("/api/admin/toggle-killswitch")
async def toggle_killswitch(req: ToggleKillSwitchRequest):
    if req.password != os.getenv("ADMIN_PASSWORD", "admin123"): raise HTTPException(status_code=403)
    database.set_kill_switch(req.active)
    return {"status": "success"}

@app.get("/api/admin/image/{filename}")
async def serve_admin_image(filename: str):
    target_url = get_image_url(filename)
    async with aiohttp.ClientSession() as session:
        async with session.get(target_url) as resp:
            if resp.status != 200: return Response(status_code=resp.status)
            return Response(content=await resp.read(), media_type=resp.headers.get("Content-Type", "image/jpeg"))

@app.post("/api/admin/chat")
async def admin_chat(req: ChatRequest):
    if req.password != os.getenv("ADMIN_PASSWORD", "admin123"): raise HTTPException(status_code=403)
    stats = database.get_dashboard_stats()
    system_prompt = f"You are IT Support. Stats: {stats}. Answer questions in conversational Thai."
    analysis_result = analyze_with_grok(req.message, search_context=str(stats))
    return {"reply": analysis_result.get("analysis")}

@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest, background_tasks: BackgroundTasks):
    database.save_feedback(req.log_id, req.is_helpful, req.reason, req.details)
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
