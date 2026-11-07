import re
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
def s(va,n=80):
    o=va-base
    if o<0 or o>=len(d): return "<out>"
    e=d.find(b"\x00",o)
    return d[o:min(e if e>0 else o+n, o+n)].decode("latin1","replace")
print("=== 关键字符串 ===")
for va in (0xDA0CDC,0xDBD820,0xDE691C,0xDE6924,0xDE692C,0xDE6934,0xDE693C,0xDE6944,0xDE694C,0xDAA778):
    print("   0x%08X %r"%(va,s(va)))
print()
print("=== 0xDA0CDC 周边 ===")
o=0xDA0CDC-base
for m in re.finditer(rb"[\x20-\x7e]{3,}", d[o-0x80:o+0x120]):
    print("   0x%08X %r"%(0xDA0CDC-0x80+m.start(), m.group().decode("latin1")[:100]))
