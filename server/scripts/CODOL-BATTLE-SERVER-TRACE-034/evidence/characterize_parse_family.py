# -*- coding: utf-8 -*-
"""TASK-034: characterize the real parse family entries in RVA 0x6D000..0x6E100."""
import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def cstr(v):
    if not (0xDA0000<=v<0xE00000): return None
    o=v-BASE
    if not (0<=o<len(d)): return None
    e=d.find(b'\x00',o)
    if e<0 or e-o>64: return None
    s=d[o:e]
    return s.decode('latin1') if all(32<=c<127 for c in s) else None
entries=[p for p in range(0x6D060,0x6E100) if d[p-1]==0xCC and (d[p:p+3] in (b"\x55\x8b\xec",b"\x6a\xff") or d[p:p+2]==b"\x8b\xff")]
print("entries in 0x6D000..0x6E100: %s" % " ".join("%X"%x for x in entries))
print()
for e in entries:
    nxt=next((x for x in entries if x>e), e+0x120)
    # collect direct calls and string pushes within the function (bounded)
    calls=[]; strs=[]; reads=[]
    cnt=0
    for ins in md.disasm(d[e:e+(nxt-e)], e):
        cnt+=1
        if ins.mnemonic=="call" and ins.op_str.startswith("0x"): calls.append(int(ins.op_str,16))
        if ins.mnemonic in ("push","mov","cmp") and ins.op_str.startswith("0x"):
            v=int(ins.op_str,16); s=cstr(v)
            if s: strs.append(s)
        if ins.mnemonic=="mov" and "dword ptr [" in ins.op_str and "0x7" in ins.op_str:
            reads.append(ins.op_str)
        if cnt>200: break
    print("--- entry RVA %X (size %d insns) ---" % (e,cnt))
    if strs: print("    strings: %s" % [s[:36] for s in strs[:4]])
    if calls: print("    direct calls: %s" % ", ".join("%X"%c for c in calls[:10]))
