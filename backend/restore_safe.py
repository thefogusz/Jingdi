import os
from PIL import Image, ImageDraw

brain_dir = r'C:\Users\Gus\.gemini\antigravity\brain\35be0c6c-0c65-4de1-b832-1e258f9e2eca'
pub_dir = r'D:\GUS\frontend\public'

def safe_flood_fill(img_path, seeds, out_path, bg_color):
    try:
        img = Image.open(img_path).convert('RGBA')
        ImageDraw.floodfill(img, xy=(0,0), value=(0,0,0,0), thresh=40)
        ImageDraw.floodfill(img, xy=(img.width-1, 0), value=(0,0,0,0), thresh=40)
        ImageDraw.floodfill(img, xy=(0, img.height-1), value=(0,0,0,0), thresh=40)
        ImageDraw.floodfill(img, xy=(img.width-1, img.height-1), value=(0,0,0,0), thresh=40)
        
        for seed in seeds:
            ImageDraw.floodfill(img, xy=seed, value=(0,0,0,0), thresh=40)
            
        img.save(out_path)
        print(f"Processed {out_path}")
    except Exception as e:
        print(f"Failed {img_path}: {e}")

# 1. Phone Cat (cat-phone.png)
# Gap between chin and phone is roughly at x=368, y=115 in standard layout? Wait, in PIL xy=(x, y). 
# Let's add multiple likely gap seeds. The previous script reported:
# center=(y=115, x=368) -> xy=(368, 115)
# center=(y=176, x=460) -> xy=(460, 176)
safe_flood_fill(
    os.path.join(brain_dir, 'cat_on_phone_1772983532669.png'), 
    [(368, 115), (460, 176), (288, 77)], # seeds for gaps
    os.path.join(pub_dir, 'cat-phone.png'),
    (254, 251, 252)
)

# 2. Reading Cat (cat-reading.png)
# Gaps at: y=136, x=370 -> xy=(370, 136)
# y=212, x=396 -> xy=(396, 212)
safe_flood_fill(
    os.path.join(brain_dir, 'cat_reading_news_1772983513084.png'), 
    [(370, 136), (396, 212)], 
    os.path.join(pub_dir, 'cat-reading.png'),
    (254, 250, 253)
)

print("Restoration script executed")
