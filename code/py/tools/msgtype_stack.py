#!/usr/bin/env python3
"""★ 真正的类型号注册点：栈上消息头结构。

形态（实测 0x62b6d0 / 0x6300fe / 0x635b51）:
    mov dword ptr [ebp - 0x10], <vfptr>     ; C7 45 F0 <imm32>   (disp8)
    mov dword ptr [ebp - 0x0c], <typeNo>    ; C7 45 F4 <imm32>   (disp8 = 上者+4)

因为 vfptr 在对象 +0x00，类型号在 +0x04。

扫描规则：
  对每个 "C7 45 <disp8=d> <imm32=v>"，若 v 属于 dwRoom 位流类 vfptr 集合，
  则找 disp8 == d+4 的 "C7 45 <d+4> <imm32=t>"，t 即类型号。

也处理 disp32 形式 (C7 85 <disp32> <imm32>)。
用法: python -I tools/msgtype_stack.py
"""
import re
import struct
import subprocess
import sys

DUMP = ("CODOL_LOCAL_ENGINE_CHAIN_20261019/logs/"
        "ROUND2_STATIC_DUMP_20261019_203103/client_runtime.bin")
BASE = 0x400000


def classes():
    out = subprocess.run(
        [sys.executable, "-I", "tools/dwroom_serializers.py"],
        capture_output=True, text=True, encoding="latin1").stdout
    r = []
    for line in out.splitlines():
        m = re.match(r"^(\S+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+"
                     r"(0x[0-9a-f]+)\s+(0x[0-9a-f]+)", line)
        if m:
            r.append((m.group(1), int(m.group(2), 16)))
    return r


def main():
    b = open(DUMP, "rb").read()
    cls = classes()
    vf2name = {}
    for name, col in cls:
        vf2name[col + 4] = name
        vf2name[col] = name      # 两种都试
    vfset = set(vf2name)

    # 收集所有 mov dword [ebp+disp8], imm32   => C7 45 xx imm32
    movs8 = []   # (off, disp8_signed, imm)
    for i in range(len(b) - 7):
        if b[i] == 0xC7 and b[i + 1] == 0x45:
            d = struct.unpack_from("<b", b, i + 2)[0]
            imm = struct.unpack_from("<I", b, i + 3)[0]
            movs8.append((i, d, imm))
    # mov dword [ebp+disp32], imm32  => C7 85 disp32 imm32
    movs32 = []
    for i in range(len(b) - 10):
        if b[i] == 0xC7 and b[i + 1] == 0x85:
            d = struct.unpack_from("<i", b, i + 2)[0]
            imm = struct.unpack_from("<I", b, i + 6)[0]
            movs32.append((i, d, imm))

    print("C7 45 (disp8) 共 %d；C7 85 (disp32) 共 %d" % (
        len(movs8), len(movs32)))
    hits = []
    for lst, width in ((movs8, 8), (movs32, 32)):
        for i, d, imm in lst:
            if imm not in vfset:
                continue
            want = d + 4
            for j, d2, imm2 in lst:
                if d2 != want or abs(j - i) > 0x40:
                    continue
                hits.append((BASE + i, imm, imm2, d))
                break
    print("\n=== 栈上消息头 -> 类型号 ===")
    res = {}
    for va, vf, typ, d in hits:
        name = vf2name.get(vf, "?")
        if name not in res:
            res[name] = (typ, va, vf)
        print("%#010x  vfptr=%#x(%s)  [obj+4]=%d (0x%02x)" % (
            va, vf, name, typ, typ))
    print("\n=== 每类（取首个）===")
    for name, col in cls:
        r = res.get(name)
        print("%-46s 类型号 = %s" % (
            name, ("%d (0x%02x) @%#x" % (r[0], r[0], r[1]))
            if r else "?"))
    print("\n命中 %d / %d 类" % (sum(1 for n, _ in cls if n in res), len(cls)))
    with open("_byte_papers/msgtype_stack.txt", "w", encoding="utf-8") as f:
        f.write("class\ttype\tvfptr\tsite\n")
        for name, col in cls:
            r = res.get(name)
            f.write("%s\t%s\t%#x\t%s\n" % (
                name, r[0] if r else "", col + 4,
                hex(r[1]) if r else ""))


if __name__ == "__main__":
    main()
