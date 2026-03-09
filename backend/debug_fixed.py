import os
from PIL import Image
import numpy as np

fix_dir = r'D:\GUS\fix\out'
pub_dir = r'D:\GUS\frontend\public'
brain = r'C:\Users\Gus\.gemini\antigravity\brain\35be0c6c-0c65-4de1-b832-1e258f9e2eca'

# To identify them, let's just make a composite
def analyze_and_composite(bg_color, out_name):
    w = 640 * 2
    h = 640 * 2
    res = Image.new('RGBA', (w, h), bg_color)
    positions = [(0,0), (640,0), (0,640), (640,640)]
    
    print(f"\n--- Analysis for bg {bg_color} ---")
    
    names = ['fixed_0.png', 'fixed_1.png', 'fixed_2.png', 'fixed_3.png']
    for i, name in enumerate(names):
        p = os.path.join(fix_dir, name)
        if not os.path.exists(p): continue
        
        img = Image.open(p).convert('RGBA')
        res.paste(img, positions[i], img)
        
        arr = np.array(img)
        transparent = arr[:,:,3] < 100
        opaque_white = (arr[:,:,0] > 240) & (arr[:,:,1] > 240) & (arr[:,:,2] > 240) & (arr[:,:,3] > 200)
        
        # Draw the index number on the image so we know which is which!
        from PIL import ImageDraw, ImageFont
        d = ImageDraw.Draw(res)
        d.text((positions[i][0] + 50, positions[i][1] + 50), f"fixed_{i}.png", fill="red")
        
    res.save(os.path.join(brain, out_name))
    print(f"Saved {out_name}")

analyze_and_composite((255, 0, 255, 255), 'debug_fixed_magenta.png')
analyze_and_composite((0, 0, 0, 255), 'debug_fixed_black.png')
