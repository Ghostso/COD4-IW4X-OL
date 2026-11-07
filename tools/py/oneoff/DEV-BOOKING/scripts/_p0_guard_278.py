# -*- coding: utf-8 -*-
"""P0: 只看匹配模块范围(0x62C000-0x63A000)内 [obj+0x278] 的读写，区分 CLEAR / REAL。"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = (r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline"
       r"\_dyn100_run_20260925_182324\live\image_best.bin")
img = open(IMG, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

LO, HI = 0x62C000, 0x63A000


def find_ins(va):
    for back in range(2, 16):
        st = va - back
        if st < 0x400000:
            continue
        ins = next(md.disasm(img[st - 0x400000: st - 0x400000 + 24], st), None)
        if ins and ins.address <= va < ins.address + ins.size:
            return ins
    return None


def main():
    pat = struct.pack("<I", 0x278)
    s = 0
    items = []
    while True:
        i = img.find(pat, s)
        if i < 0:
            break
        va = 0x400000 + i
        if LO <= va < HI:
            ins = find_ins(va)
            if ins:
                items.append(ins)
        s = i + 1
    print("匹配模块范围内 [obj+0x278] 访问 %d 条" % len(items))
    print()
    print("%-10s %-12s %-8s %s" % ("KIND", "ADDR", "SIZE", "INSN"))
    print("-" * 78)
    for ins in items:
        op0 = ins.operands[0] if ins.operands else None
        memwrite = bool(op0 and op0.type == 3)
        size = {1: "byte", 2: "word", 4: "dword"}.get(ins.op_str.count("ptr") and 0, "")
        if "byte ptr" in ins.op_str:
            size = "byte"
        elif "word ptr" in ins.op_str:
            size = "word"
        elif "dword ptr" in ins.op_str:
            size = "dword"
        kind = "READ"
        if memwrite and ins.mnemonic in ("mov", "or", "and", "xor", "add", "sub"):
            kind = "WRITE"
        # 判定是否为清零
        if kind == "WRITE":
            tail = ins.op_str.split(",")[-1].strip()
            if tail in ("0", "0x0"):
                kind = "CLEAR"
            else:
                kind = "REAL_W"
        print("%-10s %-12s %-8s %s %s"
              % (kind, "0x%08X" % ins.address, size, ins.mnemonic, ins.op_str))


if __name__ == "__main__":
    main()
