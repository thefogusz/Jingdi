import os
import uuid
import time
from typing import List

import aiohttp
import database
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from services.check_service import (
    build_image_search_queries,
    infer_image_origin_note,
    merge_search_results,
    run_text_check,
    run_url_check,
    stabilize_image_verdict,
)
from services.llm_service import analyze_text_claim, analyze_with_grok
from services.r2_service import get_image_url, upload_image
from services.reverse_image_service import reverse_image_search
from services.search_service import search_web
from services.vision_service import analyze_images_with_vision

load_dotenv()

app = FastAPI(title="Fake News Detection API")

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
            detail="ขออภัย ขณะนี้ระบบอยู่ระหว่างการปรับปรุงชั่วคราว (API Kill Switch is ON)",
        )


@app.post("/api/check-text")
async def check_text(payload: TextCheckRequest, request: Request):
    check_kill_switch()
    return await run_text_check(payload, request)


@app.post("/api/check-url")
def check_url(payload: UrlCheckRequest, request: Request):
    check_kill_switch()
    return run_url_check(payload)


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
        image_queries = build_image_search_queries(vision_result, rev_search)
        combined_context = (
            f"[VISION ANALYSIS]: {vision_analysis}\n"
            f"[VISUAL INDICATORS]: {', '.join(visual_indicators)}\n"
            f"[AI SIGNALS]: {', '.join(ai_signals)}\n\n{rev_summary}"
        )

        if extracted_text or image_queries:
            search_batches = [search_web(query, case_id) for query in image_queries] or [search_web(extracted_text, case_id)]
            search_context = merge_search_results(search_batches)
            full_context = f"{combined_context}\n\n[WEB SEARCH RESULTS]:\n{str(search_context)}"
            analysis_subject = extracted_text or " ".join(image_queries[:2])
            analysis_result = analyze_text_claim(f"Verify image claim: {analysis_subject}", full_context)
            if (40 < analysis_result.get("score", 50) < 60) or not analysis_result.get("sources"):
                analysis_result = analyze_with_grok(f"Verify image: {analysis_subject}", full_context)
        else:
            search_context = []
            analysis_result = analyze_with_grok("วิเคราะห์ภาพจากสิ่งที่เห็นและประวัติภาพจาก Google", combined_context)

        origin_note = infer_image_origin_note(vision_result, rev_search, search_context)
        if origin_note and origin_note not in analysis_result.get("analysis", ""):
            analysis_result["analysis"] = f"{origin_note}\n\n{analysis_result.get('analysis', '')}".strip()
        analysis_result = stabilize_image_verdict(analysis_result, vision_result, search_context)

        latency = int((time.time() - start_time) * 1000)
        log_id = database.log_request(
            "/api/check-image",
            f"[Image Upload] {img_filename}",
            latency,
            "success",
            cost=0.005,
            case_id=case_id,
            image_filename=img_filename,
        )
        return {
            "log_id": log_id,
            "score": analysis_result.get("score", 50),
            "analysis": analysis_result.get("analysis", ""),
            "sources": analysis_result.get("sources", []),
            "extracted_text": extracted_text,
            "visual_indicators": visual_indicators,
            "ai_signals": ai_signals,
        }
    except Exception as exc:
        return {"log_id": -1, "score": 50, "analysis": f"เกิดข้อผิดพลาด: {str(exc)}", "sources": []}


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
        image_queries = build_image_search_queries(vision_result, rev_search)
        combined_context = (
            f"[VISION ANALYSIS]: {vision_analysis}\n"
            f"[VISUAL INDICATORS]: {', '.join(visual_indicators)}\n"
            f"[AI SIGNALS]: {', '.join(ai_signals)}\n\n{rev_summary}"
        )

        if extracted_text or image_queries:
            search_batches = [search_web(query, case_id) for query in image_queries] or [search_web(extracted_text, case_id)]
            search_context = merge_search_results(search_batches)
            full_context = f"{combined_context}\n\n[WEB SEARCH RESULTS]:\n{str(search_context)}"
            analysis_subject = extracted_text or " ".join(image_queries[:2])
            analysis_result = analyze_text_claim(f"Verify screenshot claim: {analysis_subject}", full_context)
            if (40 < analysis_result.get("score", 50) < 60) or not analysis_result.get("sources"):
                analysis_result = analyze_with_grok(f"Verify screenshot: {analysis_subject}", full_context)
        else:
            search_context = []
            analysis_result = analyze_with_grok("วิเคราะห์ภาพจากสิ่งที่เห็นและประวัติภาพจาก Google", combined_context)

        origin_note = infer_image_origin_note(vision_result, rev_search, search_context)
        if origin_note and origin_note not in analysis_result.get("analysis", ""):
            analysis_result["analysis"] = f"{origin_note}\n\n{analysis_result.get('analysis', '')}".strip()
        analysis_result = stabilize_image_verdict(analysis_result, vision_result, search_context)

        latency = int((time.time() - start_time) * 1000)
        log_id = database.log_request(
            "/api/check-screenshot",
            f"[Screenshot] {img_filename}",
            latency,
            "success",
            cost=0.005,
            case_id=case_id,
            image_filename=img_filename,
        )
        return {
            "log_id": log_id,
            "score": analysis_result.get("score", 50),
            "analysis": analysis_result.get("analysis", ""),
            "sources": analysis_result.get("sources", []),
            "extracted_text": extracted_text,
            "visual_indicators": visual_indicators,
            "ai_signals": ai_signals,
        }
    except Exception as exc:
        return {"log_id": -1, "score": 50, "analysis": f"Error: {str(exc)}", "sources": []}


@app.post("/api/admin/stats")
async def admin_stats(req: Request):
    data = await req.json()
    if data.get("password") != os.getenv("ADMIN_PASSWORD", "admin123"):
        raise HTTPException(status_code=403)
    return database.get_dashboard_stats()


@app.post("/api/admin/toggle-killswitch")
async def toggle_killswitch(req: ToggleKillSwitchRequest):
    if req.password != os.getenv("ADMIN_PASSWORD", "admin123"):
        raise HTTPException(status_code=403)
    database.set_kill_switch(req.active)
    return {"status": "success"}


@app.get("/api/admin/image/{filename}")
async def serve_admin_image(filename: str):
    target_url = get_image_url(filename)
    async with aiohttp.ClientSession() as session:
        async with session.get(target_url) as resp:
            if resp.status != 200:
                return Response(status_code=resp.status)
            return Response(content=await resp.read(), media_type=resp.headers.get("Content-Type", "image/jpeg"))


@app.post("/api/admin/chat")
async def admin_chat(req: ChatRequest):
    if req.password != os.getenv("ADMIN_PASSWORD", "admin123"):
        raise HTTPException(status_code=403)
    stats = database.get_dashboard_stats()
    analysis_result = analyze_with_grok(req.message, search_context=str(stats))
    return {"reply": analysis_result.get("analysis")}


@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest, background_tasks: BackgroundTasks):
    database.save_feedback(req.log_id, req.is_helpful, req.reason, req.details)
    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
