from pathlib import Path
import re
path = Path(r'COD OL\IIPS\iips.dll')
text = path.read_bytes()
for pat in [b'.ini', b'IIPSHostApp', b'HostApp', b'ResPool', b'ReservedSize']:
    hits = [m.start() for m in re.finditer(re.escape(pat), text)]
    print(pat, len(hits), [hex(0x10000000+i) for i in hits[:20]])
