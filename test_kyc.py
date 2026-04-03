from ocr.extractor import parse_bank_kyc

text = """
BANK KYC FORM
Name* Same as ID proof
[J][O][H][N]

Father / Spouse Name
[S][M][I][T][H]

Dale of Birth
[1|2]-[0|5]-[1|9|9|0]

PAN*
[A/B/C/D/E/1/2/3/4/F]

Aadhaar Number
1234 5678 9012
"""

fields, conf = parse_bank_kyc(text)
print("FIELDS:", fields)
print("CONF:", conf)
