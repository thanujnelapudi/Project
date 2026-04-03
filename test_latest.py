import os, glob
from ocr.extractor import extract_text

files = glob.glob('uploads/*_processed.*')
if not files:
    files = glob.glob('uploads/*')
files.sort(key=os.path.getmtime, reverse=True)
latest = files[0]
print("Running OCR on:", latest)

fields, conf, form_type = extract_text(latest, form_type_hint='bank_kyc')
print("Extracted fields:", fields)
