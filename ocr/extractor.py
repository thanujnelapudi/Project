# =============================================================================
# ocr/extractor.py  —  Multi-Form Edition
#
# Supported form types:
#   bank_kyc          — Indian Bank KYC form
#   postal_speedpost  — India Post Speed Post / Parcel form
#   postal_savings    — Post Office Savings Bank ATM/account form
#   courier           — Courier / Shipment form (Origin-Destination)
#   education         — College / Academy Admission form
#   generic           — Fallback: Name / Address / Phone / Pincode / Remarks
#
# OCR Engine: TrOCR line-by-line (PaddleOCR / Tesseract removed)
# =============================================================================

import os, re, sys
import numpy as np
import pytesseract
from pytesseract import Output
from PIL import Image, ImageOps, ImageChops

os.environ["FLAGS_use_mkldnn"]                      = "0"
os.environ["FLAGS_call_stack_level"]                = "0"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ocr.preprocessor import preprocess_image
import os
debug_dir = os.path.join(os.path.dirname(__file__), 'crop_debug')
os.makedirs(debug_dir, exist_ok=True)

import re

# =============================================================================
# Geographical Helpers (India)
# =============================================================================

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana", 
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", 
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", 
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", 
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]

MAJOR_CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Bengaluru", "Hyderabad", "Ahmedabad", "Chennai", "Kolkata", "Surat", 
    "Pune", "Jaipur", "Lucknow", "Kanpur", "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", 
    "Pimpri", "Chinchwad", "Patna", "Vadodara", "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad", 
    "Meerut", "Rajkot", "Kalyan", "Dombivli", "Vasai", "Virar", "Varanasi", "Srinagar", "Aurangabad", 
    "Dhanbad", "Amritsar", "Navi Mumbai", "Allahabad", "Ranchi", "Howrah", "Coimbatore", "Jabalpur", 
    "Gwalior", "Vijayawada", "Jodhpur", "Madurai", "Raipur", "Kota", "Guwahati", "Chandigarh", "Solapur", 
    "Hubli", "Dharwad", "Bareilly", "Moradabad", "Mysore", "Gurgaon", "Aligarh", "Jalandhar", 
    "Tiruchirappalli", "Bhubaneswar", "Salem", "Warangal", "Guntur", "Thiruvananthapuram", "Bhiwandi", 
    "Saharanpur", "Amravati", "Noida", "Jamshedpur", "Bikaner", "Kochi", "Jamnagar", "Gulbarga", 
    "Agartala", "Ujjain", "Belgaum", "Mangalore", "Tirunelveli", "Malegaon", "Gaya", "Jalgaon", "Udaipur", 
    "Maheshtala"
]

def extract_geography(text):
    """
    Search for known Indian states and cities in the provided text.
    Returns (city, state).
    """
    if not text: return "", ""
    found_city, found_state = "", ""
    lower_text = text.lower()
    for state in INDIAN_STATES:
        if state.lower() in lower_text:
            found_state = state
            break
    for city in MAJOR_CITIES:
        if re.search(r'\b' + re.escape(city) + r'\b', text, re.I):
            found_city = city
            break
    return found_city, found_state

def clean_mobile(raw: str) -> str:
    raw = re.sub(r'^.*[|]', '', raw).strip()
    raw = re.sub(r'^.*ber\s*', '', raw, flags=re.IGNORECASE).strip()
    digits = re.sub(r'\D', '', raw)
    if len(digits) >= 10:
        return digits[-10:]
    return digits

def clean_year(raw: str) -> str:
    def fix(m):
        y = m.group(0)
        if y[0] in ('3','4','5','6','7','8','9'):
            return '20' + y[2:]
        return y
    return re.sub(r'\b[3-9]\d{3}\b', fix, raw)

def clean_name_trailing(raw: str) -> str:
    raw = re.sub(r'\s*[\.\-\|].*$', '', raw).strip()
    raw = re.sub(r'\s+[A-Z]$', '', raw).strip()
    return raw

def strip_grid_noise(text: str) -> str:
    """Removes trailing character-box digit noise like '1 2 3 ... 11' or '1/2 0, 2 . 3'"""
    if not text: return ""
    text = re.sub(r'(\s*(\d{1,2})[\s\.\,\-\/]+){3,}\d*$', '', text.strip())
    text = re.sub(r'([\s\.\-\/,]+\d{1,2}){2,}\s*$', '', text).strip()
    return text.strip(' ,.-')

def parse_date_from_text(text: str) -> str:
    """Smart DOB extractor. Prefers Tesseract segment 'D / M / YYYY' format."""
    if not text: return ""
    # Method 1: Clean separator pattern (Tesseract reads these perfectly)
    m = re.search(r'(\d{1,2})\s*[/\-\.]\s*(\d{1,2})\s*[/\-\.]\s*(\d{4})', text)
    if m:
        d, mo, y = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
        if 1 <= int(d) <= 31 and 1 <= int(mo) <= 12:
            return f"{d}/{mo}/{y}"
    # Method 2: Extract year, then find valid day + month from remaining groups
    year_m = re.search(r'(19|20)\d{2}', text)
    if year_m:
        year = year_m.group(0)
        pre = text[:year_m.start()]
        nums = re.findall(r'\d+', pre)
        int_nums = [int(n) for n in nums if 1 <= len(n) <= 2]
        valid_months = [n for n in int_nums if 1 <= n <= 12]
        valid_days   = [n for n in int_nums if 1 <= n <= 31]
        if valid_days and valid_months:
            day = valid_days[0]
            month = next((mo for mo in valid_months if mo != day), valid_months[-1])
            return f"{str(day).zfill(2)}/{str(month).zfill(2)}/{year}"
    # Method 3: 8 raw digits -> DD/MM/YYYY
    digits = re.sub(r'\D', '', text)
    if len(digits) == 8:
        d, mo, y = digits[0:2], digits[2:4], digits[4:8]
        if 1 <= int(d) <= 31 and 1 <= int(mo) <= 12:
            return f"{d}/{mo}/{y}"
    return ""


# =============================================================================
# Lazy Loading Helpers — TrOCR & PaddleOCR
# =============================================================================
TROCR_AVAILABLE  = False
PADDLE_AVAILABLE = False
trocr_processor  = None
trocr_model      = None
paddle_ocr       = None
torch            = None 

_engines_initialized = False

def _init_engines():
    global TROCR_AVAILABLE, PADDLE_AVAILABLE, trocr_processor, trocr_model, paddle_ocr, _engines_initialized, torch
    if _engines_initialized:
        return
    
    _engines_initialized = True
    print("\n[OCR] Initializing OCR Engines (this may take a moment on first use)...")

    # 1. TrOCR
    try:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        global torch
        import torch
        print("[OCR] Loading TrOCR model (microsoft/trocr-base-handwritten)...")
        trocr_processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
        trocr_model     = VisionEncoderDecoderModel.from_pretrained(
                              "microsoft/trocr-base-handwritten")
        trocr_model.eval()
        TROCR_AVAILABLE = True
        print("[OCR] TrOCR loaded — PRIMARY engine active.")
    except Exception as e:
        TROCR_AVAILABLE = False
        print(f"[OCR] TrOCR not available: {e}")

    # 2. PaddleOCR
    try:
        from paddleocr import PaddleOCR
        print("[OCR] Loading PaddleOCR mobile models...")
        paddle_ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="PP-OCRv5_mobile_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False
        )
        PADDLE_AVAILABLE = True
        print("[OCR] PaddleOCR loaded — BACKUP engine active.")
    except Exception as e:
        PADDLE_AVAILABLE = False
        print(f"[OCR] PaddleOCR not available: {e}")
    
    print("[OCR] Engine initialization complete.\n")


def trocr_read_line(pil_crop):
    try:
        padded = ImageOps.expand(pil_crop.convert("RGB"), border=6, fill="white")
        pixel_values = trocr_processor(images=padded, return_tensors="pt").pixel_values
        with torch.no_grad():
            ids = trocr_model.generate(
                pixel_values, 
                max_new_tokens=30,
                num_beams=1,
                do_sample=False,
                repetition_penalty=2.5,
                length_penalty=0.5
            )
        return trocr_processor.batch_decode(ids, skip_special_tokens=True)[0].strip()
    except Exception as e:
        print(f"[OCR] TrOCR line error: {e}")
        return ""


def paddle_read_line(pil_crop):
    if not PADDLE_AVAILABLE or paddle_ocr is None:
        print("[OCR] PaddleOCR NOT AVAILABLE for this line scan.")
        return ""
    try:
        import numpy as np
        if pil_crop is None: return ""
        img_np = np.array(pil_crop.convert("RGB"))
        img_bgr = img_np[:, :, ::-1].copy()
        results = paddle_ocr.ocr(img_bgr)
        if not results or not results[0]: return ""
        blocks = results[0]
        blocks.sort(key=lambda x: x[0][0][0])
        texts = []
        for b in blocks:
            text, conf = b[1]
            if conf > 0.1: texts.append(text)
        return " ".join(texts)
    except Exception as e:
        print(f"[OCR] PaddleOCR error: {e}")
        return ""


# =============================================================================
def check_image_entropy(value_crop, field_key):
    crop_gray = value_crop.convert('L')
    crop_array = np.array(crop_gray)
    white_ratio = np.sum(crop_array > 220) / crop_array.size
    if white_ratio > 0.998:
        print(f"[OCR]   [{field_key}] SKIP — crop too white (ratio={white_ratio:.2f})")
        return False
    ink_pixels = np.sum(crop_array < 180)
    if ink_pixels < 20:
        print(f"[OCR]   [{field_key}] SKIP — insufficient ink (ink_px={ink_pixels})")
        return False
    return True

def detect_text_lines(image_path, min_line_height=8, padding=4):
    img      = Image.open(image_path).convert("L")
    img      = ImageOps.autocontrast(img)
    arr      = np.array(img)
    binary   = (arr < 160).astype(np.uint8)
    row_sums = binary.sum(axis=1)
    kernel   = np.ones(3) / 3
    smoothed = np.convolve(row_sums, kernel, mode="same")
    min_dark = max(3, arr.shape[1] * 0.01)

    in_line, start_row, segments = False, 0, []
    for i, val in enumerate(smoothed):
        if not in_line and val >= min_dark:
            in_line = True; start_row = i
        elif in_line and val < min_dark:
            in_line = False
            if (i - start_row) >= min_line_height:
                segments.append((max(0, start_row - padding),
                                  min(arr.shape[0], i + padding)))
    if in_line and (len(smoothed) - start_row) >= min_line_height:
        segments.append((max(0, start_row - padding), arr.shape[0]))
    return img.width, segments

def clean_trocr_line(line):
    if not line: return ""
    line = re.sub(r'^[I\|l\.\*\#\s]+', '', line.strip())
    line = re.sub(r'000\d*', '', line)
    line = re.sub(r'^[\.\,\;\:\-\_\s]+', '', line)
    line = re.sub(r'[\s\_\"\'\.\,\#\*]+$', '', line)
    line = re.sub(r' {2,}', ' ', line)
    return line.strip()

ALPHA_FIELDS   = [
    'first_name', 'middle_name', 'last_name', 'applicant_name', 'mother_name',
    'student_name', 'father_name', 'sender_name', 'receiver_name', 'religion', 'nationality', 'guardian_name'
]
NUMERIC_FIELDS = ['mobile_number', 'phone_number', 'sol_id', 'cif_id', 'date_of_birth', 'sender_pincode', 'receiver_pincode', 'nid_number']
ALNUM_FIELDS   = ['pan_number', 'email', 'address', 'present_address', 'permanent_address', 'course_name', 'blood_group']

def post_filter_trocr(text, field_key):
    if not text: return ""
    if field_key in ALPHA_FIELDS:
        prose_glue = {"the", "and", "with", "from", "being", "should", "that", "this", "which", "into", "their"}
        words = text.lower().split()
        glue_count = sum(1 for w in words if w in prose_glue)
        if glue_count >= 2 or len(words) > 5:
            print(f"[OCR]   [{field_key}] REJECTED TrOCR (Prose Hallucination): '{text}'")
            return ""
        kept = []
        for w in words:
            if w.isdigit(): continue
            if len(w) > 15: continue
            if re.match(r'^[a-z\.\-\']+$', w): kept.append(w.capitalize())
        res = " ".join(kept)
        return res if res else ""
    elif field_key in NUMERIC_FIELDS:
        if field_key in ("mobile_number", "phone_number"):
            digits = re.sub(r'\D', '', text)
            if len(digits) >= 10: return digits[:10]
            return digits if len(digits) > 3 else ""
        elif field_key == "date_of_birth":
            # Extract only digits, slashes, dots, dashes
            clean_dob = re.sub(r'[^\d/.-]', '', text).strip('.- ')
            digits_only = re.sub(r'\D', '', clean_dob)
            if len(digits_only) > 12 or len(digits_only) < 4: return ""
            # Reconstruct as DD/MM/YYYY if we have 7-8 digits
            if len(digits_only) in (7, 8):
                d = digits_only.zfill(8)
                return f"{d[0:2]}/{d[2:4]}/{d[4:8]}"
            return clean_dob
        elif field_key == "sol_id":
            sol_match = re.search(r'\d{3,6}', text)
            sol_num = sol_match.group(0) if sol_match else ""
            date_match = re.search(r'\d{2}/?\d{2}/?\d{4}', text)
            date_str = date_match.group(0) if date_match else ""
            if date_str and sol_num:
                if '/' not in date_str and len(date_str) == 8:
                    date_str = f"{date_str[:2]}/{date_str[2:4]}/{date_str[4:]}"
                return f"SOL: {sol_num}  Date: {date_str}"
            return sol_num
        else:
            digits = re.findall(r'\d+', text)
            all_digits = "".join(digits)
            if len(all_digits) > 15: return ""
            return all_digits if all_digits else ""
    elif field_key in ALNUM_FIELDS:
        if field_key == "email":
            res = "".join([c for c in text if re.match(r'[A-Za-z0-9@\.\_\-\+]', c)])
            if '@' not in res or len(res) > 50: return ""
            return res
        elif field_key == "blood_group":
            # Map 'At' to 'A+', 'Bt' to 'B+', etc.
            text = text.replace('At', 'A+').replace('Bt', 'B+').replace('Ot', 'O+').replace('ABt', 'AB+')
            m = re.search(r'\b(A|B|O|AB)[\s]*[\+\-]\b', text.upper())
            if m: return m.group(0).replace(" ","")
            return ""
        else:
            # For present_address, permanent_address, course_name
            res = "".join([c for c in text if re.match(r'[A-Za-z0-9\s\.\,\-\/]', c)])
            res = res.strip()
            if "address" in field_key:
                # Reject very short results (single-char like 't') to force Tesseract fallback
                if len(res) < 4: return ""
                # Stop at first box-noise: isolated digit(s) with punct after alphabetic text
                m_noise = re.search(r'(?<=[a-zA-Z])\s+\d{1,3}[\s\-\.\/, ]', res)
                if m_noise:
                    res = res[:m_noise.start()].strip(' ,.-')
                # Reject prose hallucinations in addresses
                prose_glue = {"upon", "the", "and", "then", "established", "with", "which",
                              "into", "their", "spanish", "states", "shire", "borough"}
                words = res.lower().split()
                glue_count = sum(1 for w in words if w in prose_glue)
                if glue_count >= 2:
                    clean_words = []
                    for w in res.split():
                        if w.lower() in prose_glue: break
                        clean_words.append(w)
                    res = " ".join(clean_words).strip(' ,.-')
                # Strip leading single-char noise (like 't', 'l')
                res = re.sub(r'^[a-z]\s+', '', res, flags=re.IGNORECASE).strip()
                res = strip_grid_noise(res)
            elif field_key == "course_name":
                # Strip trailing punct/digit noise, then cap at 3 words
                res = re.sub(r'[\s\.\,\-]+[\d\.\,\-\s]{2,}$', '', res).strip()
                words = res.split()
                if len(words) > 3: res = " ".join(words[:3])
                res = strip_grid_noise(res)
            return res
    return text

def check_repetition(text, field_key):
    if not text: return ""
    words = text.split()
    if len(words) >= 4:
        bigrams = [words[i]+" "+words[i+1] for i in range(len(words)-1)]
        if len(bigrams) != len(set(bigrams)):
            print(f"[OCR]   [{field_key}] HALLUCINATION REJECTED (repetition detected)")
            return ""
    return text

# =============================================================================
def find_all_label_spans(line_text, form_type):
    n = re.sub(r'[^a-zA-Z0-9]', ' ', line_text.lower())
    regexes = []
    if form_type == "postal_savings":
        regexes = [
            (r"applicant\s*s?\s*n[a-z]{1,2}e", "applicant_name"),
            (r"mother\s*s?\s*(maiden)?\s*n[a-z]{1,2}e", "mother_name"),
            (r"first\s*n[a-z]{1,2}e", "first_name"),
            (r"middle\s*n[a-z]{1,2}e", "middle_name"),
            (r"last\s*n[a-z]{1,2}e", "last_name"),
            (r"mobile\s*num", "mobile_number"),
            (r"email\s*id|e\s*mail", "email"),
            (r"pan\s*num", "pan_number"),
            (r"cif\s*id", "cif_id"),
            (r"sol\s*id", "sol_id")
        ]
    elif form_type == "courier":
        regexes = [
            (r"shipper\s*s?\s*name", "shipper_name"),
            (r"receiver\s*s?\s*name", "receiver_name"),
            (r"contact\s*name", "contact_name"),
            (r"street\s*address", "street_address"),
            (r"city\s*state\s*province", "city_state"),
            (r"postal\s*code", "postal_code"),
            (r"zip\s*post\s*code", "zip_code"),
            (r"telephone\s*no", "telephone"),
            (r"origin", "origin"),
            (r"destination", "destination"),
            (r"date\s*of\s*shipment", "shipment_date"),
            (r"weight", "weight")
        ]
    elif form_type == "education":
        regexes = [
            (r"student\s*s?\s*name", "student_name"),
            (r"father\s*s?\s*name", "father_name"),
            (r"mother\s*s?\s*name", "mother_name"),
            (r"birth\s*date|date\s*of\s*birth|dob", "date_of_birth"),
            (r"present\s*address", "present_address"),
            (r"permanent\s*address", "permanent_address"),
            (r"religion", "religion"),
            (r"nationality", "nationality"),
            (r"phone\s*num|contact\s*num|mobile\s*num", "phone_number"),
            (r"email\s*address|e\s*mail", "email"),
            (r"blood\s*group", "blood_group"),
            (r"course\s*name|course\s*applied", "course_name"),
            (r"nid\s*number|id\s*number", "nid_number"),
            (r"guardian\s*s?\s*name", "guardian_name"),
        ]
    elif form_type == "postal_speedpost":
        regexes = [
            (r"sender.*name", "sender_name"),
            (r"sender.*address", "sender_address"),
            (r"receiver.*name|addressee.*name", "receiver_name"),
            (r"receiver.*address|addressee.*address", "receiver_address"),
        ]
    elif form_type == "bank_kyc":
        regexes = [
             (r"Name[\*t]?.*Same as [I1]D proof", "full_name"),
             (r"Father\s*/\s*Spouse\s*Name", "father_spouse_name"),
             (r"Mother\s*Name", "mother_name"),
             (r"first\s*name", "first_name"),
             (r"middle\s*name", "middle_name"),
             (r"last\s*name", "last_name"),
             (r"Date\s*[Oo]f\s*[Bb]irth|Dale\s*[Gg]i[Bb]inh|D[ao][lt][ae].*[Bb]irth", "date_of_birth"),
             (r"mobile\s*num", "mobile_number"),
             (r"email\s*id|e\s*mail", "email"),
             (r"\bPAN\*?\b", "pan_number"),
             (r"Passport\s*Number|A-Passport", "passport_number"),
             (r"Driving\s*Licen[sc]e|C-Driving", "driving_licence"),
             (r"Aadhaar|E-KYC", "aadhaar_number"),
             (r"Line\s*1\*?", "address_line1"),
             (r"Line\s*2\b", "address_line2"),
             (r"Line\s*3\b", "address_line3"),
             (r"City[/\s]*[Tt]own", "city"),
             (r"District\*?", "district"),
             (r"Pin[/\s]*Post\s*Code\*?", "pin_code"),
             (r"KYC\s*Number", "kyc_number"),
             (r"cif\s*id", "cif_id"),
             (r"sol\s*id", "sol_id")
        ]

    found = []
    for pat, key in regexes:
        for m in re.finditer(pat, n): found.append((key, m.start(), m.end()))
    found.sort(key=lambda x: x[1])
    return found

# =============================================================================
def extract_text(image_path, form_type_hint="auto"):
    _init_engines()
    preprocess_image(image_path)

    print("[OCR] STAGE 1: Fast Label Detection (Tesseract)...")
    img_pil = Image.open(image_path).convert("RGB")
    data = pytesseract.image_to_data(img_pil, output_type=Output.DICT)
    lines = {}
    for i in range(len(data['text'])):
        if int(data['conf'][i]) < 0: continue
        text = data['text'][i].strip()
        if not text: continue
        line_id = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        if line_id not in lines: lines[line_id] = []
        lines[line_id].append({
            'text': text, 'left': data['left'][i], 'top': data['top'][i],
            'width': data['width'][i], 'height': data['height'][i]
        })

    all_lines_text = [" ".join([w['text'] for w in words]) for words in lines.values()]
    full_text = "\n".join(all_lines_text)

    if form_type_hint and form_type_hint != "auto":
        form_type = form_type_hint
        print(f"[OCR] Form type  : {form_type} (operator selected)")
    else:
        form_type = detect_form_type(full_text)
        print(f"[OCR] Form type  : {form_type} (auto-detected via Tesseract)")

    # ------------------ STAGE 2: TROCR VALUE EXTRACTION ---------------------
    print("\n[OCR] STAGE 2: Precision Value Extraction (TrOCR)...")
    synthetic_lines = []
    
    for line_id, words in lines.items():
        line_text = " ".join([w['text'] for w in words])
        detections = find_all_label_spans(line_text, form_type)
        if not detections:
            synthetic_lines.append(line_text)
            continue
            
        for idx, (field_key, start_char, end_char) in enumerate(detections):
            label_words = []
            curr_pos = 0
            for w in words:
                ws = line_text.find(w['text'], curr_pos)
                we = ws + len(w['text'])
                curr_pos = we
                if we > start_char and ws < end_char: label_words.append(w)
            if not label_words: continue
            
            l_box_l = min([w['left'] for w in label_words])
            l_box_t = min([w['top'] for w in label_words])
            l_box_w = max([w['left'] + w['width'] for w in label_words]) - l_box_l
            l_box_h = max([w['top'] + w['height'] for w in label_words]) - l_box_t
            
            val_l, val_t, val_b = l_box_l + l_box_w + 4, l_box_t - 4, l_box_t + l_box_h + 6
            if idx + 1 < len(detections):
                next_start = detections[idx+1][1]
                next_l_words = [w for w in words if line_text.find(w['text']) >= next_start]
                val_r = (next_l_words[0]['left'] - 6) if next_l_words else (val_l + 350)
            else:
                val_r = val_l + 400
            val_r = min(val_r, img_pil.width - 5)

            # ADDRESS BOX SPECIAL CASE: Look BELOW
            if "address" in field_key.lower():
                val_l, val_t, val_b = l_box_l, l_box_t + l_box_h + 6, l_box_t + l_box_h + 55
                val_r = min(val_l + 650, img_pil.width - 10)

            # --- DOB + COURSE_NAME SPECIAL: Prefer Tesseract segment (printed text is read cleanly) ---
            val_clean = ""
            if field_key in ("date_of_birth", "course_name"):
                next_s = detections[idx+1][1] if idx+1 < len(detections) else 9999
                seg_tess = [w['text'] for w in words
                            if line_text.find(w['text']) >= end_char
                            and line_text.find(w['text']) < next_s]
                tess_seg_text = " ".join(seg_tess).strip()
                if field_key == "date_of_birth":
                    tess_dob = parse_date_from_text(tess_seg_text)
                    if tess_dob:
                        val_clean = tess_dob
                        print(f"[OCR]   [date_of_birth] TESSERACT: '{tess_seg_text}' -> '{val_clean}'")
                elif field_key == "course_name" and tess_seg_text:
                    # Use Tesseract only – cap at 2 words to avoid reading trailing form text
                    raw = strip_letterbox_noise(tess_seg_text)
                    words_c = raw.split()
                    val_clean = " ".join(words_c[:2]) if words_c else ""
                    print(f"[OCR]   [course_name] TESSERACT: '{tess_seg_text}' -> '{val_clean}'")

            val_clean_trocr = ""
            if not val_clean and (val_r - val_l) >= 15 and (val_b - val_t) >= 5 and TROCR_AVAILABLE:
                value_crop = img_pil.crop((val_l, val_t, val_r, val_b))
                crop_path = os.path.join(debug_dir, f'{field_key}.png')
                value_crop.save(crop_path)
                
                if check_image_entropy(value_crop, field_key):
                    trimmed = trim_whitespace_from_crop(value_crop)
                    if trimmed and trimmed.width >= 5 and trimmed.height >= 5:
                        bw = trimmed.convert("L").point(lambda x: 255 if x > 200 else 0, mode='1')
                        ink_px = np.sum(np.array(bw) == 0)
                        if ink_px >= 60:
                            r_val = trocr_read_line(trimmed)
                            cl_val = post_filter_trocr(clean_trocr_line(r_val), field_key)
                            val_clean_trocr = _validate_field_value(cl_val, field_key)
                val_clean = val_clean or val_clean_trocr

                if not val_clean:
                    next_s = detections[idx+1][1] if idx+1 < len(detections) else 9999
                    seg_words = [w['text'] for w in words if line_text.find(w['text']) >= end_char and line_text.find(w['text']) < next_s]
                    tess_val = strip_letterbox_noise(" ".join(seg_words))
                    if len(tess_val) > 1:
                        v_v = _validate_field_value(tess_val, field_key)
                        if v_v:
                            val_clean = v_v
                            print(f"[OCR]   [{field_key}] FALLBACK to Tesseract: '{val_clean}'")

            print(f"[OCR]   [{field_key}] Label: '{' '.join([w['text'] for w in label_words])}' | Result: '{val_clean}'")
            synthetic_lines.append(f"{field_key} {val_clean}")

    best_text = "\n".join(synthetic_lines)
    print("\n[OCR] Final Synthetic Text:\n", best_text, "\n", "="*50)

    if form_type == "bank_kyc": fields, _ = parse_bank_kyc(best_text)
    else: fields = parse_fields(best_text, form_type)
    
    confidence = score_fields(fields, form_type)
    print("[OCR] Fields     :", fields)
    return fields, confidence, form_type

# =============================================================================
FORM_SIGNATURES = {
    "bank_kyc": [r'kyc application form', r'know your customer', r'personal details', r'residential status', r'maiden name'],
    "postal_savings": [r'post office savings bank', r'savings bank.*atm', r'cif id', r'sol id'],
    "courier": [r'shipper', r'shippers name', r'origin.*destination', r'date of shipment'],
    "postal_speedpost": [r'speed post parcel', r'india post.*parcel', r'sender.*return address', r'addressee address'],
    "education": [r'admission form', r'student.*name', r'father.*name', r'course name', r'blood group', r'nid number'],
}

def detect_form_type(text):
    lower = text.lower()
    scores = {ftype: sum(1 for pat in pats if re.search(pat, lower)) for ftype, pats in FORM_SIGNATURES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "generic"

def normalize(line):
    return re.sub(r'\s{2,}', ' ', re.sub(r'[©®°•\|\*]', '', line.lower().strip()))

def get_value(line, label_text=None):
    m = re.search(r'[\:\-\–\—]\s*(.+)', line)
    if m: return m.group(1).strip().rstrip('.,;|"\'_')
    if label_text:
        m = re.search(re.escape(label_text).replace(r'\\ ', r'\s*') + r'\s*(.*)', line, re.I)
        if m and m.group(1).strip(): return m.group(1).strip().rstrip('.,;|"\'_')
    parts = re.split(r'\s{2,}', line.strip(), 1)
    if len(parts) > 1: return parts[1].strip().rstrip('.,;|"\'_')
    parts = line.strip().split(None, 1)
    return parts[1].strip().rstrip('.,;|"\'_') if len(parts) > 1 else ""

def clean_pincode(raw):
    s = raw.replace('o','0').replace('O','0').replace('l','1').replace('I','1').replace('S','5').replace('B','8')
    return re.sub(r'\D', '', s)[:6]

def clean_address(value):
    val = re.sub(r',\s*,', ',', re.sub(r'\s*\.\s*', ', ', value)).strip(' ,')
    return strip_grid_noise(val)

def fix_remarks(value):
    lower = value.lower()
    if 'speed post' in lower: return 'Speed Post'
    if 'regd post' in lower: return 'Registered Post'
    return value.strip('.,;:| ')

def _validate_field_value(val, field_key):
    if not val: return ""
    lower_val = val.lower()
    if any(w in lower_val for w in ["mobile", "number", "first", "middle", "last", "email", "id", "cif", "sol", "mother", "name"]) and len(re.sub(r'\D', '', val)) < 5: return ""
    if field_key in ("mobile_number", "phone_number"):
        digits = re.sub(r'\D', '', val)
        if len(digits) < 3 or (len(digits) >= 8 and len(set(digits)) <= 2): return ""
    if field_key == "cif_id":
        digits = re.sub(r'\D', '', val)
        if len(digits) < 4 or len(digits) > 15: return ""
    if field_key == "pan_number":
        pan = extract_pan(val)
        return pan if pan else ""
    return val

def extract_email(raw):
    s = re.sub(r'[\s\|_]+', '', raw)
    m = re.search(r'[a-zA-Z0-9.%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', s)
    if m: return m.group().strip('.,; ')
    return ""

def extract_pan(raw):
    upper = re.sub(r'\s', '', raw.upper())
    m = re.search(r'[A-Z]{5}[0-9OIS]{4}[A-Z]', upper)
    if m:
        v = list(m.group())
        for i in range(5, 9): v[i] = v[i].replace('O','0').replace('I','1').replace('S','5')
        return "".join(v)
    return ""

def clean_name(raw):
    raw = re.sub(r'^[I\|l\.\*\#\s]+', '', raw.strip())
    tokens = raw.split()
    if len(tokens) >= 3 and all(len(t) == 1 and t.isalpha() for t in tokens): return "".join(tokens)
    res = re.sub(r'[\d\s\#\*\_]+$', '', re.sub(r'000\d*', '', re.sub(r'#+\d*', '', raw))).strip('.,;|"\' ')
    return strip_grid_noise(res)

def extract_phone(raw):
    s = raw.replace('O','0').replace('o','0').replace('I','1').replace('l','1').replace('|','1')
    m = re.search(r'(?:^|\D)([6-9]\d{9})(?:\D|$)', s)
    return m.group(1) if m else re.sub(r'\D', '', s)[:10]

# =============================================================================
def parse_generic(text):
    fields = {"name":"","address":"","phone":"","pincode":"","remarks":""}
    lines  = [l.strip() for l in text.splitlines() if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        field = match_label_generic(line)
        if field == "name":
            v = get_value(line)
            if (not v or len(v)<=2) and i+1<len(lines) and not match_label_generic(lines[i+1]): v=lines[i+1]; i+=1
            if v: fields["name"] = re.sub(r'^_?[Nn]ame\s*[\:\.\-\s]+\s*', '', v).strip()
        elif field == "address":
            v = get_value(line)
            parts, j = [v] if v else [], i+1
            while j < len(lines) and not match_label_generic(lines[j]): parts.append(lines[j]); j+=1
            i = j-1
            fields["address"] = clean_address(", ".join(parts))
        elif field == "phone":
            v = get_value(line)
            if not v and i+1<len(lines) and not match_label_generic(lines[i+1]): v=lines[i+1]; i+=1
            fields["phone"] = extract_phone(v)
        elif field == "pincode":
            v = get_value(line)
            if not v and i+1<len(lines) and not match_label_generic(lines[i+1]): v=lines[i+1]; i+=1
            if v: fields["pincode"] = clean_pincode(v)
        i += 1
    return fields

def match_label_generic(line):
    n = normalize(line)
    if 'name' in n or re.match(r'^to[\)\.\:\s,]', n): return "name"
    if 'address' in n or 'vill' in n: return "address"
    if 'phone' in n or 'mobile' in n or 'contact' in n: return "phone"
    if 'pin' in n or 'zip' in n: return "pincode"
    if 'remarks' in n: return "remarks"
    return None

# =============================================================================
def parse_bank_kyc(ocr_text):
    fields = {'first_name': '', 'middle_name': '', 'last_name': '', 'full_name': '', 'father_spouse_name': '', 'mother_name': '', 'date_of_birth': '', 'gender': '', 'pan_number': '', 'marital_status': '', 'citizenship': '', 'residential_status': '', 'address_line1': '', 'address_line2': '', 'address_line3': '', 'city': '', 'district': '', 'pin_code': ''}
    for line in ocr_text.splitlines():
        for key in fields:
            if line.strip().startswith(key + " "):
                val = line[len(key)+1:].strip()
                if key in ['first_name', 'middle_name', 'last_name']: fields[key] = clean_name(val).upper()
                else: fields[key] = val
                break
    if not fields['full_name']: fields['full_name'] = " ".join([fields[f] for f in ['first_name','middle_name','last_name'] if fields[f]]).strip()
    return fields, {}

# Indian state names for fuzzy normalization of OCR misreads
_INDIAN_STATES = [
    "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam",
    "Bihar", "Chandigarh", "Chhattisgarh", "Dadra and Nagar Haveli", "Daman and Diu",
    "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir",
    "Jharkhand", "Karnataka", "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh",
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Puducherry",
    "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal"
]

def _normalize_state(raw: str) -> str:
    """Fuzzy-match OCR state text to the closest Indian state name."""
    if not raw: return ""
    raw_clean = raw.strip().lower()
    # Exact match first
    for s in _INDIAN_STATES:
        if s.lower() == raw_clean: return s
    # Partial match: state starts with the raw text or raw starts with state
    for s in _INDIAN_STATES:
        sl = s.lower()
        if sl.startswith(raw_clean) or raw_clean.startswith(sl[:5]):
            return s
    # Token overlap: count shared words
    raw_tokens = set(raw_clean.split())
    best, best_score = raw, 0
    for s in _INDIAN_STATES:
        shared = raw_tokens & set(s.lower().split())
        if len(shared) > best_score:
            best_score = len(shared)
            best = s
    return best if best_score > 0 else raw.title()

def parse_speedpost(text):
    f = {'receiver_name': '', 'receiver_address': '', 'receiver_pincode': '',
         'receiver_city': '', 'receiver_state': '',
         'sender_name': '',   'sender_address': '',   'sender_pincode': '',
         'sender_city': '',   'sender_state': ''}
    curr = None

    # Patterns that indicate a context switch – these lines are LABELS, not names
    TO_PAT   = re.compile(r'^\s*(to|to\s*,|addressee)\s*$', re.IGNORECASE)
    FROM_PAT = re.compile(r'^\s*(from|from\s*,|sender|return\s*address)\s*$', re.IGNORECASE)
    # Individual noise tokens to strip (applied in a loop)
    NOISE_TOKEN = re.compile(r'[\s,]+(aa|a\.a\.|fb|india\s*post|speed\s*post|reg\.?d?)\s*$', re.IGNORECASE)
    # State + country pattern  e.g. "Gujarat, IND"
    STATE_PAT   = re.compile(r'^([A-Za-z][A-Za-z\s]+?),?\s*(IND|India)?\s*$', re.IGNORECASE)

    for line in text.splitlines():
        ln = line.strip()
        if not ln: continue

        # Detect TO/FROM markers and set context — skip the marker line itself
        if TO_PAT.match(ln):
            curr = 'receiver'; continue
        if FROM_PAT.match(ln):
            curr = 'sender';   continue

        # Also catch inline TO/FROM at start of a line (e.g. "To, 705 Green Palms...")
        m_to   = re.match(r'^(to|to\s*,)\s+(.+)', ln, re.IGNORECASE)
        m_from = re.match(r'^(from|from\s*,)\s+(.+)', ln, re.IGNORECASE)
        if m_to:
            curr = 'receiver'; ln = m_to.group(2).strip()
        elif m_from:
            curr = 'sender';   ln = m_from.group(2).strip()

        if not curr: continue

        # Extract pincode anywhere on the line
        pin = re.search(r'\b(\d{6})\b', ln)
        if pin: f[f'{curr}_pincode'] = pin.group(1)

        # First non-empty line after the marker → name (skip lines starting with a digit)
        if not f[f'{curr}_name'] and len(ln) > 2 and not re.match(r'^\d', ln):
            f[f'{curr}_name'] = clean_name(ln)
        else:
            sep = ' ' if f[f'{curr}_address'] else ''
            f[f'{curr}_address'] += sep + ln

    # Post-process addresses
    for side in ('sender', 'receiver'):
        addr = f[f'{side}_address'].strip()
        # Strip ALL trailing noise tokens iteratively
        prev = None
        while prev != addr:
            prev = addr
            addr = NOISE_TOKEN.sub('', addr).strip()
        # City/State extraction: split on pincode position
        # Structure in address: "Street City PINCODE State, IND"
        pin = f[f'{side}_pincode']
        if pin and pin in addr:
            pin_pos = addr.find(pin)
            pre  = addr[:pin_pos].strip(' ,')    # "Street City"
            post = addr[pin_pos + len(pin):].strip(' ,')  # "State, IND ..."
            # State = everything after pincode, strip country suffix
            state_raw = re.sub(r'[\s,]+(IND|India)\s*$', '', post, flags=re.IGNORECASE).strip(' ,.')
            state_raw = NOISE_TOKEN.sub('', state_raw).strip(' ,.')
            if state_raw:
                f[f'{side}_state'] = _normalize_state(state_raw)
            # City = last word before pincode
            city_words = pre.split()
            if city_words:
                f[f'{side}_city'] = city_words[-1].strip(' ,')
                addr = ' '.join(city_words[:-1]).strip(' ,')
            else:
                addr = pre
        f[f'{side}_address'] = addr

    return f

def parse_posavings(text):
    f = {
        "applicant_name": "", "first_name": "", "middle_name": "", "last_name": "",
        "mother_name": "", "email": "", "pan_number": "",
        "mobile_number": "", "cif_id": "", "sol_id": ""
    }
    for line in text.splitlines():
        for k in f:
            if line.startswith(k + " "):
                f[k] = line[len(k)+1:].strip()
                break

    # Auto-build full applicant name from parts
    if not f["applicant_name"]:
        parts = [f["first_name"], f["middle_name"], f["last_name"]]
        f["applicant_name"] = " ".join(p for p in parts if p).strip()

    # Clean CIF ID — should be 10–15 digits only, strip letterbox noise
    if f["cif_id"]:
        cif_digits = re.sub(r'\D', '', f["cif_id"])
        f["cif_id"] = cif_digits if 4 <= len(cif_digits) <= 15 else ""

    # Clean SOL ID — extract just the numeric SOL part
    if f["sol_id"]:
        m = re.search(r'\bSOL[:\s]+(\d+)', f["sol_id"], re.IGNORECASE)
        f["sol_id"] = m.group(1) if m else re.sub(r'\D', '', f["sol_id"].split()[0])

    return f

def parse_courier(text):
    f = {"shipper_name":"", "receiver_name":"", "postal_code":"", "origin":"", "destination":""}
    for line in text.splitlines():
        for k in f:
            if line.startswith(k + " "): f[k] = line[len(k)+1:].strip()
    return f

def parse_education(text):
    fields = {
        "student_name":"", "father_name":"", "mother_name":"",
        "date_of_birth":"", "phone_number":"",
        "present_address":"", "permanent_address":"",
        "religion":"", "nationality":"", "email":"",
        "blood_group":"", "course_name":"",
        "nid_number":"", "guardian_name":""
    }
    all_field_keys = set(fields.keys())
    lines_list = [l.strip() for l in text.splitlines() if l.strip()]
    i = 0
    while i < len(lines_list):
        line = lines_list[i]
        for key in fields:
            if line.startswith(key + " "):
                val = line[len(key)+1:].strip()
                if "name" in key:  fields[key] = clean_name(val)
                elif key == "email": fields[key] = extract_email(val)
                else: fields[key] = val
                # Address fallback: if value is too short, try the next synthetic line
                if key in ("present_address", "permanent_address") and len(fields[key]) < 5:
                    if i + 1 < len(lines_list):
                        nxt = lines_list[i + 1].strip()
                        # Only use if it's not another known field line
                        is_known = any(nxt.startswith(k + " ") for k in all_field_keys)
                        if not is_known and len(nxt) >= 5:
                            fields[key] = nxt
                break
        i += 1
    return fields

def parse_fields(text, form_type="generic"):
    if form_type == "bank_kyc": return parse_bank_kyc(text)[0]
    if form_type == "postal_speedpost": return parse_speedpost(text)
    if form_type == "postal_savings": return parse_posavings(text)
    if form_type == "courier": return parse_courier(text)
    if form_type == "education":  return parse_education(text)
    return parse_generic(text)

def score_fields(fields, form_type="generic"):
    s = {}
    for k, v in fields.items():
        val = str(v).strip()
        if not val: s[k] = 0; continue
        if any(x in k for x in ("phone","mobile","contact")): s[k] = 95 if len(re.sub(r'\D','',val))==10 else 40
        elif any(x in k for x in ("pin","postal","zip")): s[k] = 95 if len(re.sub(r'\D','',val))==6 else 40
        elif k == "pan_number": s[k] = 95 if re.match(r'^[A-Z]{5}\d{4}[A-Z]$', val.upper()) else 40
        elif k == "email": s[k] = 90 if '@' in val else 30
        elif "date" in k: s[k] = 85 if re.search(r'\d', val) else 40
        elif "name" in k: s[k] = 90 if len(val)>5 else 40
        else: s[k] = 85 if len(val)>10 else 40
    return s

def trim_whitespace_from_crop(pil_crop):
    bw = pil_crop.convert("L").point(lambda x: 255 if x > 200 else 0, mode='1')
    bbox = ImageChops.difference(pil_crop.convert("L"), Image.new('L', pil_crop.size, 255)).getbbox()
    return pil_crop.crop(bbox) if bbox else pil_crop

def strip_letterbox_noise(text):
    return re.sub(r'\s+', ' ', re.sub(r'[\[\]\|\\\/\{\}\_\~]', ' ', text)).strip()

if __name__ == "__main__":
    print(f"TrOCR available: {TROCR_AVAILABLE}")