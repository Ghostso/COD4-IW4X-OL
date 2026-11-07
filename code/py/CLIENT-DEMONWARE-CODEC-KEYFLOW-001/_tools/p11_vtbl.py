import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img(); IB=im.IB
print("bytes @0xC5A31C:", im.rd(0xC5A31C,64).hex(" "))
print("bytes @0xC5BEB0:", im.rd(0xC5BEB0,32))
print("has reloc dir:", im.pe.OPTIONAL_HEADER.DATA_DIRECTORY[5].VirtualAddress, im.pe.OPTIONAL_HEADER.DATA_DIRECTORY[5].Size)
n,sva,vs,rp,rs,x=[s for s in im.secs if s[0]=='.text'][0]
d=im.d[rp:rp+rs]
for val,lab in [(0xC5A31C,"vtbl"),(0xC5BEB0,"ciphername")]:
    pat=struct.pack("<I",val); c=[]; i=d.find(pat)
    while i!=-1: c.append(IB+sva+i); i=d.find(pat,i+1)
    print("%s literal refs in .text: %d %s"%(lab,len(c),[hex(a) for a in c[:12]]))
print()
print("---- 0xA888A0 ----")
for i in im.dis(0xA888A0-0x400000,0x60): print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print("---- 0xACBAF0 ----")
for i in im.dis(0xACBAF0-0x400000,0x70): print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print("---- 0xDF6216D ----")
for i in im.dis(0xDF6216D-0x400000,0x50): print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
