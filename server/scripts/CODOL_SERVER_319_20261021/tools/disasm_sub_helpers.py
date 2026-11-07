# -*- coding: utf-8 -*-
"""换思路: 不扫 +0x38 写入, 而是**看应答是怎么被解析成对象的**。

线索: 0x4AA6CC `mov esi,[ebx+0x28]` —— esi 是"应答对象"。
      0x4AA6DE `call 0xb83d70` —— 拿它做什么?
      0x4AA6E8 `call 0x477140` —— 打印?

先反汇编 0x477140 和 0xb83d70, 看清这两个 helper 干什么。
再找 ebx(外层对象) 是谁、+0x28 在哪赋值。
"""
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000


def dump(b, md, start, ln, title):
    print("\n" + "=" * 74)
    print("%s  0x%X" % (title, start))
    print("=" * 74)
    code = b[start - BASE:start - BASE + ln]
    for ins in md.disasm(code, start):
        note = ""
        for op in ins.operands:
            try:
                v = op.imm
            except Exception:
                continue
            if 0xD00000 <= v <= 0xF00000:
                s2 = v - BASE
                if 0 <= s2 < len(b):
                    ch = b[s2:s2 + 70].split(b"\x00")[0]
                    if ch and all(32 <= x < 127 for x in ch):
                        note = '   ; "%s"' % ch.decode("latin1")
        print("  0x%08X  %-7s %s%s" % (ins.address, ins.mnemonic, ins.op_str, note))


def main():
    b = DUMP.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    dump(b, md, 0x477140, 0x90, "0x477140 —— 订阅路径里的 helper")
    dump(b, md, 0xB83D70, 0x60, "0xB83D70 —— 另一个 helper")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
