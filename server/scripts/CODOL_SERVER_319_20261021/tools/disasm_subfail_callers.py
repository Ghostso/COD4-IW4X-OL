# -*- coding: utf-8 -*-
"""反汇编订阅判定的调用点, 看清"成功"走哪条路、"失败"走哪条路。"""
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000

SPOTS = [
    ("调用点A", 0x4AA950, 0x120),
    ("调用点B", 0x4AA9E0, 0x120),
    ("调用点C", 0x5D2DC0, 0x140),
]


def main():
    b = DUMP.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    for name, start, ln in SPOTS:
        off = start - BASE
        code = b[off:off + ln]
        print("\n" + "=" * 74)
        print("%s  0x%X .. 0x%X" % (name, start, start + ln))
        print("=" * 74)
        for ins in md.disasm(code, start):
            note = ""
            for op in ins.operands:
                try:
                    v = op.imm
                except Exception:
                    continue
                if 0xD00000 <= v <= 0xF00000:
                    so = v - BASE
                    if 0 <= so < len(b):
                        chunk = b[so:so + 70].split(b"\x00")[0]
                        if chunk and all(32 <= c < 127 for c in chunk):
                            note = '   ; "%s"' % chunk.decode("latin1")
            print("  0x%08X  %-7s %s%s" % (ins.address, ins.mnemonic, ins.op_str, note))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
