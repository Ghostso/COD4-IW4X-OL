# -*- coding: utf-8 -*-
"""P0/P1 通用: 扫描某个 disp32 在镜像里的全部访问点，并判定读/写。

判定规则（基于反汇编出的操作数）：
  - 指令写目标内存 (operands[0].type == MEM) -> WRITE
  - 否则若 MEM 出现在任何操作数 -> READ
  - cmp/test/sub/add 等对内存的操作需要区分，用 mnemonics 白名单辅助
"""
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM

IMG = (r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline"
       r"\_dyn100_run_20260925_182324\live\image_best.bin")
img = open(IMG, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

WRITE_MNEM = {
    "mov", "movzx", "movsx", "movsxd", "lea", "xchg", "or", "and", "xor",
    "add", "sub", "inc", "dec", "not", "neg", "shl", "shr", "sar", "setne",
    "sete", "setz", "setnz", "movups", "movaps", "movups", "stosd",
}


def classify(ins):
    """返回 (kind, detail)。kind ∈ {WRITE, READWRITE, READ, OTHER}"""
    if not ins.operands:
        return "OTHER", ""
    mem_write = False
    mem_read = False
    for idx, op in enumerate(ins.operands):
        if op.type != X86_OP_MEM:
            continue
        if idx == 0 and ins.mnemonic in WRITE_MNEM:
            mem_write = True
        else:
            mem_read = True
    if mem_write and mem_read:
        return "READWRITE", ins.op_str
    if mem_write:
        return "WRITE", ins.op_str
    if mem_read:
        return "READ", ins.op_str
    return "OTHER", ins.op_str


def scan(disp, label, limit=None):
    pat = struct.pack("<I", disp)
    found = []
    s = 0
    while True:
        i = img.find(pat, s)
        if i < 0:
            break
        found.append(i)
        s = i + 1
    print("=" * 78)
    print("disp=0x%X  (%s)   命中 %d 处" % (disp, label, len(found)))
    print("=" * 78)
    n = 0
    for i in found:
        va = 0x400000 + i
        # 尝试从 -10 字节开始解码，找到覆盖该 disp 的那条指令
        best = None
        for back in range(2, 16):
            st = va - back
            code = img[st - 0x400000: st - 0x400000 + 24]
            ins = next(md.disasm(code, st), None)
            if ins and ins.address <= va < ins.address + ins.size:
                best = ins
                break
        if best is None:
            print("  [  ??  ] 0x%08X  (无法对齐解码)" % va)
            continue
        kind, detail = classify(best)
        print("  [%-9s] 0x%08X  %-10s %s" % (kind, best.address,
                                             best.mnemonic, best.op_str))
        n += 1
        if limit and n >= limit:
            break
    print()


if __name__ == "__main__":
    # P0: 守卫 +0x278
    scan(0x278, "guard +0x278")
    # P1: reservation array
    scan(0x75D8, "reservation array base")
    scan(0xE360, "reservation index")
    scan(0x238, "stride 0x238")
