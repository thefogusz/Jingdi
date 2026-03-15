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
        res = requests.get(url, headers=headers, timeout=6.0, verify=False, allow_redirects=True, stream=True)
        res.close()
        if res.status_code in [400, 404, 410] or res.status_code >= 500:
            return False
        return True
    except Exception:
        return False

# Initialize Grok
xai_api_key = os.getenv("XAI_API_KEY")
grok_client = OpenAI(
    api_key=xai_api_key,
    base_url="https://api.x.ai/v1",
) if xai_api_key else None

def _unique_models(*models: str) -> list[str]:
    seen = set()
    ordered = []
    for model in models:
        if model and model not in seen:
            seen.add(model)
            ordered.append(model)
    return ordered

TEXT_GROK_MODELS = _unique_models(
    os.getenv("XAI_TEXT_MODEL"),
    "grok-4-1-fast-reasoning",
    "grok-4-1-fast",
    "grok-4-1-fast-non-reasoning",
)

VISION_GROK_MODELS = _unique_models(
    os.getenv("XAI_VISION_MODEL"),
    "grok-4-1-fast",
    "grok-4-1-fast-reasoning",
    "grok-4-1-fast-non-reasoning",
)

def _grok_chat_completion(messages: list, preferred_models: list[str], **kwargs):
    last_error = None
    for model in preferred_models:
        try:
            return grok_client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
        except Exception as e:
            last_error = e
            error_text = str(e)
            if "Model not found" in error_text:
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("No Grok model configured.")

def _inject_lessons(system_prompt: str) -> str:
    """Inject lessons learned from past feedback into the system prompt."""
    try:
        from . import database
        lessons = database.get_active_lessons(limit=3)
        if lessons:
            lessons_text = "\n".join([f"- {l}" for l in lessons])
            injection = f"\n\n[Active Lessons Learned from Past Mistakes]\nNEVER REPEAT THESE VERIFIED HISTORICAL ERRORS:\n{lessons_text}\n"
            return system_prompt + injection
    except Exception:
        pass
    return system_prompt

def analyze_root_cause(claim: str, original_response: str, user_reason: str) -> str:
    """Analyze why a previous response was incorrect and extract a lesson learned."""
    gemini_client = get_next_client()
    if not gemini_client:
        return ""
        
    reflection_prompt = f"""
    You are a Fact-Check Quality Auditor. 
    You previously analyzed this claim: "{claim}"
    Your response was: "{original_response}"
    The Human Admin marked this as HELPFUL: False. 
    Admin's Reason for failure: "{user_reason}"
    
    TASK: Focus on the TRUTH. Analyze exactly why your logic or evidence gathering failed. 
    Was the source fake? Did you miss the context? Did you hallucinate?
    Return a concise 1-sentence "Lesson Learned" for your future self to avoid this exact error.
    Format your response as a direct instruction starting with "Always..." or "Never...".
    """
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=reflection_prompt,
            config=types.GenerateContentConfig(
                temperature=0.0
            )
        )
        lesson = response.text.strip()
        lesson = lesson.replace("**", "").replace('"', '').replace("'", "")
        return lesson
    except Exception as e:
        print(f"Error in analyze_root_cause: {e}")
        return ""

def analyze_text_claim(text: str, search_context: str = "") -> dict:
    """Analyze a text claim using Gemini."""
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_year_th = datetime.now().year + 543
    
    prompt = f"""
    Current Date: {current_date} (พ.ศ. {current_year_th})
    
    FORENSIC INSTRUCTION: Analyze the text and search context below. Prioritize finding the **ORIGIN** and checking **SOCIAL CONSENSUS**.
    
    We are trying to verify the following text or claim:
    "{text}"
    
    Context:
    ---
    {search_context if search_context else "No initial search context provided."}
    ---
    
    CRITICAL INSTRUCTION: You MUST use your Google Search tool to find the ORIGIN of this claim. Do not hallucinate. 
    State clearly if it originated from a specific social media user, news site, or official source.
    Cite what you searched for and what you found.
    
    TONE: Conversational Thai (ภาษาชาวบ้าน เข้าใจง่าย).
    CONCISENESS: Max 3-4 bullet points. No raw URLs in analysis. **Bold** key names.
    
    Provide a JSON response:
    - score: 0-100.
    - analysis: Text in Thai.
    - claims_extracted: List of Thai claims.
    - suspicious_words: List of Thai emotional words.
    - ai_signals: Keywords indicating AI generation (e.g., 'Deepfake', 'AI-made', 'Stable Diffusion').
    - ai_confidence_score: 0-100 likelihood of AI-generated content.
    - sources: Array of [{{"title": "...", "snippet": "...", "link": "..."}}]. ONLY return exact URLs from search_context. No hallucinations.
    
    Return ONLY valid JSON.
    """
    prompt = _inject_lessons(prompt)

    for attempt in range(4):
        gemini_client = get_next_client()
        if not gemini_client:
            return {"score": 50, "analysis": "Gemini API Keys not configured.", "sources": []}
            
        try:
            try:
                response = gemini_client.models.generate_content(
                    model='gemini-3-flash-preview',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                        tools=[{"google_search": {}}]
                    ),
                )
            except Exception as inner_e:
                if "429" in str(inner_e) or "RESOURCE_EXHAUSTED" in str(inner_e):
                    response = gemini_client.models.generate_content(
                        model='gemini-3.1-flash-lite-preview',
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
            
            valid_sources = []
            for s in parsed.get("sources", []):
                if not isinstance(s, dict): continue
                link = s.get("link", "")
                if isinstance(link, str) and verify_url(link):
                    valid_sources.append(s)
                elif "title" in s and "snippet" in s:
                    s["link"] = ""
                    valid_sources.append(s)
            parsed["sources"] = valid_sources
            return parsed
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < 3: continue
                clean_error = "ระบบขัดข้องชั่วคราว: Rate Limit ขออภัยครับ 🙏"
            else:
                clean_error = f"Error during Gemini analysis: {error_msg}"
                
            if attempt == 3 or ("429" not in error_msg and "RESOURCE_EXHAUSTED" not in error_msg):
                return {"score": 50, "analysis": clean_error, "sources": [], "skip_to_grok": True}
    return {"score": 50, "analysis": "Unknown error.", "sources": [], "skip_to_grok": True}

def analyze_with_grok(text: str, search_context: str = "") -> dict:
    """Analyze a text prompt using Grok 4.1 Fast Reasoning."""
    if not grok_client:
        return {"score": 50, "analysis": "XAI_API_KEY not configured.", "sources": []}
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_year_th = datetime.now().year + 543
    prompt = f"""
    Current Date: {current_date} (พ.ศ. {current_year_th})
    Analyze this text using a **Digital Forensics** approach:
    "{text}"
    
    Context:
    ---
    {search_context if search_context else "No search context provided."}
    ---
    
    ROLE: Professional X (Twitter) & Digital Forensic Investigator.
    STRENGTH: You have unique access to real-time data on X (Twitter) that other models might lack.
    MISSION: Final fallback analysis. Your goal is to find the "hidden truth" often found in social discussions or X links when standard web search fails.
    
    ANALYZE: 
    1. Investigate X (Twitter) links/discussions specifically.
    2. Identify the first person/account to post the claim (Provenance).
    3. Check for "social consensus" or "community notes" on X.
    4. Detect AI-generation signals (AIGC).
    
    INSTRUCTIONS:
    - If others failed to find evidence, dig deep into X/Social data.
    - STRICT ANCHORING: Discard irrelevant context.
    - TONE: Professional but investigative Thai. Focus on "**เจาะลึกที่มาบน X**".
    - CONCISENESS: Max 3-4 bullet points. No URLs in main text.
    - SOURCES: Include real links to X posts or relevant sources.
    
    Respond in JSON: {{ "score": 0, "analysis": "...", "claims_extracted": [], "suspicious_words": [], "sources": [] }}
    """
    try:
        system_msg = "You are a highly accurate fact-checker AI with live web search. Respond with valid JSON only."
        system_msg = _inject_lessons(system_msg)
        response = _grok_chat_completion(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            preferred_models=TEXT_GROK_MODELS,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        parsed = json.loads(response.choices[0].message.content)
        valid_sources = []
        for s in parsed.get("sources", []):
            if not isinstance(s, dict): continue
            link = s.get("link", "")
            if isinstance(link, str) and verify_url(link):
                valid_sources.append(s)
            elif "title" in s and "snippet" in s:
                s["link"] = ""
                valid_sources.append(s)
        parsed["sources"] = valid_sources
        return parsed
    except Exception as e:
        return {"score": 50, "analysis": f"API Error: {str(e)}", "sources": []}

def analyze_image_fact_check(image_bytes_list: list, hint_context: str = "", log_filename: str = "") -> dict:
    '''Send images directly to Grok Vision + web search.'''
    if not grok_client:
        return {"score": 50, "analysis": "XAI_API_KEY not configured.", "sources": []}
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
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        except Exception: pass
    prompt_text = (
        f"Current Date: {current_date} (พ.ศ. {current_year_th})\n\n"
        "You are a fact-checker with VISION and LIVE WEB SEARCH. Verify the image claim.\n"
        f"Context: {hint_context}\n"
        "1. Read Headline Text Overlay. 2. Verify with sources. 3. Evaluate Origin.\n"
        "4. Tone: Simple Thai. 5. JSON Format only."
    )
    content.append({"type": "text", "text": prompt_text})
    try:
        response = _grok_chat_completion(
            messages=[
                {"role": "system", "content": _inject_lessons("Accurate fact-checker with vision. Focal point is the HEADLINE text.")},
                {"role": "user", "content": content}
            ],
            preferred_models=VISION_GROK_MODELS,
            temperature=0.1,
            response_format={"type": "json_object"},
            max_tokens=2000
        )
        response_text = response.choices[0].message.content.strip()
        if response_text.startswith("```json"): response_text = response_text[7:]
        if response_text.endswith("```"): response_text = response_text[:-3]
        parsed = json.loads(response_text.strip())
        valid = []
        for s in parsed.get("sources", []):
            if not isinstance(s, dict): continue
            link = s.get("link", "")
            if isinstance(link, str) and verify_url(link): valid.append(s)
            elif "title" in s and "snippet" in s: s["link"] = ""; valid.append(s)
        parsed["sources"] = valid
        return parsed
    except Exception as e:
        return {"score": 50, "analysis": f"Vision Error: {e}", "sources": []}
