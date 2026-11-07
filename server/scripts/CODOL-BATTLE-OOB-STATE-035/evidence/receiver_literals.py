# -*- coding: utf-8 -*-
"""TASK-035: receiver 0x1C13A0 -- which literals does it reference? (recognition vs logging)"""
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
    s=d[o:e]
    return s.decode('latin1') if s and all(32<=c<127 for c in s) else None
def xrefs(va):
    out=[]
    for pfx,ln in ((b"\x68",5),(b"\xb8",5),(b"\xb9",5),(b"\xba",5),(b"\xbe",5),(b"\xbf",5)):
        pat=pfx+struct.pack("<I",va); s=0
        while True:
            i=d.find(pat,s)
            if i<0: break
            out.append((i,pfx.hex())); s=i+1
    return out
def entry_back(r,back=0x4000):
    for p in range(r,r-back,-1):
        if p<=0: break
        if d[p-1]==0xCC and (d[p:p+3] in (b"\x55\x8b\xec",b"\x6a\xff") or d[p:p+2]==b"\x8b\xff"):
            return p
    return None
print("== literal -> xref sites -> enclosing function ==")
lits=[(0xDBFE28,"connect %s \"%s\""),(0xDBFE38,"stats"),(0xDBFE40,"heartbeat"),
      (0xDBFEE8,"challengeResponse"),(0xDBFEFC,"connectReject"),(0xDBFF0C,"connectResponse"),
      (0xDBFF1C,"heartbeatresponse"),(0xDBFF30,"statResponse"),(0xDBFF40,"disconnect_ack"),
      (0xDBFF50,"echo"),(0xDBFC8C,"cancelConnect"),(0xDBFD04,"getchallenge fmt"),
      (0xDBFFB4,"userinfo fmt")]
for va,lab in lits:
    xs=xrefs(va)
    if not xs: print("  %-22s NO XREF" % lab); continue
    for off,form in xs:
        e=entry_back(off)
        print("  %-22s xref@RVA %06X(%s) -> fn %s" % (lab,off,form,("%X"%e) if e else "?"))
print()
print("== receiver candidate: what does the fn at 0x1C13A0 look like? (first 90 insns) ==")
n=0
for ins in md.disasm(d[0x1C13A0:0x1C14C0],0x1C13A0):
    note=""
    if ins.mnemonic in ("push","mov") and ins.op_str.startswith("0x"):
        c=cstr(int(ins.op_str,16))
        if c: note="   ; %r"%c
    print("  RVA %08X  %-18s %s %s%s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,note))
    n+=1
    if n>=90: break
