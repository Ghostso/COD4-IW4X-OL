# -*- coding: utf-8 -*-
"""反汇编客户端里处理 service=71 / 频道订阅的代码。

落点(上一脚本定位): 0x477297 引用字符串块 0xDB4C00
  —— 该块同时含 "ChannelSubscription" 与 "ChannelSubscriptionFail"。
目标: 看清它读哪些字段、按什么条件判成功/失败。
"""
import sys
from pathlib import Path

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000
START = 0x477250
LENGTH = 0x300

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    print("需要 capstone: pip install capstone")
    raise SystemExit(2)


def main():
    b = DUMP.read_bytes()
    off = START - BASE
    code = b[off:off + LENGTH]

    # 先把字符串块本身 dump 出来(看它到底是哪几句)
    s_off = 0xDB4C00 - BASE
    raw = b[s_off:s_off + 160]
    print("== 0xDB4C00 附近的字符串 ==")
    txt = raw.split(b"\x00")
    for t in txt[:8]:
        if t:
            print("   %r" % t.decode("latin1", "replace"))
    print()

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    print("== 反汇编 0x%X .. 0x%X ==" % (START, START + LENGTH))
    for ins in md.disasm(code, START):
        line = "  0x%08X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str)
        # 标注引用的字符串
        note = ""
        for op in ins.operands:
            try:
                v = op.imm
            except Exception:
                continue
            if 0xD00000 <= v <= 0xF00000:
                so = v - BASE
                if 0 <= so < len(b):
                    chunk = b[so:so + 60].split(b"\x00")[0]
                    if chunk and all(32 <= c < 127 for c in chunk):
                        note = '   ; "%s"' % chunk.decode("latin1")
        print(line + note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
