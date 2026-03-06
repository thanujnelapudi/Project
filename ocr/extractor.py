import pytesseract
import re
import sys
import os
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TESSERACT_PATH
from ocr.preprocessor import preprocess_image

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def extract_text(image_path):
    processed_path = preprocess_image(image_path)
    if processed_path is None:
        return {}
    img = Image.open(processed_path)

    # Use multiple Tesseract configurations for best result
    configs = [
        "--oem 3 --psm 6",
        "--oem 3 --psm 4",
        "--oem 1 --psm 6",
    ]

    best_text = ""
    best_score = 0

    for config in configs:
        text = pytesseract.image_to_string(img, config=config)
        score = len([w for w in text.split() if len(w) > 2])
        if score > best_score:
            best_score = score
            best_text = text

    print("Best OCR Output:")
    print(best_text)
    print("---")
    fields = parse_fields(best_text)
    return fields

def parse_fields(text):
    fields = {
        "name":    "",
        "address": "",
        "phone":   "",
        "pincode": "",
        "remarks": ""
    }

    lines = text.splitlines()

    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        if not line_lower:
            continue

        if any(k in line_lower for k in ["name"]):
            value = extract_value(line, "name")
            if not value and i + 1 < len(lines):
                value = lines[i + 1].strip()
            if value:
                fields["name"] = value

        elif any(k in line_lower for k in ["address", "addr"]):
            value = extract_value(line, "address|addr")
            if not value and i + 1 < len(lines):
                value = lines[i + 1].strip()
            if value:
                fields["address"] = value

        elif any(k in line_lower for k in ["phone", "mobile", "contact", "ph"]):
            value = extract_value(line, "phone|mobile|contact|ph")
            if not value:
                match = re.search(r'\d{7,}', line)
                if match:
                    value = match.group()
            if value:
                fields["phone"] = value

        elif any(k in line_lower for k in ["pincode", "pin code", "postal code", "pin"]):
            match = re.search(r'\b\d{5,6}\b', line)
            if match:
                fields["pincode"] = match.group()

        elif any(k in line_lower for k in ["remark", "note", "remarks"]):
            value = extract_value(line, "remark|remarks|note")
            if not value and i + 1 < len(lines):
                value = lines[i + 1].strip()
            if value:
                fields["remarks"] = value

    # Fallback: find phone number anywhere in text
    if not fields["phone"]:
        match = re.search(r'\b[6-9]\d{9}\b', text)
        if match:
            fields["phone"] = match.group()

    # Fallback: find pincode anywhere in text
    if not fields["pincode"]:
        match = re.search(r'\b\d{6}\b', text)
        if match:
            fields["pincode"] = match.group()

    return fields

def extract_value(line, keyword_pattern):
    pattern = rf'(?i)(?:{keyword_pattern})\s*[:\-\.]?\s*(.+)'
    match = re.search(pattern, line)
    if match:
        return match.group(1).strip()
    return ""

if __name__ == "__main__":
    print("Extractor ready.")