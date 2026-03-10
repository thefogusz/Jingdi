from PIL import Image
import os

def crop_mascot_head():
    img_path = "d:/Work/Jingdi/frontend/public/detective-cat.png"
    output_path = "d:/Work/Jingdi/frontend/src/app/icon.png"
    
    if not os.path.exists(img_path):
        print(f"Source image not found: {img_path}")
        return

    img = Image.open(img_path).convert("RGBA")
    
    # Get the bounding box of the non-transparent area
    bbox = img.getbbox()
    if not bbox:
        print("Empty image")
        return
        
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    
    # Let's focus TIGHTER on the head and hat.
    # The hat is at the very top. The head ends around middle.
    # Tighter crop: center horizontally, take from top of hat to just below the chin.
    
    # Adjust bbox to focus on head only (top ~55% of the cat)
    head_h = int(h * 0.55)
    
    # Center horizontally
    center_x = (bbox[0] + bbox[2]) // 2
    crop_size = max(w, head_h) # Make it square
    
    left = center_x - crop_size // 2
    top = bbox[1] - int(h * 0.02) # Include top of hat
    right = center_x + crop_size // 2
    bottom = top + crop_size
    
    # Ensure we stay within original bounds for left/right/top/bottom if possible
    # but for a favicon, a bit of padding is okay if we scale it.
    
    img_cropped = img.crop((left, top, right, bottom))
    
    # Resize to standard high-res icon size
    img_cropped = img_cropped.resize((512, 512), Image.Resampling.LANCZOS)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img_cropped.save(output_path, "PNG")
    print(f"Created high-visibility favicon at: {output_path}")

if __name__ == "__main__":
    crop_mascot_head()
