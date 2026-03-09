import os
import numpy as np
from PIL import Image
from scipy.ndimage import label, center_of_mass, binary_dilation

pub_dir = r'D:\GUS\frontend\public'

# Let's map the images correctly first by examining the ones we copied
# Wait, why not just process `cat-phone-orig.png`, `cat-reading-orig.png`, etc?
# Because the user said the poses were wrong. This means the artifacts I copied:
# `cat_on_phone_1772983532669.png` maybe WAS NOT the phone cat!
# Let's check the artifacts again.

# Instead of naming them blindly, let's process all 4 image_X.png files that the user JUST uploaded (which are guaranteed to be the right poses).
# The user uploaded image_0 to image_3. Let's process them and save them as fix_0 to fix_3.
# Then I will figure out which is which to map them to the frontend.

def process_smart_bg(in_path, out_path, bg_color=(235, 235, 235)):
    img = Image.open(in_path).convert('RGBA')
    arr = np.array(img)
    w, h = img.size
    
    # 1. Identify pure white regions (could be background, eyes, phone, paper)
    white_mask = (arr[:,:,0] > bg_color[0]) & (arr[:,:,1] > bg_color[1]) & (arr[:,:,2] > bg_color[2]) & (arr[:,:,3] > 200)
    
    # 2. Identify pure black pixels (pupils, outlines)
    black_mask = (arr[:,:,0] < 50) & (arr[:,:,1] < 50) & (arr[:,:,2] < 50) & (arr[:,:,3] > 200)
    
    # 3. Dilate the black mask slightly so it touches the white of the eyes
    dilated_black = binary_dilation(black_mask, iterations=3)
    
    # 4. Label the connected white regions
    labeled_white, num_white = label(white_mask)
    
    # We will build a final mask of what to REMOVE (turn transparent)
    to_remove = np.zeros((h, w), dtype=bool)
    
    from collections import deque
    # First, do standard flood fill from outside edges to guarantee we remove the main background
    q = deque()
    bg_visited = np.zeros((h, w), dtype=bool)
    for x in range(w):
        if white_mask[0, x]: q.append((x, 0))
        if white_mask[h-1, x]: q.append((x, h-1))
    for y in range(h):
        if white_mask[y, 0]: q.append((0, y))
        if white_mask[y, w-1]: q.append((w-1, y))
        
    for x, y in q:
        bg_visited[y, x] = True
        
    while q:
        x, y = q.popleft()
        for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < w and 0 <= ny < h:
                if not bg_visited[ny, nx] and white_mask[ny, nx]:
                    bg_visited[ny, nx] = True
                    q.append((nx, ny))
                    
    to_remove |= bg_visited
    
    # Now for trapped white gaps. Check every white region.
    for i in range(1, num_white + 1):
        region_mask = (labeled_white == i)
        area = np.sum(region_mask)
        
        # If the region is part of the main outside background, it's already removed
        if np.any(region_mask & bg_visited):
            continue
            
        # Small noise
        if area < 50:
            continue
            
        # Is this region touching a black pupil or dark line?
        touches_black = np.any(region_mask & dilated_black)
        
        # Eyes are usually large (100-3000 pixels) and touch black.
        # Phone screen and paper might not touch black, or they might.
        # If it DOES NOT touch black, it's a trapped gap! (Like the gap between chin and phone)
        # Wait, the phone screen might not touch black either. Let's rely on area.
        # Gaps are usually < 1000 pixels. Phone screen/paper is usually > 3000 pixels.
        if touches_black:
            # It's an eye or something bordered by heavy black. KEEP IT.
            pass
        else:
            if area < 2000: # Trapped background gap!
                print(f"  Removing trapped gap: area={area}")
                to_remove |= region_mask
                
    # Apply the to_remove mask
    arr[to_remove] = [0, 0, 0, 0]
    Image.fromarray(arr).save(out_path)
    print(f"Processed nicely into {os.path.basename(out_path)}")


os.makedirs(r'D:\GUS\fix\out', exist_ok=True)
for i in range(4):
    in_p = rf'D:\GUS\fix\image_{i}.png'
    out_p = rf'D:\GUS\fix\out\fixed_{i}.png'
    if os.path.exists(in_p):
        print(f"\nProcessing image_{i}.png...")
        process_smart_bg(in_p, out_p)
        
print("\nDone all 4 images.")
