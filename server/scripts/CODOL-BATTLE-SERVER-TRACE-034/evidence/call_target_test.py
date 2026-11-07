import struct, capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read()
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def prologue_at_off(off):
    if off<0 or off+3>len(d): return None
    if d[off:off+3]==b"\x55\x8b\xec": return "55 8b ec (push ebp; mov ebp,esp)"
    if d[off:off+1]==b"\x55": return "55 (push ebp)"
    if d[off:off+3]==b"\x6a\xff": return "6a ff (push -1)"
    if d[off:off+2]==b"\x8b\xff": return "8b ff (mov edi,edi)"
    if d[off:off+1]==b"\xcc": return "cc (int3 - NOT a function)"
    return d[off:off+4].hex()
def first_calls(off, k=6, span=0x120):
    """disassemble from off and collect the first k E8 direct call targets"""
    res=[]
    for ins in md.disasm(d[off:off+span], off):
        if ins.mnemonic=="call" and ins.op_str.startswith("0x"):
            t=int(ins.op_str,16)
            res.append((ins.address, t))
            if len(res)>=k: break
    return res
print("Hypothesis A: file_offset == VA  (callsite VA = offset, target VA = offset)")
print("Hypothesis B: file_offset == VA-0x400000  (callsite VA = offset+0x400000)")
for label, n, hyp in [("packetEvent",0x467520,"A"),("packetEvent",0x467520,"B")]:
    off = n if hyp=="A" else n-0x400000
    print("\n== %s, hypothesis %s, disasm base VA=0x%X ==" % (label, hyp, off if hyp=="A" else off+0x400000))
    for cs,tgt in first_calls(off):
        toff = tgt if hyp=="A" else tgt-0x400000
        pr = prologue_at_off(toff) if 0<=toff<len(d) else "OUT_OF_FILE"
        print("   call@%08X -> target VA %08X   file[target]= %s" % (cs, tgt, pr))
