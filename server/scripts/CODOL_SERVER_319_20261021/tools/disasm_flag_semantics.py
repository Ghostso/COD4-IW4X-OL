# -*- coding: utf-8 -*-
"""看清 0x82C4AF4 的语义 + 四个状态码的落点。

0x4AABDB: cmp byte [0x82c4af4],0 ; je 0x4aac07(发起订阅)
0x4AB4EC: cmp byte [0x82c4af4],0 ; je 0x4ab517
0x4AB4FF: mov byte [0x82c4af4], bl
"""
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000


def dump(b, md, start, ln, title):
    print("\n" + "=" * 74)
    print(title)
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
    dump(b, md, 0x4AB4C0, 0x80, "0x4AB4C0 —— 0x82c4af4 的第二处读")
    dump(b, md, 0x5D2DC0, 0x70, "0x5D2DC0 —— 0x82c4af4 的第三处读")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
