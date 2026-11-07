from capstone import *
import struct, re
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
def refs(tgt):
    le=struct.pack("<I",tgt); h=[];o=0
    while True:
        j=d.find(le,o)
        if j<0: break
        h.append(base+j); o=j+1
    return h
for tgt,name in [(0xDBD820,"Live_Init"),(0xDE691C,"1750")]:
    r=refs(tgt)
    print("=== %s (0x%08X) 引用 %d ==="%(name,tgt,len(r)))
    for va in r:
        st=max(0,va-base-24)
        for x in md.disasm(d[st:va-base+8], base+st):
            m="  <<<" if x.address<=va<x.address+x.size else ""
            print("      %08X  %-18s %s %s%s"%(x.address,x.bytes.hex(),x.mnemonic,x.op_str,m))
        print()
print()
print("=== DBD820 周边串 ===")
o=0xDBD7E0-base
for m in re.finditer(rb"[\x20-\x7e]{4,}", d[o:o+0x120]):
    print("   0x%08X %r"%(0xDBD7E0+m.start(), m.group().decode("latin1")[:90]))
