import os
from PIL import Image
import numpy as np
from collections import deque

pub_dir = r'D:\GUS\frontend\public'

def safe_remove_bg(in_name, out_name, extra_seeds=[], bg_threshold=(235, 235, 235)):
    in_path = os.path.join(pub_dir, in_name)
    out_path = os.path.join(pub_dir, out_name)
    
    img = Image.open(in_path).convert('RGBA')
    arr = np.array(img)
    w, h = img.size
    
    visited = np.zeros((h, w), dtype=bool)
    # Background must be lighter than thresh
    mask = (arr[:,:,0] > bg_threshold[0]) & (arr[:,:,1] > bg_threshold[1]) & (arr[:,:,2] > bg_threshold[2])
    
    q = deque()
    
    # Edges
    for x in range(w):
        if mask[0, x]: q.append((x, 0))
        if mask[h-1, x]: q.append((x, h-1))
    for y in range(h):
        if mask[y, 0]: q.append((0, y))
        if mask[y, w-1]: q.append((w-1, y))
        
    for seed in extra_seeds:
        if mask[seed[1], seed[0]]:
            q.append(seed)
            
    for x, y in q:
        visited[y, x] = True
        
    while q:
        x, y = q.popleft()
        for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < w and 0 <= ny < h:
                if not visited[ny, nx] and mask[ny, nx]:
                    visited[ny, nx] = True
                    q.append((nx, ny))
                    
    arr[visited] = [0, 0, 0, 0]
    
    Image.fromarray(arr).save(out_path)
    print(f"Perfectly processed {out_name}")

# Poses
safe_remove_bg('cat-phone-orig.png', 'cat-phone.png', [(368, 115), (460, 176), (385, 216), (333, 490), (393, 506), (465, 390)])
safe_remove_bg('cat-reading-orig.png', 'cat-reading.png', [(396, 212), (327, 463), (347, 446), (370, 136), (453, 485), (511, 291)])

# cat-detective-candidate2.png is the shocked/idle original
safe_remove_bg('cat-detective-candidate2.png', 'detective-cat.png', [])

# Since thinking is an odd one with the checkerboard background, wait, is cat-thinking-orig.png checkerboarded? 
# The mean was 215.3, so it might have the fake checkerboard. If so, a simple >235 threshold might miss grey squares.
# Let's check with a script.
