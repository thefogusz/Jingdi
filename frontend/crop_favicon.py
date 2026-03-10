from PIL import Image
import os

def crop_favicon():
    input_path = r"d:\Work\Jingdi\frontend\public\detective-cat.png"
    output_path = r"d:\Work\Jingdi\frontend\src\app\icon.png"
    
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found")
        return

    img = Image.open(input_path).convert("RGBA")
    
    # Simple strategy: find the head
    # The image has the cat body and head. The head is at the top.
    # Let's find the bounding box of the non-transparent pixels
    bbox = img.getbbox()
    if not bbox:
        print("Error: Image is empty")
        return
    
    # Bbox is (left, top, right, bottom)
    # Detective cat head is roughly the top 60% of the active area
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    
    # Crop just the head area
    # Looking at the mascot, the head is round and at the top.
    # Let's try to crop a square centered horizontally in the bbox, 
    # starting from the top.
    
    side = int(w * 1.1) # Make it slightly wider to be safe
    head_bbox = (
        bbox[0] - int(w * 0.05),
        bbox[1] - int(h * 0.05),
        bbox[2] + int(w * 0.05),
        bbox[1] + int(h * 0.75) # Take top 75% of height for head+hat
    )
    
    head_img = img.crop(head_bbox)
    
    # Make it a square
    hw, hh = head_img.size
    new_side = max(hw, hh)
    square_img = Image.new("RGBA", (new_side, new_side), (0,0,0,0))
    offset = ((new_side - hw) // 2, (new_side - hh) // 2)
    square_img.paste(head_img, offset)
    
    # Resize to standard icon size 512x512 for quality (Next.js will handle display)
    final_img = square_img.resize((512, 512), Image.Resampling.LANCZOS)
    
    # Save as icon.png in src/app (Next.js default icon path)
    final_img.save(output_path)
    print(f"Favicon saved to {output_path}")

if __name__ == "__main__":
    crop_favicon()
