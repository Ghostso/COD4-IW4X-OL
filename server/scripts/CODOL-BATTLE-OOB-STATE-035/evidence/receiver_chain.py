# -*- coding: utf-8 -*-
"""TASK-035: receiver comparison chain 0x1C13A0 -- dispatch structure over OOB reply tokens."""
import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def cstr(va):
    if not (0x900000<=va<0xE40000): return None
    o=va-BASE
    if not (0<=o<len(d)): return None
    e=d.find(b'\x00',o)
    if e<0 or e-o>72: return None
    return d[o:e].decode('latin1')
print("== comparison sites + following branch (windows around each xref) ==")
for site,lab in [(0x1C1684,"challengeResponse"),(0x1C1755,"connectReject"),(0x1C17B4,"connectResponse"),
                 (0x1C18B5,"heartbeatresponse"),(0x1C1963,"statResponse"),(0x1C1B0A,"disconnect_ack"),
                 (0x1C1B4A,"echo")]:
    print("--- %s (xref @ RVA %06X) ---" % (lab,site))
    n=0
    for ins in md.disasm(d[site-0x10:site+0x2A], site-0x10):
        note=""
        if ins.mnemonic=="call" and ins.op_str.startswith("0x"): note="  ; call"
        if ins.mnemonic.startswith("j") : note="  ; branch"
        print("    RVA %08X  %-16s %s %s%s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,note))
        n+=1
        if n>=22: break
