import pefile, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
path = Path(r'WeGame\client_launcher.exe')
pe = pefile.PE(str(path), fast_load=True)
data = pe.__data__
base = pe.OPTIONAL_HEADER.ImageBase
addrs = [0x4327A4,0x4327F8,0x432818,0x432897,0x4328D8,0x4328FC,0x432908,0x432A0C,0x432A24,0x432B10,0x447000,0x432382,0x43034D,0x4303FE]
def read(va):
    off = pe.get_offset_from_rva(va-base)
    if off < 0 or off >= len(data): return None
    return off
for va in addrs:
    off = read(va)
    print(f'\nVA {va:08X} FILE {off:08X}')
    if off is None: continue
    print('raw', data[off:off+96].hex(' '))
    for enc, width in [('latin1',1),('utf-16le',2)]:
        raw = data[off:off+512]
        end = 0
        while end+width <= len(raw):
            chunk = raw[end:end+width]
            if chunk == b'\0'*width: break
            if width == 1 and (chunk[0] < 32 or chunk[0] >= 127) and chunk[0] not in (9,10,13): break
            if width == 2 and (chunk[1] != 0): break
            end += width
        if end:
            try: s = raw[:end].decode(enc, errors='strict')
            except Exception: continue
            print(enc, repr(s))
