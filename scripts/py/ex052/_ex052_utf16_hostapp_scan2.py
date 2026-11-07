import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
import re
path = Path(r'COD OL\IIPS\iips.dll')
text = path.read_bytes()
for base in [0x33000, 0x36000, 0x37000]:
    seg = text[base:base+0x2000]
    matches = list(re.finditer(rb'(?:IIPSHostApp[^\x00\n\r]{0,40})', seg))
    seen=[]
    for m in matches:
        s=m.group().decode('utf-16le','ignore')
        if s not in seen:
            seen.append(s)
    if seen:
        print('base', hex(base), seen)
