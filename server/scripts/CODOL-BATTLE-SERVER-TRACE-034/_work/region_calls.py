import struct, capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def entries(lo,hi):
    out=[]
    for p in range(lo,hi):
        if d[p-1]==0xCC and (d[p:p+3] in (b"\x55\x8b\xec",b"\x6a\xff") or d[p:p+2]==b"\x8b\xff"):
            out.append(p)
    return out
ents=entries(0x60000,0x70000)
print("Function entries scanned in msg/parse region: %d" % len(ents))
# find the region containing RVA 0x6E6A0
lo=max(e for e in ents if e<=0x6E6A0)
nxt=min([e for e in ents if e>lo], default=lo+0x400)
print("Region containing probe RVA 0x6E6A0: entry=0x%X .. next=0x%X (size %d)" % (lo,nxt,nxt-lo))
print()
# Collect every direct call (E8) in each entry, resolve and classify target
def disasm_entry(e, limitbytes=0x1200):
    seen=[]
    for ins in md.disasm(d[e:e+limitbytes], e):
        if ins.mnemonic=="call":
            op=ins.op_str
            if op.startswith("0x"):
                seen.append((ins.address, int(op,16), "direct"))
            elif op.startswith("dword ptr [") or op.startswith("qword ptr ["):
                seen.append((ins.address, op, "indirect"))
        if ins.mnemonic.startswith("ret"): break
    return seen
print("=== calls inside the parseServerMessage-region function @0x%X ===" % lo)
for a,t,k in disasm_entry(lo):
    tag = ("VA %X RVA %X"%(t,t-BASE)) if isinstance(t,int) else t
    print("   call@%X -> %s (%s)" % (a,tag,k))
