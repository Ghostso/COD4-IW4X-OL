# -*- coding: utf-8 -*-
"""TASK-035: what values are WRITTEN into the client state global 0x76446B0?"""
import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
print("== the 5 'mov dword [0x76446B0], imm32' write sites ==")
for rva in (0x70467,0x1BE90A,0x1BEA8B,0x37C343,0x413D34):
    b=d[rva:rva+10]
    imm=struct.unpack_from("<I",b,6)[0]
    print("  RVA %08X : %s  -> imm32 = %d (0x%X)" % (rva,b.hex(),imm,imm))
print()
print("== context around each write (8 instructions before, 3 after) ==")
for rva in (0x70467,0x1BE90A,0x1BEA8B,0x37C343,0x413D34):
    print("--- near RVA %08X ---" % rva)
    for ins in md.disasm(d[rva-0x30:rva+0x14], rva-0x30):
        mark = "  <<< WRITE" if ins.address==rva else ""
        print("    RVA %08X  %-18s %s %s%s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,mark))
