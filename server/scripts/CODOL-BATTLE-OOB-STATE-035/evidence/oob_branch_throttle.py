# -*- coding: utf-8 -*-
"""TASK-035: throttle branch exact evidence (target RVAs)."""
import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
print("== throttle block 0x1C0693..0x1C06F5 ==")
for ins in md.disasm(d[0x1C0693:0x1C06F5],0x1C0693):
    note=""
    if ins.address in (0x1C06B3,0x1C06B8,0x1C06C9,0x1C06D3,0x1C06D9,0x1C06E9,0x1C06F2):
        note="   <<< KEY"
    print("  RVA %08X  %-20s %s %s%s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,note))
print()
print("== exact imm encodings ==")
for rva,lab,ln,off in [(0x1C06B3,"cmp eax, 0xBB8 (3000)",6,2),
                       (0x1C06C9,"cmp ecx, 0x64 (100)",3,1),
                       (0x1C06D3,"cmp ecx, 0x1F4 (500)",6,2)]:
    b=d[rva:rva+ln]
    import struct
    imm = b[off] if (b[0] in (0x83,0xC6) ) else struct.unpack_from("<I",b,off)[0]
    print("  %-24s @RVA %06X  bytes=%s  imm=%d (0x%X)" % (lab,rva,b.hex(),imm,imm))
