# -*- coding: utf-8 -*-
"""追 0x927100 的返回值 —— 客户端用 cmp eax,0x27DA / cmp eax,0x6C 判"成功"。

看 0x927100 是什么函数(读哪个字段), 以及 0x27DA/0x6C 是什么。
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
                so = v - BASE
                if 0 <= so < len(b):
                    chunk = b[so:so + 70].split(b"\x00")[0]
                    if chunk and all(32 <= x < 127 for x in chunk):
                        note = '   ; "%s"' % chunk.decode("latin1")
        print("  0x%08X  %-7s %s%s" % (ins.address, ins.mnemonic, ins.op_str, note))


def main():
    b = DUMP.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    dump(b, md, 0x927100, 0x80, "0x927100 —— 返回被 cmp 的状态码")

    # 0x27DA / 0x6C 是否在字符串区有对应
    print("\n== 0x27DA / 0x6C 作为字符串/常量出现 ==")
    for pat, label in ((b"\xDA\x27", "0x27DA (LE)"), (b"11226", "11226"), (b"108", "108")):
        cnt = 0
        i = 0
        locs = []
        while cnt < 4:
            j = b.find(pat, i)
            if j < 0:
                break
            locs.append(j + BASE)
            cnt += 1
            i = j + 1
        print("  %-12s %d 处 %s" % (label, len(locs), " ".join("0x%X" % x for x in locs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
