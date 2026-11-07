import struct, capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def rd(va,n): return d[va-BASE:va-BASE+n]
def xref_push(addr):
    """find 'push imm32' with imm == addr (VA)"""
    pat=b"\x68"+struct.pack("<I",addr); out=[]; s=0
    while True:
        i=d.find(pat,s)
        if i<0: break
        out.append(i+BASE); s=i+1
    return out
def xref_mov(addr):
    out=[]
    for op in (0xB8,0xB9,0xBA,0xBB,0xBE,0xBF):
        pat=bytes([op])+struct.pack("<I",addr); s=0
        while True:
            i=d.find(pat,s)
            if i<0: break
            out.append((op,i+BASE)); s=i+1
    return out
print("=== Absolute xrefs for the battle command strings (convention: string VA = file_offset+0x400000) ===")
for s_off,label in [(0x9BFD04,"getchallenge"),(0x9B4700,"gamestateupdate"),(0x9BFE40,"heartbeat"),
                    (0x9B42E0,"heartbeat(2)"),(0x9BFEE8,"challengeResponse")]:
    va=s_off+BASE
    pu=xref_push(va); mv=xref_mov(va)
    print("%-20s VA=%08X push_refs=%s mov_refs=%s" % (label,va,["%X"%a for a in pu[:6]] or "-",
          ["%s@%X"%(hex(o),a) for o,a in mv[:4]] or "-"))
