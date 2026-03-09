import os
from PIL import Image

d = r'D:\GUS\fix'
w, h = 640*2, 640*2
res = Image.new('RGB', (w, h), (255, 0, 255))
positions = [(0,0), (640,0), (0,640), (640,640)]

from PIL import ImageDraw
for i in range(4):
    p = os.path.join(d, f'true_{i}.png')
    if os.path.exists(p):
        img = Image.open(p).convert('RGBA')
        res.paste(img, positions[i], img)
        draw = ImageDraw.Draw(res)
        draw.text((positions[i][0] + 50, positions[i][1] + 50), f"true_{i}.png", fill="black")

res.save(r'C:\Users\Gus\.gemini\antigravity\brain\35be0c6c-0c65-4de1-b832-1e258f9e2eca\debug_trues.png')
print("Saved debug_trues.png")
