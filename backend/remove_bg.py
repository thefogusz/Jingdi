import os
from PIL import Image
import numpy as np
from rembg import remove, new_session
from scipy.ndimage import binary_fill_holes

def process_image(input_path, output_path, session):
    print(f"Processing {os.path.basename(input_path)}...")
    img = Image.open(input_path).convert('RGBA')
    
    # 1. Rembg removes background, but also eats the white of the eyes (they become transparent)
    result = remove(img, session=session)
    
    # 2. Extract the alpha mask as a numpy array
    arr = np.array(result)
    alpha = arr[:, :, 3]
    
    # 3. Fill holes in the alpha mask (the eyes are holes completely surrounded by the opaque cat)
    # True for opaque (alpha > 0), False for transparent
    binary_mask = alpha > 10 
    filled_mask = binary_fill_holes(binary_mask)
    
    # 4. Wherever the filled mask is True, make it fully opaque (255) in the original RGB
    # Note: We take the ORIGINAL image's RGB so that the eyes regain their original bright white color,
    # and we only apply our new filled alpha mask.
    orig_arr = np.array(img)
    
    # Create the final array: original RGB, with our new filled alpha channel
    final_arr = np.zeros_like(orig_arr)
    final_arr[:, :, :3] = orig_arr[:, :, :3]
    
    # Where filled_mask is true, set alpha to 255. Else set to 0. (Rembg actually gives partial transparency at edges,
    # so we can use the original rembg alpha, but set filled holes to 255).
    final_alpha = alpha.copy()
    final_alpha[filled_mask & (alpha < 255)] = 255
    final_arr[:, :, 3] = final_alpha
    
    # Save the result
    final_img = Image.fromarray(final_arr, 'RGBA')
    final_img.save(output_path, 'PNG')

if __name__ == "__main__":
    session = new_session()
    pub = r'D:\GUS\frontend\public'
    brain = r'C:\Users\Gus\.gemini\antigravity\brain\35be0c6c-0c65-4de1-b832-1e258f9e2eca'
    
    files = [
        ('cat_reading_news_1772983513084.png', 'cat-reading.png'),
        ('cat_on_phone_1772983532669.png', 'cat-phone.png'),
        ('cat_thinking_1772983550090.png', 'cat-thinking.png'),
    ]
    
    for in_name, out_name in files:
        in_path = os.path.join(brain, in_name)
        out_path = os.path.join(pub, out_name)
        process_image(in_path, out_path, session)

    print("All images processed successfully!")
