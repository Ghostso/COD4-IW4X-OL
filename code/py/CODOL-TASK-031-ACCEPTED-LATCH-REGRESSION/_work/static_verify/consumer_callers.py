import struct, capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def call_xrefs(t):
    res=[];
    for i in range(len(d)-5):
        if d[i]==0xE8:
            rel=struct.unpack_from("<i",d,i+1)[0]; va=i+BASE
            if (va+5+rel)&0xffffffff==t: res.append(va)
    return res
print("callers of 0x634340 (latch consumer fn):", ["%08X"%a for a in call_xrefs(0x634340)] or "NONE")
print("callers of 0x634080:", ["%08X"%a for a in call_xrefs(0x634080)] or "NONE")
# find vtable install: c7 01/02/03/06/07/00/41... imm32
def find_pattern(pat):
    s=0;out=[]
    while True:
        i=d.find(pat,s)
        if i<0: break
        out.append(i+BASE); s=i+1
    return out
for vt in (0xDC73A0,0xDC7840):
    tb=struct.pack("<I",vt); hits=[]
    for modrm in range(256):
        pat=bytes([0xC7,modrm])+tb
        for a in find_pattern(pat): hits.append((a,modrm))
    print("vtable %08X mov [mem],imm hits: %s" % (vt, hits[:20] or "NONE"))
