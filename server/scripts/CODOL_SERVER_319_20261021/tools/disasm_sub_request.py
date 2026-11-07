# -*- coding: utf-8 -*-
"""看两个"发起订阅"函数如何组装请求 —— 这是 71/3 应答结构的镜像。

0x4AAB40: 注册回调 0x4AA960
0x4AAC07: 注册回调 0x4AAA10
两者都 call 0x4aae20 (发送)。
"""
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\RECONNECT_20261024_1445\mem\mem_000.bin")
BASE = 0x400000


def dump(b, md, start, ln, title):
    print("\n" + "=" * 76)
    print(title)
    print("=" * 76)
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
            if op.type == 2:   # imm
                pass
        print("  0x%08X  %-7s %s%s" % (ins.address, ins.mnemonic, ins.op_str, note))


def main():
    b = DUMP.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    dump(b, md, 0x4AAB00, 0xC0, "发起订阅 A  (0x4AAB00 起, 回调 0x4AA960)")
    dump(b, md, 0x4AABD0, 0xA0, "发起订阅 B  (0x4AABD0 起, 回调 0x4AAA10)")
    dump(b, md, 0x4AAE20, 0x90, "0x4AAE20 —— 两者都调的发送函数")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

