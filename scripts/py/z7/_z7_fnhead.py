img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
o = 0x803EE4 - BASE
# walk back for "cc cc" padding then function start
seg = d[o-0x800:o]
i = seg.rfind(b"\xcc\xcc\xcc\xcc")
print("padding ends at VA:", hex(0x803EE4-0x800+i+4) if i>=0 else "none")
if i>=0:
    fs = 0x803EE4-0x800+i+4
    print("function start likely:", hex(fs))
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    n=0
    for ins in md.disasm(d[fs-BASE:fs-BASE+0x60], fs):
        print("0x%08X  %-14s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        n+=1
        if n>12: break
