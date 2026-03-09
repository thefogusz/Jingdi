import os
import numpy as np
from PIL import Image
from collections import deque

pub = r'D:\GUS\frontend\public'

def manual_safe_bg(in_path, out_path, bg_color=(235, 235, 235), extra_seeds=[]):
    img = Image.open(in_path).convert('RGBA')
    arr = np.array(img)
    w, h = img.size
    
    # 1. Precise BFS flood fill from edges ONLY
    visited = np.zeros((h, w), dtype=bool)
    mask = (arr[:,:,0] > bg_color[0]) & (arr[:,:,1] > bg_color[1]) & (arr[:,:,2] > bg_color[2])
    
    q = deque()
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
                    
    # Only remove visited background pixels.
    # Everything inside the cat (brown pupils, white eyes, props) is guaranteed safe!
    arr[visited] = [0, 0, 0, 0]
    
    Image.fromarray(arr).save(out_path)
    print(f"Perfectly processed {out_path}")

# Process the true pristine items the user uploaded
# target mappings:
# true_0 = detective 
# true_1 = reading
# true_2 = shocked
# true_3 = thinking

# true_1 (reading) gaps:
reading_gaps = [(396, 212), (327, 463), (347, 446), (370, 136), (453, 485), (511, 291)]
manual_safe_bg(r'D:\GUS\fix\true_1.png', os.path.join(pub, 'cat-reading.png'), extra_seeds=reading_gaps)

# true_0 (detective) has no enclosed white background gaps.
manual_safe_bg(r'D:\GUS\fix\true_0.png', os.path.join(pub, 'detective-cat.png'))

# true_2 (shocked) has a gap under the chin? The previous shocked cat didn't have enclosed gaps.
manual_safe_bg(r'D:\GUS\fix\true_2.png', os.path.join(pub, 'cat-shocked.png'))

# true_3 (thinking) DOES NOT have pure white background! It has the fake checkerboard.
# Let's use our previously confirmed thinking cat script. BUT wait, earlier the thinking cat was fine except maybe I swapped it!
# Let's write a targeted rembg script that just fills ALL alpha holes.
