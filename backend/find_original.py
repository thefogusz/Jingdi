import os, glob, shutil
from PIL import Image
import numpy as np

d = r'C:\Users\Gus\.gemini\antigravity\brain\35be0c6c-0c65-4de1-b832-1e258f9e2eca'
media = glob.glob(os.path.join(d, 'media__*.png'))
media.sort(key=os.path.getmtime)
latest_original = None

for m in media:
    try:
        img = Image.open(m).convert('RGBA')
        if img.size == (640, 640):
            arr = np.array(img)
            # Center of the cat's hollow eye in the original drawing
            r, g, b, a = arr[279, 428]
            # The pristine transparent PNG had solid white eyes (since it was manually fixed by the user, or it was generated with them)
            # Actually wait, did the ORIGINAL main cat have a solid white background?
            # Yes! The original main cat had a solid background before I removed it!
            # Let's check a pixel that is background. Top left corner (0,0)
            # If the user uploaded a transparent PNG, it has a=0. 
            bg_a = arr[0, 0, 3]
            eye_r, eye_g, eye_b, eye_a = arr[279, 428]
            
            # The background must be transparent OR very white, but the eye MUST be opaque white
            if eye_a > 200 and eye_r > 240 and eye_g > 240 and eye_b > 240:
                print(f"Candidate {os.path.basename(m)}: bg_alpha={bg_a}, eye=({eye_r},{eye_g},{eye_b},{eye_a})")
                latest_original = m
    except Exception as e: pass

print(f'\nFound pristine original: {latest_original}')
if latest_original:
    shutil.copy(latest_original, r'D:\GUS\frontend\public\detective-cat.png')
    print('Restored pristine detective-cat.png to public dir')
