#!/usr/bin/env python3
"""精确版：对 dwroom_serializers 报的每个 vtable 地址 V，
在全镜像里找 `mov dword [reg], V` 的字节形态，再在其前后找 `mov [reg+4], imm`。

vfptr 值 = V（dwroom_serializers 的 "vtable" 列直接就是 vfptr 指向的
第一个 dword 的地址 —— 实测 0xdc759c + 4 = 0xdc75a0 才是构造函数里装填的值）。

因此对每个类，同时尝试 V 和 V+4。
"""
import re
import struct
import subprocess
import sys

DUMP = ("CODOL_LOCAL_ENGINE_CHAIN_20261019/logs/"
        "ROUND2_STATIC_DUMP_20261019_203103/client_runtime.bin")
BASE = 0x400000
RMAP = {0: "eax", 1: "ecx", 2: "edx", 3: "ebx", 5: "ebp", 6: "esi", 7: "edi"}


def classes():
    out = subprocess.run(
        [sys.executable, "-I", "tools/dwroom_serializers.py"],
        capture_output=True, text=True, encoding="latin1").stdout
    r = []
    for line in out.splitlines():
        m = re.match(r"^(\S+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+"
                     r"(0x[0-9a-f]+)\s+(0x[0-9a-f]+)", line)
        if m:
            r.append((m.group(1), int(m.group(2), 16), int(m.group(4), 16)))
    return r


def find_mov_reg_imm(b, imm):
    """返回 [(va, rm)] —— mov dword [reg], imm32 (mod=00)"""
    hits = []
    pat = struct.pack("<I", imm)
    k = 0
    while True:
        i = b.find(pat, k)
        if i < 0:
            break
        k = i + 1
        if i < 2:
            continue
        if b[i - 2] != 0xC7:
            continue
        m = b[i - 1]
        if (m & 0xF8) != 0x00:
            continue
        rm = m & 7
        if rm == 5:
            continue
        hits.append((BASE + i - 2, rm))
    return hits


def find_type_near(b, va, rm):
    """从 va 起前后 0x80 找 [same reg +4] = imm（C7 4x 04 imm32 或 C6 4x 04 imm8）"""
    lo = max(0, va - BASE - 0x80)
    hi = min(len(b), va - BASE + 0x80 + 8)
    best = None
    for i in range(lo, hi - 7):
        m = b[i + 1]
        if b[i] == 0xC7 and (m & 0xF8) == 0x40 and (m & 7) == rm \
                and m != 0x44 and b[i + 2] == 0x04:
            imm = struct.unpack_from("<I", b, i + 3)[0]
            if 0 <= imm <= 0xFF:
                d = abs(BASE + i - va)
                if best is None or d < best[0]:
                    best = (d, imm, 4)
        elif b[i] == 0xC6 and (m & 0xF8) == 0x40 and (m & 7) == rm \
                and m != 0x44 and b[i + 2] == 0x04:
            imm = b[i + 3]
            d = abs(BASE + i - va)
            if best is None or d < best[0]:
                best = (d, imm, 1)
    return best


def main():
    b = open(DUMP, "rb").read()
    cls = classes()
    print("%-46s %-8s %-10s %s" % ("class", "vfptr", "类型号", "ctor"))
    rows = []
    for name, col, ser in cls:
        got = None
        ctor = None
        for cand in (col + 4, col):
            hits = find_mov_reg_imm(b, cand)
            if not hits:
                continue
            for va, rm in hits:
                t = find_type_near(b, va, rm)
                if t:
                    got = t[1]
                    ctor = va
                    break
            if got is not None:
                break
        rows.append((name, col + 4, got, ctor))
        print("%-46s %#010x %-10s %s" % (
            name, col + 4,
            str(got) if got is not None else "?",
            hex(ctor) if ctor else "-"))
    ok = sum(1 for r in rows if r[2] is not None)
    print("\n命中 %d / %d" % (ok, len(cls)))
    with open("_byte_papers/msgtype_table.txt", "w", encoding="utf-8") as f:
        f.write("class\tvfptr\ttype\tctor\n")
        for name, vf, t, c in rows:
            f.write("%s\t%#x\t%s\t%s\n" % (
                name, vf, t if t is not None else "", hex(c) if c else ""))


if __name__ == "__main__":
    main()
