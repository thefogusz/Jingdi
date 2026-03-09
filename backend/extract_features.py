import os, numpy as np
from PIL import Image

for i in range(6):
    p = rf'D:\GUS\fix\unique_{i}.png'
    if not os.path.exists(p): continue
    
    arr = np.array(Image.open(p).convert('RGBA'))
    bg_mask = (arr[:,:,0] > 240) & (arr[:,:,1] > 240) & (arr[:,:,2] > 240)
    fg_arr = arr[~bg_mask]
    
    news = np.sum((fg_arr[:,0]>180) & (fg_arr[:,1]>180) & (fg_arr[:,2]>180))
    blue = np.sum(fg_arr[:,2] > fg_arr[:,0].astype(int) + 30)
    brown = np.sum((fg_arr[:,0] > 70) & (fg_arr[:,0] < 180) & (fg_arr[:,1] > 40) & (fg_arr[:,1] < 120) & (fg_arr[:,2] < 80))
    dark = np.sum((fg_arr[:,0] < 50) & (fg_arr[:,1] < 50) & (fg_arr[:,2] < 50))
    white_pupil = np.sum((fg_arr[:,0]>240) & (fg_arr[:,1]>240) & (fg_arr[:,2]>240) & (fg_arr[:,3]>240))
    
    print(f'unique_{i}.png: bg_size={np.sum(bg_mask)}, news: {news}, blue: {blue}, brown: {brown}, dark: {dark}, white_pupil: {white_pupil}')
