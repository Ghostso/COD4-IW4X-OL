# -*- coding: utf-8 -*-
"""139t: 找 0xB80D90 的调用者，其每个调用点前面的 push imm32 就是服务名，
push imm8/imm32 的另一参数就是类型号。"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = open(r"E:\codol_re\client_image_20261027.bin", "rb").read()
VA = 0x400000
N = len(d)

def callers(t):
    out = []
    for i in range(N - 5):
        if d[i] == 0xE8 and (i + 5 + struct.unpack_from("<i", d, i + 1)[0] + VA) == t:
            out.append(i + VA)
    return out

def cstr(va, n=32):
    o = va - VA
    if not (0 <= o < N - 1):
        return None
    e = d.find(b"\0", o, o + n)
    if e < 0:
        return None
    s = d[o:e]
    if len(s) >= 2 and all(32 <= b < 127 for b in s):
        return s.decode()
    return None

cs = callers(0xB80D90)
print(f"0xB80D90 调用者 {len(cs)}: {[hex(x) for x in cs][:80]}")
print()
for c in cs:
    # 往前扫 0x40 字节找 push imm32 / push imm8
    args = []
    for i in range(c - 0x40, c):
        if i < VA:
            continue
        b = d[i - VA]
        if b == 0x68:
            imm = struct.unpack_from("<I", d, i + 1 - VA)[0]
            s = cstr(imm)
            args.append((i, "imm32", imm, s))
        elif b == 0x6A:
            args.append((i, "imm8", d[i + 1 - VA], None))
    desc = []
    for i, kind, v, s in args:
        desc.append(f"{kind}=0x{v:X}" + (f"<{s}>" if s else ""))
    print(f"0x{c:08X}: " + "  ".join(desc))
