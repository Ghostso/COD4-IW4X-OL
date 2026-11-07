# -*- coding: utf-8 -*-
"""TASK-034: OOB dispatcher full disassembly + branch summary (local target image)."""
import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def u32(r): return struct.unpack_from("<I",d,r)[0]
def s(r):
    e=d.find(b'\x00',r); return d[r:e].decode('latin1','replace')
print("=== OOB dispatcher RVA 0x1C05F0 .. 0x1C0740 (state gate + command dispatch) ===")
for ins in md.disasm(d[0x1C05F0:0x1C0740], 0x1C05F0):
    note=""
    if ins.mnemonic=="push" and ins.op_str.startswith("0x"):
        v=int(ins.op_str,16)
        if 0xDA0000<=v<0xE00000: note="  ; %r" % s(v-BASE)[:40]
    if ins.mnemonic=="jmp" and "[" in ins.op_str:
        note="  ; JUMP TABLE"
    print("RVA %08X  %-20s %-34s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic+" "+ins.op_str, note))
print()
print("=== jump table A @RVA 0x1C0F2C (index=state) ===")
for i in range(4): print("   [%d] -> RVA %X" % (i, u32(0x1C0F2C+i*4)-BASE))
print("=== jump table B @RVA 0x1C0F3C (index=cmd-3) ===")
for i in range(4): print("   [%d] -> RVA %X" % (i, u32(0x1C0F3C+i*4)-BASE))
print()
print("=== command handlers: first 24 insns each ===")
for tgt in (0x5C070E,0x5C0776,0x5C0E07,0x5C0EBB):
    r=tgt-BASE
    print("--- handler RVA %X ---" % r)
    n=0
    for ins in md.disasm(d[r:r+0x80], r):
        note=""
        if ins.mnemonic=="push" and ins.op_str.startswith("0x"):
            v=int(ins.op_str,16)
            if 0xDA0000<=v<0xE00000: note="  ; %r" % s(v-BASE)[:44]
        print("    RVA %08X  %-18s %s %s%s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,note))
        n+=1
        if n>=22: break
