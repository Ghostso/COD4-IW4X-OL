import pefile, math, collections
from capstone import *
p=r"COD OL\ace-ats32.dll"
pe=pefile.PE(p)
print("=== sections ===")
for s in pe.sections:
    nm=s.Name.rstrip(b"\x00").decode("latin1")
    seg=open(p,"rb").read()[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
    if seg:
        c=collections.Counter(seg[:0x20000]); tot=len(seg[:0x20000])
        ent=-sum((v/tot)*math.log2(v/tot) for v in c.values())
        z=seg[:0x20000].count(0)/tot if tot else 0
    else: ent=0; z=0
    print("  %-10s VA 0x%08X vsize 0x%-8X raw 0x%-7X rsize 0x%-7X ent %.2f zeros %.2f"%(nm, s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData, ent, z))
print()
d=open(p,"rb").read()
import re
print("=== RTTI / 类名 ===")
seen=set()
for m in re.finditer(rb"\.\?A[UV][A-Za-z0-9_@?$]{2,70}", d):
    s=m.group().decode("latin1")
    if s in seen: continue
    seen.add(s); print("  off 0x%06X %s"%(m.start(), s[:110]))
    if len(seen)>40: break
