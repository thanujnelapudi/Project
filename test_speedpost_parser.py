import re

INDIAN_STATES = [
    "Andhra Pradesh", "Assam", "Bihar", "Goa", "Gujarat", "Haryana", "Karnataka", "Kerala", 
    "Madhya Pradesh", "Maharashtra", "Odisha", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana", "Uttar Pradesh", "Uttarakhand", "West Bengal"
]

MAJOR_CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Bengaluru", "Hyderabad", "Ahmedabad", "Chennai", "Kolkata", "Surat", 
    "Pune", "Jaipur", "Lucknow", "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", "Patna", "Vadodara"
]

def extract_geography(text):
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

def parse_speedpost(text: str) -> dict:
    fields = {
        'receiver_name': '', 'receiver_address': '', 'receiver_pincode': '',
        'receiver_city': '', 'receiver_state': '',
        'sender_name': '', 'sender_address': '', 'sender_pincode': '',
        'sender_city': '', 'sender_state': ''
    }
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    to_lines, from_lines = [], []
    current = None
    for line in lines:
        u = line.upper()
        if re.match(r'^TO[\)\.\:\s,]*$', u) or u == 'TO':
            current = 'to'
            continue
        elif re.search(r'^FROM[\)\.\:\s,]*$', u) or u == 'FROM':
            current = 'from'
            continue
        
        if current == 'to':  to_lines.append(line)
        if current == 'from': from_lines.append(line)

    def extract_block_data(block_lines, prefix):
        if not block_lines: return
        fields[f'{prefix}_name'] = re.sub(r'^(TO|FROM)[\)\.\:\s,]+', '', block_lines[0], flags=re.IGNORECASE).strip()
        addr_parts = []
        for line in block_lines[1:]:
            u = line.upper()
            if u in ('INDIA POST', '[SPEED POST]', 'SPEED POST', 'AA FB', 'IND'): continue
            if re.search(r'\b\d{10}\b', line): continue
            pin = re.search(r'\b(\d{6})\b', line)
            if pin and not fields[f'{prefix}_pincode']:
                fields[f'{prefix}_pincode'] = pin.group(1)
                rem = line.replace(pin.group(1), '').strip(' ,-—~')
                if rem: addr_parts.append(rem)
                continue
            addr_parts.append(line)
        addr = ', '.join(addr_parts)
        fields[f'{prefix}_address'] = addr
        c, s = extract_geography(addr)
        if c: fields[f'{prefix}_city'] = c
        if s: fields[f'{prefix}_state'] = s

    extract_block_data(to_lines, 'receiver')
    extract_block_data(from_lines, 'sender')
    return fields

sample_text = """[SPEED POST]
To,
Mr Ramesh Senjaliya
705, Green Palms
VIP Road
Surat
395007
Gujarat, IND
From,
Mr Kaushik Shrivastav
12-D, Aashiyana
Shyamla Hills Road
Bhopal
462002
Madhya Pradesh, IND
aa FB
India Post"""

res = parse_speedpost(sample_text)
for k in sorted(res.keys()):
    print(f"{k} -> {res[k]}")
