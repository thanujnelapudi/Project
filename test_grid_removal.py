import cv2
import numpy as np
import os
import glob
from PIL import Image

def remove_grid_from_image(image_path, out_path):
    # Load grayscale
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None: return
    
    # Binarize
    thresh = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 5)

    # Detect horizontal lines (long thin lines)
    # The minimum length of a line to identify it as a grid line
    min_line_length = 40
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (min_line_length, 1))
    horizontal_mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)

    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, min_line_length))
    vertical_mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=1)

    # Combine grid masks
    grid_mask = cv2.bitwise_or(horizontal_mask, vertical_mask)

    # Dilate grid slightly to catch fuzzy edges around the lines
    grid_mask = cv2.dilate(grid_mask, np.ones((3,3), np.uint8), iterations=1)

    # Subtract grid from text
    cleaned_binary = cv2.subtract(thresh, grid_mask)
    
    # Morphology close to bridge the gaps in characters torn by the grid lines
    bridge_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned_binary = cv2.morphologyEx(cleaned_binary, cv2.MORPH_CLOSE, bridge_kernel)

    # Invert back to black on white
    result = cv2.bitwise_not(cleaned_binary)
    cv2.imwrite(out_path, result)
    print(f"Processed {image_path} -> {out_path}")

# Run on debug crops
os.makedirs('grid_test', exist_ok=True)
crops = glob.glob('ocr/crop_debug/*.png')
for c in crops:
    name = os.path.basename(c)
    remove_grid_from_image(c, f'grid_test/{name}')
