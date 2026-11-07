import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read()
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def plaus(off):
    if off is None or off<0 or off+3>len(d): return "OUT_OF_FILE"
    if d[off:off+3]==b"\x55\x8b\xec": return "PROLOGUE 55 8b ec"
    if d[off:off+3]==b"\x6a\xff": return "hotpatch 6a ff"
    if d[off:off+2]==b"\x8b\xff": return "8b ff (mov edi,edi)"
    if d[off:off+2]==b"\x55\x8b": return "55 8b"
    if d[off:off+1]==b"\x55": return "55"
    if d[off:off+1]==b"\xcc": return "int3(padding!)"
    return d[off:off+4].hex()
def test(F, B, label):
    print("\n===== %s : file_offset(F)=0x%X  disasm base B=0x%X =====" % (label,F,B))
    if F+0x40>len(d): print("   F out of file"); return
    print("   bytes: %s" % d[F:F+16].hex())
    n=0; ok=0
    for ins in md.disasm(d[F:F+0x140], F+B):
        if ins.mnemonic=="call" and ins.op_str.startswith("0x"):
            T=int(ins.op_str,16); toff=T-B
            inrange = 0 <= toff < len(d)
            p=plaus(toff) if inrange else "OUT_OF_FILE"
            if p.startswith(("PROLOGUE","55")): ok+=1
            print("   call -> VA %08X  target_off=0x%X  %s" % (T, toff, p))
            n+=1
            if n>=7: break
    print("   => valid prologue targets: %d/%d" % (ok,n))
# probe RVA for packetEvent = 0x467520 ; VA = 0x400000 + RVA = 0x867520
test(0x867520, 0x0,       "CONVENTION 1: file_offset == VA (absolute)")
test(0x467520, 0x400000,  "CONVENTION 2: file_offset == RVA (VA-ImageBase)")
