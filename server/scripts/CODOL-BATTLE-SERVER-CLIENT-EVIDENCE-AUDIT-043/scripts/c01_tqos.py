# -*- coding: utf-8 -*-
"""Phase C: TQOS attribution re-check by dataflow (not adjacency); dispatcher
call-chain; IAT slot coverage. Read-only."""
import sys, os, io, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._bi; out=[]
def emit(s): out.append(s)

# 1) direct string refs to TQOS strings in code section
emit("=== TQOS string refs in code section (imm32) ===")
code=b[0x1000:0x8a8000]
for rva,label in [(0x985AA4,"QOSCSPkg"),(0x985A94,"QOSCSPkgHead"),(0x985A84,"QOSCSPkgBody"),
                  (0x985A78,"QOSSSPkg"),(0x985A68,"QOSSSPkgHead"),(0x985A58,"QOSSSPkgBody"),
                  (0x985AB0,"udp://%s:%d"),(0x985AE0,"tqos_find_connd_by_ip fail"),
                  (0x985AF0,"tqos_get_qosconnd_iplist fail"),(0x985B1C,"tqos_create_protohandle err")]:
    s=C.icstr(rva,30)
    va=C.IBI+rva; pat=struct.pack("<I",va); refs=[]; i=0
    while True:
        j=code.find(pat,i)
        if j<0: break
        refs.append(0x1000+j); i=j+1
    emit("  %08x %-32s %s"%(rva, (s or b"")[:30].decode("latin1","replace"), [hex(x) for x in refs]))

# 2) dispatcher function boundary + callers of its entry & its caller fn entry
def cc_run_starts(lo,hi):
    res=[]; i=lo
    while i<hi-2:
        if b[i]==0xCC and b[i+1]==0xCC and b[i+2]==0xCC:
            e=i
            while e<hi and b[e]==0xCC: e+=1
            res.append((i,e)); i=e
        else: i+=1
    return res
emit("")
emit("=== function boundaries around 0x85E6F0 ===")
for (a,e) in cc_run_starts(0x85E000,0x85F000):
    emit("  cc %08x..%08x -> next %08x"%(a,e,e))

# 3) do 0x85E6F0 / handlers reference any TQOS string? (direct imm32)
def refs_of(lo,hi):
    got=[]
    for k in C.idis_range(lo,hi):
        for tok in k.op_str.replace("["," ").replace("]"," ").replace(","," ").split():
            if tok.startswith("0x"):
                try: v=int(tok,16)
                except: continue
                if 0x800000<=v<0xA65000:  # string region
                    got.append((k.address-C.IBI, v-C.IBI))
    return got
for lo,hi,lab in [(0x85E6F0,0x85E800,"dispatcher 0x85E6F0"),
                  (0x85E4F0,0x85E5C0,"handler 0x85E4F0"),
                  (0x85E5C0,0x85E6F0,"handler 0x85E5C0"),
                  (0x85D2E0,0x85D3A0,"ctor 0x85D2E0")]:
    emit("")
    emit("=== string refs in %s ==="%lab)
    for a,r in refs_of(lo,hi):
        s=C.icstr(r,40)
        if s and all(32<=c<127 for c in s):
            emit("  %08x -> rva %08x  %s"%(a,r,s[:40].decode("latin1")))
io.open(os.path.join(C.EV,"c_stage_tqos_and_chain.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
