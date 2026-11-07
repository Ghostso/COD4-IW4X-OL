from pathlib import Path
import re
import pefile

path = Path(r'COD OL\IIPS\iips.dll')
data = path.read_bytes()
pe = pefile.PE(str(path))
base = pe.OPTIONAL_HEADER.ImageBase
rdata = data[0x33000:0x33000+0xEC81]
text = data

needles = [
    (b'IFS2.dll', 'IFS2_upper'),
    (b'ifs2.dll', 'ifs2_lower'),
    (b'IIPSHostApp.ini', 'host_ini'),
    (b'IIPSHostApp.exe', 'host_exe'),
    (b'ReservedSize', 'reserved_size'),
    (b'[ResPool]', 'respool'),
]

def find_rdata(pattern, label):
    print(f'## {label}')
    for m in re.finditer(re.escape(pattern), rdata):
        addr = base + 0x33000 + m.start()
        hits = []
        for mm in re.finditer(re.escape(pattern), text):
            if mm.start() == 0x33000 + m.start():
                continue
            hits.append(hex(base + mm.start()))
        print(hex(addr), hits[:20], 'count=', len(hits))

for pat, label in needles:
    find_rdata(pat, label)
