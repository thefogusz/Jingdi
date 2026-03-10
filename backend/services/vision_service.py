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
    "CRITICAL ARCHITECTURAL KNOWLEDGE: The 'King Power Mahanakhon' building in Bangkok has a unique 'pixelated' or 'fragmented' design that looks like parts are missing or crumbling. This is INTENTIONAL ARCHITECTURE. Do NOT flag this building as a sign of image manipulation, destruction, or glitches.\n\n"
    "CRITICAL INSTRUCTION: Analyze the image objectively. Extract the text accurately. Identify colors, logos, and layouts. "
    "Only flag manipulation if it is clearly intended to deceive (e.g., deepfaking a person's face).\n\n"
    "Return a JSON response with ONLY the following keys:\n"
    "- score: Integer 0 to 100 for credibility.\n"
    "- analysis: Objective explanation of findings in Thai.\n"
    "- visual_indicators: A list of visual signals in Thai (e.g., logos, building names).\n"
    "- extracted_text: Readable text in the image (both Thai and English). BE EXTREMELY THOROUGH. Read every small character correctly.\n"
    "- text_clarity: 'high', 'low', or 'none'. Set to 'low' if text is blurry, handwritten, or partially obscured.\n"
    "- english_keywords: Array of 4-8 specific ENGLISH search terms. INCLUDE SOURCES (e.g. 'efinanceThai TV') and ACTIONS (e.g. 'withdraw normally') found in text. Focus on the EXACT news post.\n"
    "- is_global_story: true if the headline describes an international/scientific/foreign story.\n"
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
                        "You are a highly accurate fact-checker. Respond with valid JSON only in this format: "
                        '{"score": 50, "analysis": "...", "visual_indicators": [], "extracted_text": "", '
                        '"english_keywords": ["keyword1", "keyword2"], "is_global_story": true}'
                        "\n\nCRITICAL ARCHITECTURAL KNOWLEDGE: "
                        "\nThe 'King Power Mahanakhon' building in Bangkok has a unique 'pixelated' fragmented design. This is STYLISTIC ARCHITECTURE, not destruction."
                        "\n\nINSTRUCTION:"
                        "\n1. Read ALL text. State the core claim. Translate Thai headline to English search terms."
                        "\n2. Be objective. Use neutral language."
                        "\nis_global_story: true if headline describes international/science/foreign story."
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
