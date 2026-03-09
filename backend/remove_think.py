import os
from PIL import Image
import numpy as np
from rembg import remove, new_session
from scipy.ndimage import binary_fill_holes

def process_thinking_cat():
    pub = r'D:\GUS\frontend\public'
    in_path = os.path.join(pub, 'cat-thinking-orig.png')
    out_path = os.path.join(pub, 'cat-thinking.png')
    
    print(f"Processing {os.path.basename(in_path)}...")
    img = Image.open(in_path).convert('RGBA')
    
    session = new_session()
    result = remove(img, session=session)
    
    arr = np.array(result)
    alpha = arr[:, :, 3]
    
    # Fill holes in the alpha mask (the eyes)
    binary_mask = alpha > 10 
    filled_mask = binary_fill_holes(binary_mask)
    
    orig_arr = np.array(img)
    
    final_arr = np.zeros_like(orig_arr)
    final_arr[:, :, :3] = orig_arr[:, :, :3]
    
    final_alpha = alpha.copy()
    final_alpha[filled_mask & (alpha < 255)] = 255
    final_arr[:, :, 3] = final_alpha
    
    final_img = Image.fromarray(final_arr, 'RGBA')
    final_img.save(out_path, 'PNG')
    print("Thinking cat perfectly processed!")

if __name__ == "__main__":
    process_thinking_cat()
