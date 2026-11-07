# -*- coding: utf-8 -*-
"""反汇编 0x4AAB00 附近 —— 这里写 0xC1B8020/0xC1B8038(订阅错误状态)。

目标: 看清它从哪个字段读错误码, 从而知道应答里哪个位置代表"失败"。
"""
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000
START = 0x4AAC00
LN = 0x100


def main():
    b = DUMP.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    code = b[START - BASE:START - BASE + LN]
    print("== 0x%X .. 0x%X ==" % (START, START + LN))
    for ins in md.disasm(code, START):
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
                    if chunk and all(32 <= x < 127 for x in chunk):
                        note = '   ; "%s"' % chunk.decode("latin1")
        print("  0x%08X  %-7s %s%s" % (ins.address, ins.mnemonic, ins.op_str, note))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


