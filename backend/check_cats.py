import os
import numpy as np
from PIL import Image

pub = r'D:\GUS\frontend\public'
files = ['cat-phone-orig.png', 'cat-reading-orig.png', 'cat-thinking-orig.png', 'cat-detective-candidate1.png', 'cat-detective-candidate2.png']

for f in files:
    try:
        p = os.path.join(pub, f)
        if not os.path.exists(p):
            print(f"File not found: {p}")
            continue
        img = Image.open(p).convert('RGBA')
        arr = np.array(img)
        print(f'{f}: size={img.size}, mean={arr.mean():.1f}, non-transparent={np.sum(arr[:,:,3] > 10)}')
    except Exception as e:
        print(f'Error on {f}: {e}')
print("Done checking")
