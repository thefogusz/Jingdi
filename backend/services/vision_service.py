import os
import io
import json
import base64
from datetime import datetime
from PIL import Image
from google import genai
from google.genai import types

from .gemini_pool import get_next_client

VISION_PROMPT_TEMPLATE = (
    "Current Date: {current_date} (พ.ศ. {current_year_th})\n\n"
    "{context}\n\n"
    "CRITICAL INSTRUCTION: If the image appears to be a graphic quote, an infographic, a meme format, "
    "or text added onto a background for aesthetic/sharing purposes, DO NOT lower the score just because "
    "it is 'manipulated', 'photoshopped', or 'AI-generated'. People use these tools to create news graphics. "
    "Your primary goal is to extract the text claim accurately so it can be fact-checked. Only flag manipulation "
    "if it is intended to deceive (e.g., deepfaking a person doing something they didn't).\n\n"
    "Return a JSON response with ONLY the following keys:\n"
    "- score: Integer 0 to 100 for credibility.\n"
    "- analysis: Explanation of the findings in Thai.\n"
    "- visual_indicators: A list of visual signals in Thai.\n"
    "- extracted_text: Any readable text in the image (both Thai and English).\n"
    "- english_keywords: Array of 4-8 specific ENGLISH search terms for finding the ORIGINAL NEWS STORY.\n"
    "CRITICAL — THAI NEWS GRAPHIC PATTERN: Thai news graphics often use a dramatic BACKGROUND PHOTO "
    "(e.g., squid on fishing boat) as clickbait, while the ACTUAL STORY is described in the TEXT OVERLAY and a smaller inset image. "
    "ALWAYS read ALL text in the image first. The HEADLINE TEXT is the real story. The background photo may be completely unrelated.\n"
    "PRIORITY for keywords: "
    "(1) HEADLINE TEXT: Translate Thai headline text to English. Use its MEANING, not what the background photo shows. "
    "Example: big squid-fishing photo + text 'พบหมึกมหึมาในถิ่นที่อยู่ธรรมชาติครั้งแรก' "
    "→ keywords MUST be ['colossal squid', 'first natural habitat observation', 'Mesonychoteuthis hamiltoni'] "
    "NOT ['giant squid', 'Thai fishermen', 'fishing boat']. "
    "KEY TERM: หมึกมหึมา = colossal squid = Mesonychoteuthis hamiltoni (different from ปลาหมึกยักษ์ = Architeuthis dux).\n"
    "(2) Add: organization, location, event type from text or small inset image.\n"
    "- is_global_story: true if the HEADLINE describes an international/science/foreign story (even if text is in Thai).\n"
)


def _grok_vision_fallback(image_buffers: list, prompt: str) -> dict:
    """Use Grok as a fallback when all Gemini vision keys are exhausted."""
    try:
        from openai import OpenAI
        xai_api_key = os.getenv("XAI_API_KEY")
        if not xai_api_key:
            return None
        
        grok_client = OpenAI(api_key=xai_api_key, base_url="https://api.x.ai/v1")
        
        content = [{"type": "text", "text": prompt}]
        for buf in image_buffers:
            img = Image.open(io.BytesIO(buf))
            out = io.BytesIO()
            img.convert("RGB").save(out, format="JPEG", quality=85)
            b64 = base64.b64encode(out.getvalue()).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
            })
        
        response = grok_client.chat.completions.create(
            model="grok-4-1-fast-non-reasoning",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a highly accurate fake news detection AI that can analyze images. "
                        "Respond with valid JSON only in this format: "
                        '{"score": 50, "analysis": "...", "visual_indicators": [], "extracted_text": "", '
                        '"english_keywords": ["keyword1", "keyword2"], "is_global_story": true}'
                        "\n\nCRITICAL — THAI NEWS GRAPHIC PATTERN:"
                        "\nThai news graphics use a dramatic BACKGROUND PHOTO as clickbait. The ACTUAL STORY is in the TEXT OVERLAY."
                        "\nALWAYS fact-check the HEADLINE TEXT, not the background photo."
                        "\n\nPRIORITY for english_keywords:"
                        "\n1. Read ALL text in the image. Translate Thai headline to English. Use its MEANING."
                        "   Example: big squid-fishing photo + text 'พบหมึกมหึมาในถิ่นที่อยู่ธรรมชาติครั้งแรก'"
                        "   → keywords: ['colossal squid', 'first natural habitat observation', 'Mesonychoteuthis hamiltoni']"
                        "   NOT ['giant squid', 'Thai fishermen', 'fishing boat']"
                        "\n   KEY TERM: หมึกมหึมา = colossal squid = Mesonychoteuthis hamiltoni"
                        "\n   (DIFFERENT from ปลาหมึกยักษ์ = Architeuthis dux)"
                        "\n2. Add visual details from text or small inset image (not background photo)."
                        "\nis_global_story: true if headline describes international/science story (even if text is Thai)."
                    )
                },
                {"role": "user", "content": content}
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
            max_tokens=1500
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Grok vision fallback error: {e}")
        return None


def analyze_images_with_vision(image_buffers: list, is_screenshot: bool = False) -> dict:
    """Use Gemini Vision to analyze images for fake news signals, with Grok fallback."""
    client = get_next_client()
    if not client:
        return {
            "score": 50,
            "analysis": "Gemini API Keys not configured. Vision analysis disabled.",
            "visual_indicators": []
        }
    
    images = [Image.open(io.BytesIO(buffer)) for buffer in image_buffers]
    
    if is_screenshot:
        context = (
            "These are screenshots of social media posts or news articles. "
            "Extract the text, identify the platform if possible, check if it looks manipulated or features "
            "a reliable source layout, and evaluate the credibility of the claim being made across the images."
        )
    else:
        context = (
            "These are images. Determine if these images look AI-generated, manipulated, or out of context. "
            "Read any text present and evaluate if the images are conveying misinformation."
        )

    current_date = datetime.now().strftime("%Y-%m-%d")
    current_year_th = datetime.now().year + 543
    
    prompt = VISION_PROMPT_TEMPLATE.format(
        current_date=current_date,
        current_year_th=current_year_th,
        context=context
    )

    all_rate_limited = True

    for attempt in range(4):
        client = get_next_client()
        if not client:
            break
            
        try:
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[prompt, *images],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
            except Exception as inner_e:
                if "429" in str(inner_e) or "RESOURCE_EXHAUSTED" in str(inner_e):
                    response = client.models.generate_content(
                        model='gemini-2.5-flash-lite',
                        contents=[prompt, *images],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1,
                        ),
                    )
                else:
                    raise inner_e
                    
            return json.loads(response.text)
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < 3:
                    import time
                    time.sleep(1)
                    continue
                # All 4 keys exhausted
                break
            else:
                all_rate_limited = False
                return {
                    "score": 50,
                    "analysis": f"Error during vision analysis: {error_msg}",
                    "visual_indicators": [],
                    "extracted_text": ""
                }

    # Gemini exhausted — try Grok vision fallback
    print("All Gemini keys rate-limited for vision. Trying Grok fallback...")
    grok_result = _grok_vision_fallback(image_buffers, prompt)
    if grok_result:
        return grok_result

    return {
        "score": 50,
        "analysis": "ระบบวิเคราะห์รูปภาพกำลังยุ่งมากครับ (โควต้า AI Vision เต็มชั่วคราว) รบกวนลองอีกครั้งใน 5 นาทีครับ 🙏",
        "visual_indicators": [],
        "extracted_text": ""
    }
