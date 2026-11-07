# -*- coding: utf-8 -*-
"""定位 Demonware service 分派层。

思路: 客户端收到 0x86 帧后, 要把 (service, task) 映射到处理函数。
常见形态:
  A. 一串 cmp eax, <service> ; je/jne  (链式比较)
  B. 一张 {service, handler} 表

先用 A 找: 扫全 .text 里 "cmp eax, imm32" 且 imm 落在 1..200 的密集区,
特别是同一函数里连续比较多个 service 号的地方。
再把 71 单独拎出来看上下文。
"""
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000
TEXT_LO, TEXT_HI = 0x401000, 0xC00000


def main():
    b = DUMP.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    # cmp eax, imm32 = 3D xx xx xx xx
    print("== 扫 `cmp eax, imm32` 且 imm 是 service 号(1..200) ==")
    hits = []
    i = TEXT_LO - BASE
    end = min(len(b) - 5, TEXT_HI - BASE)
    while i < end:
        j = b.find(b"\x3D", i)
        if j < 0 or j >= end:
            break
        imm = struct.unpack_from("<I", b, j + 1)[0]
        if 1 <= imm <= 200:
            hits.append((j + BASE, imm))
        i = j + 1
    print("  共 %d 处" % len(hits))

    # 按地址排序, 找"连续出现"的密集区(同一函数里比较多个 service)
    hits.sort()
    clusters = []
    cur = [hits[0]] if hits else []
    for k in range(1, len(hits)):
        if hits[k][0] - hits[k - 1][0] <= 0x120:
            cur.append(hits[k])
        else:
            if len(cur) >= 3:
                clusters.append(cur)
            cur = [hits[k]]
    if len(cur) >= 3:
        clusters.append(cur)

    print("\n== 密集区(同一段代码里连续比较多个 service 号) ==")
    for c in clusters[:12]:
        vals = [str(v) for _, v in c]
        print("  0x%06X .. 0x%06X  共 %d 个: %s"
              % (c[0][0], c[-1][0], len(c), " ".join(vals[:18])))

    # 单独看 71
    print("\n== 值 == 71 的比较 ==")
    for va, imm in hits:
        if imm == 71:
            start = max(0, (va - BASE) - 24)
            code = b[start:(va - BASE) + 20]
            insns = list(md.disasm(code, start + BASE))
            txt = " | ".join("%s %s" % (x.mnemonic, x.op_str) for x in insns)
            print("  0x%08X : %s" % (va, txt[:150]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
