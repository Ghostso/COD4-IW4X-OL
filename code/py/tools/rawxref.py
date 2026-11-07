#!/usr/bin/env python3
"""用原始字节模式找字符串引用（不依赖线性反汇编）。

支持:
  68 <imm32>            push imm32
  a1 <imm32>            mov eax, [imm32]
  8b 0d/15/1d/35/3d <imm32>   mov reg, [imm32]
  8d 0d/15/1d/35/3d <imm32>   lea reg, [imm32]
  c7 05 <imm32> <val>   mov [imm32], imm32
"""
import struct
import sys


def main():
    path = sys.argv[1]
    # 目标 VA 列表
    targets = [int(x, 0) for x in sys.argv[2:]]
    b = open(path, "rb").read()

    # 节表
    e = struct.unpack_from("<I", b, 0x3C)[0]
    n = struct.unpack_from("<H", b, e + 6)[0]
    osz = struct.unpack_from("<H", b, e + 20)[0]
    opt = e + 24
    magic = struct.unpack_from("<H", b, opt)[0]
    ib = struct.unpack_from("<Q" if magic == 0x20B else "<I",
                            b, opt + (24 if magic == 0x20B else 28))[0]
    so = opt + osz
    secs = []
    for i in range(n):
        o = so + i * 40
        nm = b[o:o + 8].rstrip(b"\0").decode("latin1", "replace")
        vs, va, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        fl = struct.unpack_from("<I", b, o + 36)[0]
        secs.append((nm, ib + va, vs, rp, rs, fl))

    def off_to_va(off):
        for nm, va, vs, rp, rs, fl in secs:
            if rp <= off < rp + rs:
                return va + (off - rp), nm
        return None, None

    pats = [
        (b"\x68", 1, "push"),
        (b"\xa1", 1, "mov eax,[m]"),
        (b"\x8b\x0d", 2, "mov ecx,[m]"),
        (b"\x8b\x15", 2, "mov edx,[m]"),
        (b"\x8b\x1d", 2, "mov ebx,[m]"),
        (b"\x8b\x35", 2, "mov esi,[m]"),
        (b"\x8b\x3d", 2, "mov edi,[m]"),
        (b"\x8d\x0d", 2, "lea ecx,[m]"),
        (b"\x8d\x15", 2, "lea edx,[m]"),
        (b"\x8d\x1d", 2, "lea ebx,[m]"),
        (b"\x8d\x35", 2, "lea esi,[m]"),
        (b"\x8d\x3d", 2, "lea edi,[m]"),
    ]

    tset = set(targets)
    found = {t: [] for t in targets}
    for pre, skip, name in pats:
        start = 0
        while True:
            i = b.find(pre, start)
            if i < 0:
                break
            start = i + 1
            if i + skip + 4 > len(b):
                continue
            v = struct.unpack_from("<I", b, i + skip)[0]
            if v in tset:
                va, sec = off_to_va(i)
                found[v].append((va, sec, name, i))

    for t in targets:
        print("=== %#x  命中 %d" % (t, len(found[t])))
        for va, sec, name, off in found[t][:20]:
            print("   %#010x [%s] %-14s file_off=%#x" % (
                va if va else 0, sec, name, off))


if __name__ == "__main__":
    main()
