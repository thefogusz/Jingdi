import os
from PIL import Image
import numpy as np

pub = r'D:\GUS\frontend\public'
brain = r'C:\Users\Gus\.gemini\antigravity\brain\35be0c6c-0c65-4de1-b832-1e258f9e2eca'

names = [
    'detective-cat.png',
    'cat-reading.png',
    'cat-phone.png',
    'cat-thinking.png'
]

def analyze_and_composite(names, bg_color, out_name):
    w = 640 * 2
    h = 640 * 2
    res = Image.new('RGBA', (w, h), bg_color)
    
    positions = [(0,0), (640,0), (0,640), (640,640)]
    
    print(f"\n--- Analysis for bg {bg_color} ---")
    for i, name in enumerate(names):
        p = os.path.join(pub, name)
        if not os.path.exists(p): continue
        
        img = Image.open(p).convert('RGBA')
        res.paste(img, positions[i], img)
        
        arr = np.array(img)
        transparent = arr[:,:,3] < 100
        opaque_white = (arr[:,:,0] > 240) & (arr[:,:,1] > 240) & (arr[:,:,2] > 240) & (arr[:,:,3] > 200)
        opaque_black = (arr[:,:,0] < 50) & (arr[:,:,1] < 50) & (arr[:,:,2] < 50) & (arr[:,:,3] > 200)
        
        print(f"{name}: trans={np.sum(transparent)}, op_white={np.sum(opaque_white)}, op_black={np.sum(opaque_black)}")
        
        # Check eyes specifically (y=210-290, x=270-450)
        eye_region = arr[210:300, 270:450]
        eye_trans = np.sum(eye_region[:,:,3] < 100)
        print(f"  {name} eye region transparent pixels: {eye_trans}")
        
    res.save(os.path.join(brain, out_name))
    print(f"Saved {out_name}")

analyze_and_composite(names, (255, 0, 255, 255), 'debug_magenta.png')
analyze_and_composite(names, (0, 0, 0, 255), 'debug_black.png')
