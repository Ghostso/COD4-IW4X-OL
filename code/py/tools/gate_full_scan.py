#!/usr/bin/env python3
"""全镜像扫描 [0x849ba30] 的所有访问，按指令形态分类。"""
import struct
from collections import Counter

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000
T = 0x0849BA30


def main():
    b = open(DUMP, "rb").read()
    pat = struct.pack("<I", T)
    print("镜像大小 %#x" % len(b))

    hits = []
    k = 0
    while True:
        i = b.find(pat, k)
        if i < 0:
            break
        hits.append(i)
        k = i + 1

    print("地址出现 %d 处\n" % len(hits))

    WRITE = {(0xA3,): "mov [T],eax",
             (0xC7, 0x05): "mov [T],imm32",
             (0x89, 0x0D): "mov [T],ecx",
             (0x89, 0x15): "mov [T],edx",
             (0x89, 0x1D): "mov [T],ebx",
             (0x89, 0x35): "mov [T],esi",
             (0x89, 0x3D): "mov [T],edi"}

    writes = []
    kinds = Counter()
    for i in hits:
        # 检查前 1 或 2 字节
        p1 = b[i - 1] if i >= 1 else -1
        p2 = b[i - 2] if i >= 2 else -1
        form = None
        if (p1,) in WRITE:
            form = WRITE[(p1,)]
        elif (p2, p1) in WRITE:
            form = WRITE[(p2, p1)]
        if form:
            writes.append((BASE + i, form, b[i - 8:i + 8].hex(" ")))
            kinds[form] += 1

    print("=== 写入点 (%d) ===" % len(writes))
    for va, form, ctx in writes:
        print("  %#010x  %-18s  ctx=%s" % (va, form, ctx))

    print("\n=== 读/比较 (%d) ===" % (len(hits) - len(writes)))
    rc = Counter()
    for i in hits:
        p1 = b[i - 1] if i >= 1 else -1
        p2 = b[i - 2] if i >= 2 else -1
        if (p1,) in WRITE or (p2, p1) in WRITE:
            continue
        rc[("%02x %02x" % (p2, p1))] += 1
    for k2, v in rc.most_common(12):
        print("  前导 %s : %d" % (k2, v))


if __name__ == "__main__":
    main()
