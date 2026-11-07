from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
# find all callers of 0xBA3710 to prove it is 0x85-only
import struct
print("=== raw callers of 0xBA3710 in whole image ===")
lo,hi=0x400000,0xE65000
lo_off=lo-BASE; hi_off=hi-BASE
hits=[]
for i in range(lo_off, min(hi_off, len(data))-5):
    if data[i]==0xE8:
        rel=struct.unpack_from("<i", data, i+1)[0]
        if (BASE+i+5+rel) & 0xFFFFFFFF == 0xBA3710:
            hits.append(BASE+i)
print("count:", len(hits))
for h in hits[:20]: print("   %08X" % h)
print()
print("=== also count callers of 0xBA3600 (0x89 branch) ===")
h2=[]
for i in range(lo_off, min(hi_off, len(data))-5):
    if data[i]==0xE8:
        rel=struct.unpack_from("<i", data, i+1)[0]
        if (BASE+i+5+rel) & 0xFFFFFFFF == 0xBA3600:
            h2.append(BASE+i)
print("count:", len(h2))
for h in h2[:10]: print("   %08X" % h)
