import os, numpy as np
from PIL import Image

f = r'D:\GUS\fix\true_0.png'
arr = np.array(Image.open(f).convert('RGBA'))
w, h = Image.open(f).size
print(f'Size: {w}x{h}')

# See if there are brown pixels anywhere
# Brown is around R=100-150, G=50-100, B=20-50
mask = (arr[:,:,0] > 70) & (arr[:,:,0] < 180) & (arr[:,:,1] > 40) & (arr[:,:,1] < 120) & (arr[:,:,2] < 80)
print(f'Brownish pixels in true_0.png: {np.sum(mask)}')
print(f'Total transparent pixels: {np.sum(arr[:,:,3] < 100)}')
