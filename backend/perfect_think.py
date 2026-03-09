import os
from PIL import Image
import numpy as np
from rembg import remove, new_session
from scipy.ndimage import binary_fill_holes

def process_thinking_cat():
    pub = r'D:\GUS\frontend\public'
    in_path = r'D:\GUS\fix\true_3.png'
    out_path = os.path.join(pub, 'cat-thinking.png')
    
    img = Image.open(in_path).convert('RGBA')
    
    session = new_session()
    result = remove(img, session=session)
    
    arr = np.array(result)
    alpha = arr[:, :, 3]
    
    # Fill any disconnected holes in the alpha mask (this completely seals the eyes and any props so nothing inside the cat becomes transparent)
    binary_mask = alpha > 10 
    filled_mask = binary_fill_holes(binary_mask)
    
    orig_arr = np.array(img)
    final_arr = np.zeros_like(orig_arr)
    # Restore original pristine RGB colors
    final_arr[:, :, :3] = orig_arr[:, :, :3]
    
    final_alpha = alpha.copy()
    # Where fill_holes added opacity, set alpha to 255.
    final_alpha[filled_mask & (alpha < 255)] = 255
    final_arr[:, :, 3] = final_alpha
    
    Image.fromarray(final_arr, 'RGBA').save(out_path)
    print("Perfectly processed " + out_path)

if __name__ == "__main__":
    process_thinking_cat()
