import os
import numpy as np
from PIL import Image
from collections import deque

brain = r'C:\Users\Gus\.gemini\antigravity\brain\35be0c6c-0c65-4de1-b832-1e258f9e2eca'
pub = r'D:\GUS\frontend\public'

originals = {
    'detective-cat.png': 'orange_detective_cat_1772919237701.png',
    'cat-reading.png': 'cat_reading_news_1772983513084.png',
    'cat-shocked.png': 'cat_shocked_1772923629094.png'
}

def manual_safe_bg(orig_name, out_name, bg_color=(235, 235, 235), extra_seeds=[]):
    in_path = os.path.join(brain, orig_name)
    out_path = os.path.join(pub, out_name)
    
    img = Image.open(in_path).convert('RGBA')
    arr = np.array(img)
    w, h = img.size
    
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
                    
    arr[visited] = [0, 0, 0, 0]
    Image.fromarray(arr).save(out_path)
    print(f"Perfectly processed {out_path}")

# reading gaps
reading_gaps = [(396, 212), (327, 463), (347, 446), (370, 136), (453, 485), (511, 291)]
manual_safe_bg(originals['cat-reading.png'], 'cat-reading.png', extra_seeds=reading_gaps)

# detective and shocked have no enclosed gaps we know of, just flood-fill the outside!
manual_safe_bg(originals['detective-cat.png'], 'detective-cat.png', extra_seeds=[])
manual_safe_bg(originals['cat-shocked.png'], 'cat-shocked.png', extra_seeds=[])

print("Completed safe background removal for reading, detective, and shocked cats.")

# Next is the thinking cat
