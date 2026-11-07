import pefile, re
p=r"COD OL\GDPLoader.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase; d=open(p,"rb").read()
# TssQosPkg 在 .rdata 0x10037450
for name,va in [("TssQosPkg",0x10037450),("tqos.gamesafe.qq.com",0x10037438)]:
    o=pe.get_offset_from_rva(va-ib)
    e=d.find(b"\x00",o)
    print("%-24s VA 0x%08X -> %r"%(name,va,d[o:e].decode("latin1")))
print()
print("=== .rdata 0x10037400 起 512 字节的可读串（TssQosPkg 邻域）===")
o=pe.get_offset_from_rva(0x10037400-ib)
seg=d[o:o+0x200]; i=0
while i<len(seg):
    j=i
    while j<len(seg) and 32<=seg[j]<127: j+=1
    if j-i>=2:
        print("   VA 0x%08X  %r"%(0x10037400+i, seg[i:j].decode("latin1"))); i=j
    else: i+=1
