import numpy as np
import os
from PIL import Image

pub = r'D:\GUS\frontend\public'

# Fix detective-cat.png (Eyes only, holes 4 and 5)
img_dc = Image.open(os.path.join(pub, 'detective-cat.png')).convert('RGBA')
arr_dc = np.array(img_dc)
transparent = arr_dc[:,:,3] < 100
from scipy.ndimage import label, center_of_mass
labeled, num_features = label(transparent)
for i in range(1, num_features + 1):
    area = np.sum(labeled == i)
    com = center_of_mass(transparent, labeled, i)
    # Fill eyes based on center coordinates
    # Hole 4: center=(y=279.3, x=428.1)
    # Hole 5: center=(y=286.4, x=317.0)
    if (abs(com[0] - 279) < 10 and abs(com[1] - 428) < 10) or \
       (abs(com[0] - 286) < 10 and abs(com[1] - 317) < 10):
        # Set to white opaque
        arr_dc[labeled == i] = [255, 255, 255, 255]

Image.fromarray(arr_dc).save(os.path.join(pub, 'detective-cat.png'))
print('Fixed detective-cat.png eyes')

# Now for cat-phone and cat-reading, let's just find the white/near-white gap and flood fill it to transparent
# We know the gap is a specific isolated clump of whitish pixels that didn't get removed because it was trapped.
# Wait, if it's trapped between chin and phone, maybe I can just do a connected component analysis on the *original* white background, and remove anything that is pure white (r>240, g>240, b>240).
# The phone screen might be slightly blue or grey, not pure white. The newspaper might be off-white.
# The background was (254, 250, 253) -> very pure white.
def remove_trapped_bg(img_name):
    img = Image.open(os.path.join(pub, img_name)).convert('RGBA')
    arr = np.array(img)
    # Find all very bright white exactly matching the old bg
    # The old bg was approx R>245, G>240, B>245
    pure_white = (arr[:,:,0] > 240) & (arr[:,:,1] > 240) & (arr[:,:,2] > 240) & (arr[:,:,3] > 100)
    
    labeled, num = label(pure_white)
    for i in range(1, num + 1):
        com = center_of_mass(pure_white, labeled, i)
        area = np.sum(labeled == i)
        # Avoid eyes (y ~ 270-290, area ~ 2000-3000)
        if area > 100 and com[0] > 310: 
            # This must be the trapped gap (y > 310, below eyes)
            # The phone screen is NOT pure white (it usually has blueish glow in generated images)
            # But just to be safe, filter the phone screen if it's too big
            if "phone" in img_name and area > 4000:
                continue # Probably the phone screen
            if "reading" in img_name and area > 4000:
                continue # Probably the newspaper pages
                
            print(f"Removing trapped white gap in {img_name}: area={area}, center={com}")
            arr[labeled == i] = [0, 0, 0, 0]
            
    Image.fromarray(arr).save(os.path.join(pub, img_name))

remove_trapped_bg('cat-phone.png')
remove_trapped_bg('cat-reading.png')
print('Finished removing gaps')
