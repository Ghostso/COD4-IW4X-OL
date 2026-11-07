# -*- coding: utf-8 -*-
"""追 [obj+0x38] 的**写入点** —— 那个字段决定订阅成功/失败。

已知: 0x927100 = `mov eax,[ecx+0x38]; ret`, 被 0x4AAC7F 调用,
      返回值与 0x27DA / 0x6C 比较。

要找: 谁写 [reg+0x38]。在 32 位代码里表现为 `mov [reg+0x38], eax/imm` 等,
      机器码形如 89 4? 38 / C7 4? 38 xx xx xx xx。
      直接扫整个映像里的 "38" 位移写法太宽, 改用: 找引用了
      0x27DA / 0x6C 这两个常量的地方(它们很可能也在写入侧出现)。
"""
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000


def main():
    b = DUMP.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    print("== 找 cmp/ mov 里出现 0x27DA 或 0x6C 的地方 ==")
    for val in (0x27DA, 0x6C):
        pat = struct.pack("<I", val)
        hits = []
        i = 0
        while len(hits) < 12:
            j = b.find(pat, i)
            if j < 0:
                break
            # 只看 .text 范围(大致 0x401000 - 0xC00000)
            va = j + BASE
            if 0x401000 <= va <= 0xC00000:
                hits.append(va)
            i = j + 1
        print("\n  0x%X : %d 处" % (val, len(hits)))
        for va in hits:
            start = max(0, (va - BASE) - 12)
            code = b[start:(va - BASE) + 8]
            insns = list(md.disasm(code, start + BASE))
            txt = " | ".join("%s %s" % (x.mnemonic, x.op_str) for x in insns[-4:])
            print("     0x%08X : %s" % (va, txt[:130]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
