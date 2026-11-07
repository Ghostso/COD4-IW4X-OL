# -*- coding: utf-8 -*-
"""在我们自己的客户端里找 Demonware service 分发表。

思路: 客户端要把 service id(如 71、102)映射到处理函数, 通常是一张
  {service, handler} 表, 或一串 cmp。找 71 / 102 这两个值的比较指令,
  以及"同一个函数里连续比较多个 service 号"的地方。
"""
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000


def main():
    b = DUMP.read_bytes()
    print("转储 %.1f MB" % (len(b) / 1048576))

    # 找 0xC1B8008 / 0xC1B8020 / 0xC1B8038 这些"错误状态全局"的引用,
    # 写它们的地方 = 解析应答的地方。
    targets = [0xC1B8008, 0xC1B8020, 0xC1B8038]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    print("\n== 引用错误状态全局的指令(前 40 处) ==")
    for t in targets:
        pat = struct.pack("<I", t)
        cnt = 0
        i = 0
        while cnt < 14:
            j = b.find(pat, i)
            if j < 0:
                break
            # 该位置前 1-2 字节通常是 modrm; 把附近 16 字节反汇编
            start = max(0, j - 8)
            code = b[start:j + 12]
            insns = list(md.disasm(code, start + BASE))
            txt = " | ".join("%s %s" % (x.mnemonic, x.op_str) for x in insns)
            print("  0x%08X  (ref 0x%X): %s" % (j + BASE, t, txt[:120]))
            cnt += 1
            i = j + 1
        print("  ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
