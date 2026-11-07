# -*- coding: utf-8 -*-
"""找订阅回调 0x4AA960 / 0x4AAA10 的**注册点**(谁把它们存进表里)。

回调是通过函数指针表调用的(所以搜不到 call)。注册点形态:
  mov [X], 0x4AA960   -> C7 05 xx xx xx xx 60 A9 4A 00
  push 0x4AA960       -> 68 60 A9 4A 00
  mov reg, 0x4AA960   -> B8/B9/BA/BB/... 60 A9 4A 00
"""
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000


def scan_refs(b, target):
    pat = struct.pack("<I", target)
    out = []
    i = 0
    while len(out) < 20:
        j = b.find(pat, i)
        if j < 0:
            break
        va = j + BASE
        if 0x401000 <= va <= 0xF00000:
            out.append(va)
        i = j + 1
    return out


def main():
    b = DUMP.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    for target, label in ((0x4AA960, "订阅回调1"), (0x4AAA10, "订阅回调2"),
                          (0x4AAB40, "发起订阅1"), (0x4AAC07, "发起订阅2")):
        refs = scan_refs(b, target)
        print("\n== %s 0x%X 的引用: %d 处 ==" % (label, target, len(refs)))
        for va in refs[:8]:
            start = max(0, (va - BASE) - 14)
            code = b[start:(va - BASE) + 8]
            insns = list(md.disasm(code, start + BASE))
            txt = " | ".join("%s %s" % (x.mnemonic, x.op_str) for x in insns[-4:])
            print("   0x%08X : %s" % (va, txt[:140]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
