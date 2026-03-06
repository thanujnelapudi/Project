import pytesseract
import easyocr
import re
import sys
import os
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TESSERACT_PATH
from ocr.preprocessor import preprocess_image

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Initialize EasyOCR once when the file loads
reader = easyocr.Reader(['en'], gpu=False)

def extract_text(image_path):
    processed_path = preprocess_image(image_path)
    if processed_path is None:
        return {}

    # --- Tesseract OCR ---
    img = Image.open(processed_path)
    tesseract_text = pytesseract.image_to_string(
        img, config="--oem 3 --psm 6"
    )

    # --- EasyOCR ---
    easy_results = reader.readtext(processed_path, detail=0)
    easy_text = "\n".join(easy_results)

    # --- Pick better result ---
    tesseract_score = len([
        w for w in tesseract_text.split() if len(w) > 2
    ])
    easy_score = len([
        w for w in easy_text.split() if len(w) > 2
    ])

    if easy_score >= tesseract_score:
        best_text = easy_text
        print("Using EasyOCR result")
    else:
        best_text = tesseract_text
        print("Using Tesseract result")

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
    lines = [l.strip() for l in lines if l.strip()]

    for i, line in enumerate(lines):
        line_lower = line.lower().strip()

        # Name detection
        if any(k in line_lower for k in ["name"]):
            value = extract_value(line, "name")
            # If value is just punctuation or empty look at next line
            if not value or len(value) <= 2:
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Make sure next line is not another label
                    if not any(k in next_line.lower() for k in
                               ["address","phone","pin","remark"]):
                        value = next_line
            if value and len(value) > 2:
                fields["name"] = value

        # Address detection
        elif any(k in line_lower for k in ["address", "addr", "addx", "addy"]):
            value = extract_value(line, "address|addr|addx|addy")
            if not value and i + 1 < len(lines):
                value = lines[i + 1].strip()
            if value:
                fields["address"] = value

        # Phone detection - expanded keywords to catch OCR misreads
        elif any(k in line_lower for k in
                 ["phone","mobile","contact","ph","phon",
                  "phyle","phne","fone","mabile","mobi"]):
            # Try to extract digits directly
            match = re.search(r'\d{7,}', line)
            if match:
                fields["phone"] = match.group()
            else:
                value = extract_value(
                    line,
                    "phone|mobile|contact|ph|phyle|phne|fone"
                )
                if value:
                    fields["phone"] = value

        # Pincode detection
        elif any(k in line_lower for k in
                 ["pincode","pin code","postal","pin","diacode"]):
            match = re.search(r'\b\d{5,6}\b', line)
            if match:
                fields["pincode"] = match.group()

        # Remarks detection
        elif any(k in line_lower for k in
                 ["remark","remarks","note","reraudy","remar"]):
            value = extract_value(
                line,
                "remark|remarks|note|reraudy|remar"
            )
            if not value and i + 1 < len(lines):
                value = lines[i + 1].strip()
            if value:
                fields["remarks"] = value

    # Fallback phone - search entire text for 10 digit number
    if not fields["phone"]:
        match = re.search(r'\b[6-9]\d{9}\b', text)
        if match:
            fields["phone"] = match.group()
        else:
            # Catch any 7+ digit number
            match = re.search(r'\d{7,}', text)
            if match:
                fields["phone"] = match.group()

    # Fallback pincode
    if not fields["pincode"]:
        match = re.search(r'\b\d{6}\b', text)
        if match:
            fields["pincode"] = match.group()

    # Fallback name - use first non-label line
    if not fields["name"]:
        for line in lines:
            if not any(k in line.lower() for k in
                       ["name","address","phone","pin",
                        "remark","post","india"]):
                if len(line) > 2:
                    fields["name"] = line
                    break

    return fields

def extract_value(line, keyword_pattern):
    pattern = rf'(?i)(?:{keyword_pattern})\s*[:\-\.]?\s*(.+)'
    match = re.search(pattern, line)
    if match:
        return match.group(1).strip()
    return ""

if __name__ == "__main__":
    print("Extractor with EasyOCR ready.")