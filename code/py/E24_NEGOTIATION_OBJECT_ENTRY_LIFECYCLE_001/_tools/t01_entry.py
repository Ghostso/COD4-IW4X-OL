import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img()
cm = call_targets(img)
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_6ab310_full.txt","w",encoding="utf-8")
# find function start
st = func_start(img, 0x6AB310)
print("func_start candidate:", hex(st))
# find the end: scan until next 0xCC run followed by a new prologue after ret
dump(img, st, 0x900, OUT, "0x6AB310 FUNC")
OUT.close()
print("dumped")
# entry paths for 0x6AB310
print("E8/E9 callers of RVA 0x6AB310:", [(hex(r),hex(op)) for r,op in find_calls(img, cm, 0x6AB310)])
# pointer-form
import struct
for form,val in (("VA",img.IB+0x6AB310),("RVA",0x6AB310)):
    pat=struct.pack("<I",val); cnt=img.d.count(pat)
    print("  %s-form %08X occurrences: %d"%(form,val,cnt))
