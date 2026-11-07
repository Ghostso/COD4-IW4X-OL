#!/usr/bin/env python3
"""UIPage/UIClick 共用 helper @file 0x240FD0 (VA 0x640FD0) 解剖.
1) 反汇编骨架: 扫 0x240FD0..+0x300 里的 `68 imm32`(push const) / `e8 rel32`(call) / `50-57`(push reg)
2) 把 push 的 imm32 当 VA 解析成串
3) 全镜像找所有 call 0x240FD0 的点 → 谁在用这个简化的"事件名+单参"路径
"""
import struct, re
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

def cstr(off, maxlen=200):
    if not (0 <= off < N): return None
    e = d.find(b"\x00", off)
    if e < 0 or e - off > maxlen: e = off + maxlen
    return d[off:e]

def va_str(v):
    s = cstr(v - VA)
    if s is None: return None
    try:
        t = s.decode("latin1")
    except Exception:
        return None
    if not t: return ""
    if all(32 <= ord(c) < 127 or c in "\t\n" for c in t):
        return t
    return None

F = 0x240FD0
print("=== 0x%06X..0x%06X 骨架 ===" % (F, F + 0x300))
i = F
end = F + 0x300
while i < end:
    b = d[i]
    if b == 0x68:  # push imm32
        v = struct.unpack_from("<I", d, i + 1)[0]
        s = va_str(v)
        print("  0x%06X  push 0x%08X  %s" % (i, v, ("-> %r" % s) if s is not None else ""))
        i += 5
    elif b == 0xE8:  # call rel32
        rel = struct.unpack_from("<i", d, i + 1)[0]
        tgt = i + 5 + rel
        print("  0x%06X  call 0x%06X (file)" % (i, tgt))
        i += 5
    elif b in (0xE9,):
        rel = struct.unpack_from("<i", d, i + 1)[0]
        print("  0x%06X  jmp  0x%06X (file)" % (i, i + 5 + rel))
        i += 5
    elif b == 0xC3:
        print("  0x%06X  ret" % i)
        i += 1
        if i > F + 0x40:
            break
    elif 0x50 <= b <= 0x57:
        print("  0x%06X  push %s" % (i, "eax ecx edx ebx esp ebp esi edi".split()[b - 0x50]))
        i += 1
    elif b == 0x8D:  # lea reg,[ebp-..]
        m = d[i:i+3]
        if m[1] in (0x45, 0x4D, 0x55, 0x5D, 0x75, 0x7D) and m[2] > 0x80:
            print("  0x%06X  lea r,[ebp-%d]" % (i, 256 - m[2]))
        i += 3 if (m[1] & 7) == 5 else 2
    elif b == 0x6A:  # push imm8
        v = d[i+1]
        print("  0x%06X  push 0x%02X" % (i, v))
        i += 2
    else:
        i += 1

print()
print("=== 全镜像 call 0x%06X 的调用点 ===" % F)
# call rel32 -> tgt F  =>  e8 <rel> where i+5+rel==F
targets = []
for i in range(0, N - 5):
    if d[i] == 0xE8:
        rel = struct.unpack_from("<i", d, i + 1)[0]
        if i + 5 + rel == F:
            targets.append(i)
print("  共 %d 处" % len(targets))
for t in targets:
    # 往回看 16 字节, 找最近的 push imm32 名字
    ctx = d[max(0, t - 24):t]
    s = ""
    for k in range(len(ctx) - 5, -1, -1):
        if ctx[k] == 0x68:
            v = struct.unpack_from("<I", ctx, k + 1)[0]
            t2 = va_str(v)
            if t2 is not None:
                s = repr(t2[:60])
                break
    print("  call@0x%06X  name=%s" % (t, s))
