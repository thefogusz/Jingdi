from PIL import Image
from collections import deque
import os
import math

def color_dist(c1, c2):
    return math.sqrt((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2 + (c1[2]-c2[2])**2)

def remove_bg_smart(img_path, tolerance=30):
    img = Image.open(img_path).convert('RGBA')
    w, h = img.size
    px = img.load()
    visited = [[False]*h for _ in range(w)]
    queue = deque()
    
    # Sample background color from top-left corner
    bg_color = px[0,0][:3]
    
    # Edge seed
    for x in range(w):
        queue.append((x, 0))
        queue.append((x, h-1))
        visited[x][0] = True
        visited[x][h-1] = True
    for y in range(h):
        queue.append((0, y))
        queue.append((w-1, y))
        visited[0][y] = True
        visited[w-1][y] = True

    while queue:
        x, y = queue.popleft()
        r, g, b, a = px[x,y]
        
        # If it matches the background color within tolerance
        if color_dist((r,g,b), bg_color) <= tolerance:
            px[x,y] = (r,g,b,0) # Make transparent
            
            # ONLY add neighbors to queue if we successfully matched background here
            # This ensures we don't bleed past the cat's outline
            for nx,ny in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
                if 0<=nx<w and 0<=ny<h and not visited[nx][ny]:
                    visited[nx][ny] = True
                    queue.append((nx,ny))

    img.save(img_path, 'PNG')
    print(f'Done true flood fill: {os.path.basename(img_path)}')

pub = r'D:\GUS\frontend\public'

# First recopy the pristine generated images
import shutil
brain_dir = r'C:\Users\Gus\.gemini\antigravity\brain\35be0c6c-0c65-4de1-b832-1e258f9e2eca'
shutil.copy(os.path.join(brain_dir, 'cat_reading_news_1772983513084.png'), os.path.join(pub, 'cat-reading.png'))
shutil.copy(os.path.join(brain_dir, 'cat_on_phone_1772983532669.png'), os.path.join(pub, 'cat-phone.png'))
# For cat thinking, wait, the original generated image had a fake checkerboard background!
# The fake checkerboard is NOT a solid color, so flood fill won't work on it natively if tolerance is low.
# But let's copy them all anyway.
shutil.copy(os.path.join(brain_dir, 'cat_thinking_1772983550090.png'), os.path.join(pub, 'cat-thinking.png'))

print("Restored pristine images, starting flood fill...")
# Process them
for fname in ['cat-reading.png', 'cat-phone.png']:
    remove_bg_smart(os.path.join(pub, fname), tolerance=40)
    
# for cat-thinking, it has that checkerboard. We need a higher tolerance or just use rembg.
remove_bg_smart(os.path.join(pub, 'cat-thinking.png'), tolerance=60)

print('All done!')
