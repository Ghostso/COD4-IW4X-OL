#!/usr/bin/env python3
"""138: 搜索对 slot 偏移 0x25B8 等间接引用编码。
用法: s138_slotrefs.py [off_hex ...]
默认搜 25B8 (小端 B8 25 00 00)。同时搜 modrm 变体。
打印命中 VA 及其反汇编上下文。
"""
import sys
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def dis_at(va, before=0x10, after=0x18):
    f = va - VA
    start = max(0, f - before)
    code = d[start:f + after]
    for ins in md.disasm(code, VA + start):
        mark = ">>" if ins.address == va else "  "
        print("  %s 0x%08X  %-18s %s %s" % (
            mark, ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))


def scan_suffix(suffix, name):
    pat = bytes.fromhex(suffix)
    print("=" * 70)
    print("pattern %s (%s)" % (suffix, name))
    cnt = 0
    pos = 0
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        va = VA + i
        cnt += 1
        print("\n--- hit @ VA 0x%08X (file 0x%06X)" % (va, i))
        dis_at(va, 0x10, 0x14)
    print("\nTOTAL %s hits: %d" % (name, cnt))


if __name__ == "__main__":
    offs = sys.argv[1:] or ["25B8"]
    for off in offs:
        lo = off[-2:]
        hi = off[-4:-2]
        if len(off) == 4:
            base = "B8 25 00 00".replace("B8", off[2:]).replace("25", off[:2])
        # build suffix little-endian: offset u16 then 00 00
        o = int(off, 16)
        suffix = (o & 0xFF).to_bytes(1, 'little').hex() + ((o >> 8) & 0xFF).to_bytes(1, 'little').hex() + "0000"
        scan_suffix(suffix, "off=0x" + off)
