from pathlib import Path
import struct, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p=Path(r'COD OL\WeGameLauncher\launcher.exe')
b=p.read_bytes(); base=0x400000
for va in [0x56f574,0x56f534,0x56f528,0x56f51c,0x56f50c,0x56f4f4,0x56f500,0x56f596,0x56a230]:
    off=va-base
    chunk=b[off:off+256]
    print(f'VA {va:08X} off {off:08X} bytes={chunk[:64].hex(" ")}')
    for enc in ('latin1','utf-16le'):
        parts=[]
        try:
            s=chunk.decode(enc,errors='ignore')
            parts=[x for x in re.split(r'[\x00\r\n]+',s) if x]
        except Exception: pass
        if parts: print(enc, repr(parts[:6]))
print('DWORD refs:')
vals=[0x56f574,0x56f534,0x56f528,0x56f51c,0x56f50c,0x56f4f4,0x56f500]
for i in range(0,len(b)-4):
    v=struct.unpack_from('<I',b,i)[0]
    if v in vals:
        print(f'file {i:08X} VA {base+i:08X} -> {v:08X}')
