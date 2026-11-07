p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
def s(va,n=120):
    o=va-base
    if o<0 or o>=len(d): return "<out>"
    e=d.find(b"\x00",o)
    return d[o:min(e if e>0 else o+n,o+n)].decode("latin1","replace")
print("=== 关键字符串 ===")
for va in (0xDDBF8C,0xDDBFA0,0xE609A50,0x81AA758):
    print("   0x%08X %r"%(va,s(va)))
print()
print("=== 0xDDBF60..0xDDC020 区域全串 ===")
import re
o=0xDDBF60-base
for m in re.finditer(rb"[\x20-\x7e]{3,}", d[o:o+0x100]):
    print("   0x%08X %r"%(0xDDBF60+m.start(), m.group().decode("latin1")[:110]))
