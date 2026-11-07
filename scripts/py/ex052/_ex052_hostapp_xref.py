from pathlib import Path
import re
path = Path(r'COD OL\IIPS\iips.dll')
text = path.read_bytes()
base = 0x10000000
rdata = text[0x33000:0x33000+0xEC81]
for pat,label in [(b'IIPSHostApp.ini','ini'),(b'IIPSHostApp.exe','exe')]:
    off = rdata.find(pat)
    addr = base + 0x33000 + off
    print('rdata', label, hex(addr), off)
    hits = [m.start() for m in re.finditer(re.escape(pat), text) if m.start() != 0x33000+off]
    print('count', len(hits), [hex(base+i) for i in hits[:20]])
