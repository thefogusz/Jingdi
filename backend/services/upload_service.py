"""
Upload Service
==============
Provides temporary public hosting for images so they can be analyzed
by APIs that require a public URL (like SerpApi's Google Lens).

We use Catbox.moe which provides fast, free, and anonymous uploads 
without requiring an API key. 
"""

import requests

def upload_to_catbox(image_bytes: bytes, filename: str = "image.jpg") -> str:
    """
    Uploads image bytes to Catbox.moe and returns the public URL.
    Returns empty string if upload fails.
    """
    try:
        url = "https://catbox.moe/user/api.php"
        data = {"reqtype": "fileupload"}
        files = {"fileToUpload": (filename, image_bytes)}
        
        # Note: Catbox can sometimes be slow or block certain regions, 
        # so we set a reasonable timeout.
        response = requests.post(url, data=data, files=files, timeout=15)
        
        if response.status_code == 200 and response.text.startswith("http"):
            return response.text.strip()
        else:
            print(f"[Upload Service] Failed to upload: {response.status_code} - {response.text[:100]}")
            return ""
            
    except Exception as e:
        print(f"[Upload Service] Error uploading to Catbox: {e}")
        return ""
