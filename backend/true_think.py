import os
from PIL import Image
import numpy as np
from rembg import remove, new_session
from scipy.ndimage import binary_fill_holes

brain = r'C:\Users\Gus\.gemini\antigravity\brain\35be0c6c-0c65-4de1-b832-1e258f9e2eca'
pub = r'D:\GUS\frontend\public'

def process_thinking_true():
    in_path = os.path.join(brain, 'cat_thinking_1772983550090.png')
    out_path = os.path.join(pub, 'cat-thinking.png')
    
    img = Image.open(in_path).convert('RGBA')
    session = new_session()
    result = remove(img, session=session)
    
    arr = np.array(result)
    alpha = arr[:, :, 3]
    
    binary_mask = alpha > 10 
    filled_mask = binary_fill_holes(binary_mask)
    
    orig_arr = np.array(img)
    final_arr = np.zeros_like(orig_arr)
    # Restore original pristine RGB colors since rembg might have slightly modified edge colors
    final_arr[:, :, :3] = orig_arr[:, :, :3]
    
    final_alpha = alpha.copy()
    final_alpha[filled_mask & (alpha < 255)] = 255
    final_arr[:, :, 3] = final_alpha
    
    Image.fromarray(final_arr, 'RGBA').save(out_path)
    print("Perfectly processed cat-thinking.png")

if __name__ == "__main__":
    process_thinking_true()
