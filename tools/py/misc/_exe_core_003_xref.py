from pathlib import Path
import re
p = Path(r"COD OL\codoMP_client_shipRetail.exe")
text = p.read_bytes()
ib = 0x400000
for rva in [0x77F580, 0x77F8B3, 0x4FD9B0, 0x4FCEE0, 0x808650, 0x7E98F0, 0x6212C0]:
    target = ib + rva
    pat = re.escape(target.to_bytes(4, "little"))
    hits = [m.start() for m in re.finditer(pat, text)]
    print(hex(target), len(hits), [hex(ib + i) for i in hits[:20]])
