# -*- coding: utf-8 -*-
"""彻底搞清 0x82C4AF4 的方向 + 四个状态码的含义。

已知:
  0x4AAA10 回调: 成功 -> al=1 -> [0x82c4af4]=1
  0x4AA6F6 段:  状态码命中 {0x6C,0x27DA,0x4AA2,0x27D8} -> [0x82c4af4]=0

⇒ 这四个码 = "失败/非成功"类, 而不是成功。
要确认: 0x82c4af4 读的地方怎么用(1=成功 还是 1=失败)。
"""
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import struct

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000


def main():
    b = DUMP.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    pat = struct.pack("<I", 0x82C4AF4)
    print("== 所有引用 0x82C4AF4 的指令 ==")
    hits = []
    i = 0
    while len(hits) < 25:
        j = b.find(pat, i)
        if j < 0:
            break
        if 0x401000 <= j + BASE <= 0xC00000:
            hits.append(j + BASE)
        i = j + 1
    for va in hits:
        start = max(0, (va - BASE) - 10)
        code = b[start:(va - BASE) + 8]
        insns = list(md.disasm(code, start + BASE))
        txt = " | ".join("%s %s" % (x.mnemonic, x.op_str) for x in insns[-3:])
        print("  0x%08X : %s" % (va, txt[:130]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
