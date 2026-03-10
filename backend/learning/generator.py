import sys
import os
import datetime
import json

# Add parent and grand-parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))
sys.path.append(os.path.dirname(os.path.dirname(current_dir)))

import database
from learning.analyzer import extract_learning_data
from services.llm_service import analyze_with_grok, get_next_client
from google.genai import types as genai_types

INSIGHTS_FILE = os.path.join(current_dir, "insights.md")

def generate_insights():
    print("Extracting data for learning...")
    raw_data = extract_learning_data(limit=20)
    
    if not any(raw_data.values()):
        print("No new data to learn from.")
        return

    prompt = f"""
    You are the "Autonomous Brain" of the Jingdi Fact-Checking System.
    Your task is to analyze recent failures, errors, and negative user feedback to improve yourself.
    
    RECENT DATA FOR ANALYSIS:
    {json.dumps(raw_data, indent=2, ensure_ascii=False)}
    
    INSTRUCTIONS:
    1. Identify PATTERNS: Are there specific types of news (e.g., crypto scams, political rumors) where we fail?
    2. Identify SOURCE GAPS: Are we missing specific high-quality news sources that could have solved these cases?
    3. Technical Audit: Diagnose why errors occurred (API timeouts, OCR failures, etc.)
    4. Actionable Advice: Provide 2-3 specific "Lessons Learned" for the next time an AI assistant (like me) works on this codebase.
    
    FORMAT: Write a concise Markdown report starting with "## Session: [Date]". Use bullet points.
    Language: Thai (Conversational but professional).
    """

    print("Generating insights using AI...")
    insights = ""
    try:
        # Try Grok
        res = analyze_with_grok(prompt, search_context="System Internal Logs Analysis")
        if isinstance(res, dict):
            insights = res.get("analysis", str(res))
        else:
            insights = str(res)
    except Exception as e:
        print(f"Grok failed: {e}. Falling back to Gemini...")
        client = get_next_client()
        if client:
            resp = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            insights = resp.text
        else:
            insights = "Error: Unable to call LLM for insight generation."

    # Append to file
    with open(INSIGHTS_FILE, "a", encoding="utf-8") as f:
        header = f"\n\n# Autonomous Learning Session: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f.write(header + insights)
    
    print(f"Learning session complete. Insights saved to {INSIGHTS_FILE}")

if __name__ == "__main__":
    generate_insights()
