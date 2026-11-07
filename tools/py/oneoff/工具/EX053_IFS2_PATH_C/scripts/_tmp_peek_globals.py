from pathlib import Path
import struct
with Path('codoMP_client_shipRetail.exe').open('rb') as f:
    f.seek(0x3c); pe=struct.unpack('<I',f.read(4))[0]
    f.seek(pe+6); n=struct.unpack('<H',f.read(2))[0]
    f.seek(pe+20); oh=struct.unpack('<H',f.read(2))[0]
    so=pe+24+oh
    secs=[]
    for i in range(n):
        f.seek(so+40*i); h=f.read(40)
        name=h[:8].split(b'\0')[0].decode('latin1'); vs,va,rs,pr=struct.unpack_from('<IIII',h,8); ch=struct.unpack_from('<I',h,36)[0]
        secs.append((name,va,vs,rs,pr,ch))
def off(rva):
    for z in secs:
        name,va,vs,rs,pr,ch=z
        if va<=rva<va+min(vs,rs): return pr+rva-va
    return None
for va in [0x7886E60,0x7886E68,0x7886E6C,0x81AA110,0x81AA114,0x1CD5EF8,0x1CD5EFC,0xC9EFC34,0xC9EFC38,0xC9FFD54,0xC9FFD58]:
    o=off(va-0x400000)
    if o is None:
        print(hex(va),'NO_RAW'); continue
    with Path('codoMP_client_shipRetail.exe').open('rb') as f: f.seek(o); b=f.read(16)
    print(hex(va),hex(o),b.hex(),[hex(struct.unpack_from('<I',b,k)[0]) for k in range(0,16,4)])
