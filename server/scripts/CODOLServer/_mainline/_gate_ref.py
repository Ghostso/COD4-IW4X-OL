from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
for tgt,name in [(0x849B61F,"门1 gate61F"),(0x7EF43C,"tick跳转表")]:
    if name.startswith("tick"):
        print("=== %s @0x%08X (10 项) ==="%(name,tgt))
        for i in range(10):
            v=struct.unpack_from("<I",d,tgt-base+i*4)[0]
            print("   step %d -> 0x%08X"%(i,v))
        continue
    le=struct.pack("<I",tgt)
    hits=[]; o=0
    while True:
        j=d.find(le,o)
        if j<0: break
        hits.append(base+j); o=j+1
    print()
    print("=== 引用 0x%08X (%s) 共 %d 处 ==="%(tgt,name,len(hits)))
    for va in hits:
        st=max(0,va-base-16)
        for x in md.disasm(d[st:va-base+8], base+st):
            m="  <<<" if x.address<=va<x.address+x.size else ""
            print("      %08X  %-20s %s %s%s"%(x.address,x.bytes.hex(),x.mnemonic,x.op_str,m))
        print()
