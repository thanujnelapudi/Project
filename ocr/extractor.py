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
reader = easyocr.Reader(['en'], gpu=False)

def extract_text(image_path):
    processed_path = preprocess_image(image_path)
    if processed_path is None:
        return {}

    img = Image.open(processed_path)
    tesseract_text = pytesseract.image_to_string(
        img, config="--oem 3 --psm 6"
    )
    easy_results = reader.readtext(processed_path, detail=0)
    easy_text = "\n".join(easy_results)

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

    return parse_fields(best_text)

def clean_pincode(raw):
    raw = raw.replace('o','0').replace('O','0')
    raw = raw.replace('l','1').replace('I','1')
    raw = raw.replace('S','5').replace('s','5')
    raw = raw.replace('C','0').replace('c','0')
    raw = raw.replace('B','8')
    digits = re.sub(r'\D', '', raw)
    digits = digits.lstrip('0')
    return digits

def match_label(line):
    """
    Returns the field name if the line starts with
    a known label, otherwise returns None.
    Strict prefix matching to avoid false positives.
    """
    line_stripped = line.strip()
    line_lower = line_stripped.lower()

    name_patterns = [
        r'^name\s*[:\-\.]',
        r'^aame\s*[:\-\.]',
        r'^nane\s*[:\-\.]',
        r'^mame\s*[:\-\.]',
    ]
    address_patterns = [
        r'^address\s*[:\-\.]',
        r'^addx\s*[:\-\.]',
        r'^addr\s*[:\-\.]',
        r'^adress\s*[:\-\.]',
    ]
    phone_patterns = [
        r'^phone\s*[:\-\.]',
        r'^phon\s*[:\-\.]',
        r'^phyle\s*[:\-\.]',
        r'^mobile\s*[:\-\.]',
        r'^contact\s*[:\-\.]',
        r'^ph\s*[:\-\.]',
    ]
    pincode_patterns = [
        r'^pincode\s*[:\-\.]',
        r'^pin code\s*[:\-\.]',
        r'^pincope\s*[:\-\.]',
        r'^pincooe\s*[:\-\.]',
        r'^diacode\s*[:\-\.]',
        r'^pin\s*[:\-\.]',
    ]
    remarks_patterns = [
        r'^remarks\s*[:\-\.]',
        r'^remark\s*[:\-\.]',
        r'^reraudy\s*[:\-\.]',
        r'^remarhs\s*[:\-\.]',
        r'^note\s*[:\-\.]',
    ]

    for pattern in name_patterns:
        if re.match(pattern, line_lower):
            return "name"
    for pattern in address_patterns:
        if re.match(pattern, line_lower):
            return "address"
    for pattern in phone_patterns:
        if re.match(pattern, line_lower):
            return "phone"
    for pattern in pincode_patterns:
        if re.match(pattern, line_lower):
            return "pincode"
    for pattern in remarks_patterns:
        if re.match(pattern, line_lower):
            return "remarks"

    return None

def get_value_from_line(line):
    """Extract everything after the first colon, dash or dot."""
    match = re.search(r'[:\-\.]\s*(.+)', line)
    if match:
        return match.group(1).strip().rstrip('.,;')
    return ""

def parse_fields(text):
    fields = {
        "name":    "",
        "address": "",
        "phone":   "",
        "pincode": "",
        "remarks": ""
    }

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]
        field = match_label(line)

        if field == "name":
            value = get_value_from_line(line)
            if not value or len(value) <= 1:
                if i + 1 < len(lines):
                    next_field = match_label(lines[i+1])
                    if not next_field:
                        value = lines[i+1]
                        i += 1
            if value:
                fields["name"] = value

        elif field == "address":
            value = get_value_from_line(line)
            parts = [value] if value else []
            # Collect continuation lines
            j = i + 1
            while j < len(lines):
                if match_label(lines[j]):
                    break
                if len(lines[j]) > 1:
                    parts.append(lines[j])
                j += 1
            i = j - 1
            if parts:
                fields["address"] = " ".join(parts)

        elif field == "phone":
            value = get_value_from_line(line)
            if not value:
                if i + 1 < len(lines):
                    if not match_label(lines[i+1]):
                        value = lines[i+1]
                        i += 1
            match = re.search(r'\d{7,}', value)
            if match:
                fields["phone"] = match.group()
            elif value:
                fields["phone"] = value

        elif field == "pincode":
            value = get_value_from_line(line)
            if not value or len(value.strip()) <= 1:
                if i + 1 < len(lines):
                    if not match_label(lines[i+1]):
                        value = lines[i+1]
                        i += 1
            if value:
                cleaned = clean_pincode(value)
                if len(cleaned) >= 5:
                    fields["pincode"] = cleaned[:6]

        elif field == "remarks":
            value = get_value_from_line(line)
            parts = [value] if value else []
            j = i + 1
            while j < len(lines):
                if match_label(lines[j]):
                    break
                if len(lines[j]) > 1:
                    parts.append(lines[j])
                j += 1
            i = j - 1
            if parts:
                fields["remarks"] = " ".join(parts)

        i += 1

    # Fallback phone
    if not fields["phone"]:
        match = re.search(r'\b[6-9]\d{9}\b', text)
        if match:
            fields["phone"] = match.group()

    # Fallback pincode
    if not fields["pincode"]:
        match = re.search(r'\b\d{6}\b', text)
        if match:
            fields["pincode"] = match.group()

    return fields

if __name__ == "__main__":
    print("Extractor ready.")