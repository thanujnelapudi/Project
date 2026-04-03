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

    # Resize if too large
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

    # Check if image is dark (mean brightness below 127)
    mean_brightness = np.mean(gray)
    print(f"Image brightness: {mean_brightness:.1f}")

    if mean_brightness < 127:
        # Image is dark - invert it first
        gray = cv2.bitwise_not(gray)
        print("Image inverted due to dark background")

    # Increase contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    contrast = clahe.apply(gray)

    # Simple threshold
    _, thresh = cv2.threshold(
        contrast, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # Check if result is mostly black (inverted result)
    white_pixels = np.sum(thresh == 255)
    total_pixels = thresh.shape[0] * thresh.shape[1]
    white_ratio = white_pixels / total_pixels

    print(f"White pixel ratio: {white_ratio:.2f}")

    # If less than 40% white pixels, image is inverted
    if white_ratio < 0.40:
        thresh = cv2.bitwise_not(thresh)
        print("Threshold result inverted to fix black background")

    base, ext = os.path.splitext(image_path)
    processed_path = base + "_processed" + ext
    cv2.imwrite(processed_path, thresh)
    return processed_path

if __name__ == "__main__":
    print("Preprocessor ready.")
