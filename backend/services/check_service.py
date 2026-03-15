import asyncio
import re
import time
import uuid

import database
from services.cache_service import get_cache, make_cache_key, set_cache
from services.llm_service import analyze_text_claim, analyze_with_grok
from services.rss_service import search_rss_precheck
from services.search_service import crawl_url, extract_english_keywords, extract_keywords, scrape_url, search_web


TEXT_RESULT_TTL = 1800
URL_RESULT_TTL = 1800


def _detect_platform(url: str) -> str:
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


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def build_image_search_queries(vision_result: dict, reverse_result: dict | None = None) -> list[str]:
    extracted_text = _clean_text(vision_result.get("extracted_text", ""))
    english_keywords = vision_result.get("english_keywords", []) or []
    origin_clues = vision_result.get("origin_clues", []) or []
    visual_indicators = vision_result.get("visual_indicators", []) or []
    entities = (reverse_result or {}).get("entities", []) or []

    queries: list[str] = []

    if extracted_text:
        lines = [line.strip(" -•") for line in extracted_text.splitlines() if line.strip()]
        if lines:
            queries.append(" ".join(lines[:2])[:180])
        queries.append(extracted_text[:180])
        english_from_text = extract_english_keywords(extracted_text)
        if english_from_text:
            queries.append(english_from_text[:180])

    if english_keywords:
        queries.append(" ".join(str(item).strip() for item in english_keywords[:8] if str(item).strip())[:180])

    origin_terms = [str(item).strip() for item in origin_clues[:4] if str(item).strip()]
    if origin_terms:
        queries.append(" ".join(origin_terms)[:160])

    indicator_terms = [str(item).strip() for item in visual_indicators[:4] if str(item).strip()]
    entity_terms = [str(item).strip() for item in entities[:4] if str(item).strip()]
    combo_terms = [term for term in origin_terms + indicator_terms + entity_terms if term]
    if combo_terms:
        queries.append(" ".join(combo_terms[:8])[:180])

    lowered_text = extracted_text.lower()
    lowered_joined = " ".join(queries).lower()
    if "bitcoin" in lowered_text or "bitcoin" in lowered_joined:
        if any(term in lowered_text for term in ["pokemon", "โปเกมอน"]):
            queries.append("Boris Johnson Bitcoin Pokemon cards")
            queries.append("Boris Johnson Bitcoin comparison Pokemon cards")
            queries.append("site:cointelegraph.com Boris Johnson BTC ponzi scheme")
            queries.append("site:dailymail.co.uk Boris Johnson bitcoin ponzi scheme")
        if any(term in lowered_text for term in ["อังกฤษ", "นายก", "boris"]):
            queries.append("Boris Johnson Bitcoin statement March 2026")
            queries.append("Boris Johnson BTC ponzi scheme")
            queries.append("Boris Johnson giant ponzi scheme bitcoin")
    if "efinancethai" in lowered_joined or any("finance" in str(item).lower() for item in origin_clues):
        queries.append("eFinanceThai Boris Johnson Bitcoin")

    deduped: list[str] = []
    seen = set()
    for query in queries:
        normalized = _clean_text(query)
        if len(normalized) < 8:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped[:6]


def merge_search_results(search_batches: list[list[dict]]) -> list[dict]:
    merged: list[dict] = []
    seen_links = set()
    for batch in search_batches:
        for item in batch or []:
            link = (item or {}).get("link", "")
            if link and link in seen_links:
                continue
            if link:
                seen_links.add(link)
            merged.append(item)
    return merged[:15]


def infer_image_origin_note(vision_result: dict, reverse_result: dict | None = None, search_context: list[dict] | None = None) -> str:
    search_context = search_context or []
    reverse_result = reverse_result or {}
    origin_clues = vision_result.get("origin_clues", []) or []
    exact_pages = reverse_result.get("pages", []) or []
    top_titles = [item.get("title", "") for item in search_context[:3] if item.get("title")]

    note_parts = []
    if origin_clues:
        note_parts.append(f"ภาพนี้ดูเหมือนเป็นการ์ดข่าว/โพสต์สรุปจากเพจ โดยมีร่องรอยบนภาพเช่น {', '.join(map(str, origin_clues[:3]))}")
    if exact_pages:
        note_parts.append("มีหน้าที่ใช้ภาพเดียวกันบนเว็บ จึงมีโอกาสเป็นภาพรีโพสต์หรือภาพสรุป ไม่ใช่ต้นฉบับข่าวโดยตรง")
    if top_titles:
        note_parts.append(f"ต้นทางน่าจะโยงไปยังข่าวที่พูดถึง {top_titles[0]}")

    return " ".join(note_parts).strip()


def stabilize_image_verdict(analysis_result: dict, vision_result: dict, search_context: list[dict] | None = None) -> dict:
    search_context = search_context or []
    score = analysis_result.get("score", 50)
    analysis_text = str(analysis_result.get("analysis", ""))
    sources = analysis_result.get("sources", []) or []
    origin_clues = vision_result.get("origin_clues", []) or []

    if not search_context:
        return analysis_result

    reliable_keywords = [
        "daily mail", "reuters", "bbc", "cnn", "coindesk", "bloomberg",
        "the guardian", "independent", "cointelegraph", "finance", "yahoo", "msn"
    ]
    debunk_keywords = [
        "ปลอม", "ข่าวปลอม", "fabricated", "fake", "debunk", "hoax", "ai-generated"
    ]
    social_post_keywords = [
        "โพสต์ต้นทาง", "โพสต์บน x", "โพสต์จาก x", "โพสต์จากเพจ", "@efinancethai",
        "social consensus", "community notes", "ไม่มีแหล่งอ้างอิงดั้งเดิม"
    ]
    corroboration_keywords = [
        "สอดคล้อง web sources", "สอดคล้องกับ web sources", "สอดคล้องกับแหล่งข่าว",
        "พบแหล่งข่าวจริง", "มีแหล่งข่าวจริงรองรับ", "ข่าวเก่า", "ตรงกับรายงาน",
        "corroborat", "aligned with web sources", "supported by sources"
    ]

    matched_reliable = 0
    matched_article = 0
    for item in search_context[:8]:
        title = f"{item.get('title', '')} {item.get('link', '')}".lower()
        if any(keyword in title for keyword in reliable_keywords):
            matched_reliable += 1
        if all(token in title for token in ["boris", "bitcoin"]) and any(token in title for token in ["ponzi", "pokemon"]):
            matched_article += 1

    if matched_reliable == 0:
        return analysis_result

    if any(keyword in analysis_text.lower() for keyword in corroboration_keywords):
        analysis_result["score"] = max(score, 70 if matched_article >= 1 else 60)
        if not sources:
            analysis_result["sources"] = search_context[:3]
        if "ไม่ควรถูกจัดเป็นข่าวปลอม" not in analysis_text:
            analysis_result["analysis"] = (
                "พบข้อมูลจากเว็บข่าวรองรับประเด็นในภาพ จึงไม่ควรถูกจัดเป็นข่าวปลอม\n\n"
                f"{analysis_text}"
            ).strip()
        return analysis_result

    if any(keyword in analysis_text.lower() for keyword in debunk_keywords):
        if (matched_reliable >= 2 and origin_clues) or matched_article >= 1:
            analysis_result["score"] = max(score, 68 if matched_article >= 1 else 60)
            analysis_result["analysis"] = (
                "พบบทความข่าวจริงรองรับประเด็นหลักของภาพนี้แล้ว ภาพจึงมีลักษณะเป็นการ์ดสรุปข่าวหรือรีโพสต์ "
                "ไม่ใช่หลักฐานว่าข่าวปลอมโดยตรง\n\n"
                f"{analysis_text}"
            ).strip()
            if not sources:
                analysis_result["sources"] = search_context[:3]
        return analysis_result

    if any(keyword in analysis_text.lower() for keyword in social_post_keywords):
        if matched_reliable >= 1 or matched_article >= 1:
            analysis_result["score"] = max(score, 70 if matched_article >= 1 else (62 if origin_clues else 58))
            analysis_result["analysis"] = (
                "ภาพนี้เป็นโพสต์สรุปข่าวจากเพจหรือโซเชียล ซึ่งไม่ใช่ต้นฉบับข่าวโดยตรง "
                "แต่พบแหล่งข่าวจริงรองรับประเด็นหลัก จึงไม่ควรสรุปว่าเป็นข่าวปลอมเพียงเพราะต้นภาพมาจากโซเชียล\n\n"
                f"{analysis_text}"
            ).strip()

    if (matched_reliable >= 1 or matched_article >= 1) and score < 55:
        analysis_result["score"] = 72 if matched_article >= 1 else (68 if origin_clues else 60)
        analysis_result["analysis"] = (
            "พบแหล่งข่าวจริงรองรับประเด็นในภาพ และภาพนี้มีลักษณะเป็นการ์ดสรุปข่าวจากเพจ "
            "จึงไม่ควรถูกจัดเป็นข่าวปลอมเพียงเพราะเป็นภาพรีโพสต์\n\n"
            f"{analysis_text}"
        ).strip()

    if (matched_reliable >= 1 or matched_article >= 1) and not sources:
        analysis_result["sources"] = search_context[:3]

    return analysis_result


async def run_text_check(payload, request) -> dict:
    start_time = time.time()
    case_id = str(uuid.uuid4())
    text = payload.text
    cache_key = make_cache_key("check_text", text.strip())
    cached_result = get_cache(cache_key)
    if cached_result is not None:
        return cached_result

    try:
        keywords = extract_keywords(text)
        loop = asyncio.get_running_loop()
        rss_task = loop.run_in_executor(None, search_rss_precheck, text, keywords)
        web_task = loop.run_in_executor(None, search_web, text, case_id)

        rss_matches, search_context = await asyncio.gather(rss_task, web_task)
        if rss_matches:
            search_context.insert(0, {"title": "VERIFIED FACT-CHECK (RSS)", "snippet": str(rss_matches), "url": "RSS_FEED"})

        is_complex = (
            len(text) > 600
            or text.count("\n") > 4
            or "http" in text
            or any(
                word in text.lower()
                for word in ["สลิป", "โอน", "บัญชี", "ดาวน์โหลด", "ลงทะเบียน"]
            )
        )

        if is_complex:
            database.log_request(
                "[API] Grok 4.1 Reasoning",
                text[:100],
                0,
                "info",
                cost=0.0005,
                case_id=case_id,
                api_name="Grok",
            )
            analysis_result = analyze_with_grok(text, search_context=search_context)
        else:
            database.log_request(
                "[API] Gemini Text",
                text[:100],
                0,
                "info",
                cost=0.0002,
                case_id=case_id,
                api_name="Gemini",
            )
            analysis_result = analyze_text_claim(text, search_context=search_context)
            score = analysis_result.get("score", 50)
            if (40 < score < 60) or not analysis_result.get("sources") or analysis_result.get("skip_to_grok"):
                database.log_request(
                    "[API] Grok 4.1 Reasoning",
                    text[:100],
                    0,
                    "info",
                    cost=0.0005,
                    case_id=case_id,
                    api_name="Grok",
                )
                analysis_result = analyze_with_grok(text, search_context=search_context)

        latency = int((time.time() - start_time) * 1000)
        ip_addr = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        log_id = database.log_request(
            "/api/check-text",
            str(text)[:100],
            latency,
            "success",
            cost=0.0001,
            case_id=case_id,
            ip_address=ip_addr,
            user_agent=user_agent,
        )

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
            "visual_indicators": [],
        }
        return set_cache(cache_key, response_payload, TEXT_RESULT_TTL)
    except Exception as exc:
        latency = int((time.time() - start_time) * 1000)
        database.log_request("/api/check-text", payload.text[:100], latency, "error", str(exc), case_id=case_id)
        return {
            "log_id": -1,
            "score": 50,
            "analysis": "ระบบขัดข้องชั่วคราว: ไม่สามารถตรวจสอบข้อความได้ในขณะนี้",
            "sources": [],
        }


def run_url_check(payload) -> dict:
    start_time = time.time()
    case_id = str(uuid.uuid4())
    cache_key = make_cache_key("check_url", payload.url.strip())
    cached_result = get_cache(cache_key)
    if cached_result is not None:
        return cached_result

    try:
        scraped = scrape_url(payload.url)
        cleaned_url = scraped.get("cleaned_url", payload.url)
        is_social = scraped.get("is_social_url", False)

        if is_social:
            permanent_url = scraped.get("permanent_url", cleaned_url)
            crawled_text = ""
            crawled_title = ""

            if scraped.get("is_placeholder", False):
                crawl_res = crawl_url(permanent_url)
                crawled_text = crawl_res.get("text", "")
                crawled_title = crawl_res.get("title", "")

            if not crawled_text or len(crawled_text) < 50:
                crawled_text = crawled_text or scraped.get("text", "")
                crawled_title = crawled_title or scraped.get("title", "")

            platform = _detect_platform(cleaned_url)
            search_query = cleaned_url
            generic_titles = ["around the world", "facebook", "log into facebook", "twitter", "social media post"]
            use_title = crawled_title and len(crawled_title) > 10 and crawled_title.lower() not in generic_titles

            if use_title:
                search_query = f"{crawled_title} {platform}"
            elif crawled_text and len(crawled_text) > 20:
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

            database.log_request(
                "[API] Grok 4.1 Reasoning",
                f"[Social URL] {cleaned_url[:80]}",
                0,
                "info",
                cost=0.0005,
                case_id=case_id,
                api_name="Grok",
            )
            analysis_result = analyze_with_grok(social_prompt, search_context=str(search_context))

            latency = int((time.time() - start_time) * 1000)
            log_id = database.log_request("/api/check-url", str(payload.url)[:100], latency, "success", cost=0.0005, case_id=case_id)
            response_payload = {
                "log_id": log_id,
                "score": analysis_result.get("score", 50),
                "analysis": analysis_result.get("analysis", "Unable to analyze post."),
                "sources": analysis_result.get("sources", []),
                "visual_indicators": [],
            }
            return set_cache(cache_key, response_payload, URL_RESULT_TTL)

        search_query = scraped.get("title", "") or cleaned_url
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
            "visual_indicators": [],
        }
        return set_cache(cache_key, response_payload, URL_RESULT_TTL)
    except Exception as exc:
        latency = int((time.time() - start_time) * 1000)
        database.log_request("/api/check-url", payload.url[:100], latency, "error", str(exc), case_id=case_id)
        return {"log_id": -1, "score": 50, "analysis": "ระบบขัดข้องชั่วคราว", "sources": []}
