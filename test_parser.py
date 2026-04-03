import sys
sys.path.append('.')
from ocr.extractor import parse_fields

text = """INDIA POST - POSTAL FORM
Name: Thanuj Kumar.
Address: 12 MG Road Hyderabad Telangana
Phone: 9876543210
Pincode: 500001
Remarks: Speed Post"""

result = parse_fields(text)
print("Name:    ", result["name"])
print("Phone:   ", result["phone"])
print("Pincode: ", result["pincode"])
print("Address: ", result["address"])
print("Remarks: ", result["remarks"])