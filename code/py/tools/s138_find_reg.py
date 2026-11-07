#!/usr/bin/env python3
"""s138_find_reg: 找 (svc=6, task=5) 注册/发送模式:
  A) 序列 '6a 05 6a 06' 或 '6a 06 6a 05' 周边 40 字节内有 push 代码指针 或 call
  B) 找 'push 0x14' 且在 ±48 字节内有两个 0x68(push imm32) 且 imm 落在 .text
"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000, 0x401000 + 0x8a689a


def cstr(va, ml=80):
    o = va - VA
    if not (0 <= o < N - 1): return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 3: return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


print("=== A: 'push 5; push 6' / 'push 6; push 5' (±48B 有 call 或 push 代码指针) ===")
for i in range(TL - VA, TH - VA - 8):
    if d[i:i+2] in (b"\x6a\x05\x6a\x06", b"\x6a\x06\x6a\x05"):
        lo = i - 24; hi = i + 48
        seg = d[max(0, lo):hi]
        has_call = b"\xe8" in seg
        # collect nearby push codeptr
        ptrs = []
        for k in range(max(0, lo), min(N - 5, hi)):
            if d[k] == 0x68:
                v = struct.unpack_from("<I", d, k + 1)[0]
                if TL <= v < TH:
                    ptrs.append((VA + k, v, cstr(v)))
        if has_call or ptrs:
            print("  @VA 0x%08X seq=%s call=%s ptrs=%s" % (
                VA + i, d[i:i+2].hex(), has_call,
                [(hex(a), hex(v), s) for a, v, s in ptrs]))

print("\n=== B: push 0x14 且 ±64B 内有两个 push 代码指针 ===")
n = 0
for i in range(TL - VA, TH - VA - 2):
    if d[i] == 0x6A and d[i+1] == 0x14:
        lo = i - 64; hi = i + 64
        ptrs = []
        for k in range(max(0, lo), min(N - 5, hi)):
            if d[k] == 0x68:
                v = struct.unpack_from("<I", d, k + 1)[0]
                if TL <= v < TH:
                    ptrs.append((VA + k, v, cstr(v)))
        if len(ptrs) >= 2:
            print("  @VA 0x%08X ptrs=%s" % (VA + i, [(hex(a), hex(v), s) for a, v, s in ptrs]))
            n += 1
            if n > 40: break
