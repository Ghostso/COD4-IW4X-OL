# -*- coding: utf-8 -*-
"""看 0x4AA704 和 0x4ABC3B 两处 0x27DA 比较的上下文。

0x4AA704 与订阅回调在同一函数区, 0x4ABC3B 前面刚 mov eax, 0xdb6fc4(字符串)。
"""
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000

SPOTS = [("0x4AA6C0 起", 0x4AA6C0, 0x90),
         ("0x4ABC00 起", 0x4ABC00, 0x90)]


def main():
    b = DUMP.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    # 先看 0xdb6fc4 是什么字符串
    so = 0xDB6FC4 - BASE
    raw = b[so:so + 80].split(b"\x00")[0]
    print("0xDB6FC4 处的字符串: %r" % raw.decode("latin1", "replace"))
    print()

    for name, start, ln in SPOTS:
        print("=" * 74)
        print(name)
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
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
