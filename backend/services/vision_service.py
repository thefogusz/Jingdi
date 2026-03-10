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
    "CRITICAL INSTRUCTION: Your primary task is to identify evidence that helps determine the **TRUTH** or **FALSEHOOD** of the claim. "
    "Identify colors, logos, layouts, and text. "
    "Check for AI-generated artifacts (AIGC) as a key piece of forensic evidence. If an image is AI-generated, it is a strong signal of potential misinformation, but your analysis must focus on whether the visual evidence supports or contradicts the core claim.\n\n"
    "Return a JSON response with ONLY the following keys:\n"
    "- score: Integer 0 to 100 for credibility (where 100 is factually confirmed and 0 is debunked).\n"
    "- analysis: Objective explanation of findings in Thai. Prioritize explaining if the image is consistent with reality or a fabrication.\n"
    "- visual_indicators: A list of visual signals in Thai (e.g., logos, building names).\n"
    "- extracted_text: Readable text in the image (both Thai and English).\n"
    "- text_clarity: 'high', 'low', or 'none'.\n"
    "- ai_generated_signals: A list of potential AI-generated artifacts (e.g., 'distorted hands', 'AI watermark'). Use these as clues for deception.\n"
    "- ai_confidence_score: Integer 0 to 100 (100 = Definitive AI). This is a forensic clue, not the final answer.\n"
    "- origin_clues: A list of clues that might point to the absolute original source (e.g., social media handles @username, specific news logos, timestamps in the image, or unique UI elements of a platform like Line, TikTok, or Facebook).\n"
    "- english_keywords: Array of 4-8 specific ENGLISH search terms. "
    "Focus on the EXACT core claim and any organizations or news outlets mentioned in the image.\n"
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
                        '"ai_generated_signals": [], "ai_confidence_score": 0, '
                        '"english_keywords": ["keyword1", "keyword2"], "is_global_story": true}'
                        "\n\nCRITICAL ARCHITECTURAL KNOWLEDGE: "
                        "\nThe 'King Power Mahanakhon' building in Bangkok has a unique 'pixelated' fragmented design. This is STYLISTIC ARCHITECTURE, not destruction."
                        "\n\nINSTRUCTION:"
                        "\n1. Read ALL text. State the core claim. Translate Thai headline to English search terms."
                        "\n2. Identify origin clues (handles @, logos, timestamps, platform UI)."
                        "\n3. Be objective. Use neutral language."
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
                    model='gemini-2.0-flash',
                    contents=[prompt, *images],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
            except Exception as inner_e:
                if "429" in str(inner_e) or "RESOURCE_EXHAUSTED" in str(inner_e):
                    response = client.models.generate_content(
                        model='gemini-1.5-flash',
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
