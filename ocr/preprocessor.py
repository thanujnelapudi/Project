import cv2
import numpy as np
import pytesseract
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TESSERACT_PATH

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def preprocess_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print("Error: Could not read image.")
        return None

    # Resize only if image is very large
    max_width = 1800
    height, width = img.shape[:2]
    if width > max_width:
        scale = max_width / width
        img = cv2.resize(
            img,
            (int(width * scale), int(height * scale)),
            interpolation=cv2.INTER_AREA
        )

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Simple threshold - fast and effective for printed forms
    _, thresh = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    base, ext = os.path.splitext(image_path)
    processed_path = base + "_processed" + ext
    cv2.imwrite(processed_path, thresh)
    return processed_path

if __name__ == "__main__":
    print("Preprocessor ready.")