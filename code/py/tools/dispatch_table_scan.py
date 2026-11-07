#!/usr/bin/env python3
"""找 '函数指针连续数组' 及其引用 —— 用来判一段 string 表是枚举/映射表还是死数据."""
import struct, sys
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
START = int(sys.argv[1], 0)
MAXN  = int(sys.argv[2]) if len(sys.argv) > 2 else 64
def out(s): sys.stdout.write(s.encode("ascii","replace").decode("ascii")+"\n")

def is_code_ptr(v):
    f = v - VA
    return 0 <= f < N - 4

# 表项: [flags/val dword][ptr dword] 连续若干项, 最后跟 0
f = START
n = 0
while n < MAXN:
    x, y = struct.unpack_from("<II", d, f)
    if x == 0 and y == 0:
        break
    n += 1; f += 8
out("### 表 @VA 0x%06X 自然长度 %d 项, 结束于 VA 0x%06X (file 0x%06X)" % (START, n, f, f-VA))

def refs(v):
    out("--- 引用扫描 VA 0x%06X ---" % v)
    import re
    pat = struct.pack("<I", v)
    hits = [m.start() for m in re.finditer(re.escape(pat), d)]
    out("  立即数: %s" % (" ".join("0x%06X" % h for h in hits[:16]) if hits else "无"))
    return hits

for k, label in ((0, "表首"), (n-1, "表尾"), (n, "结束符")):
    v = START + k*8
    out("")
    out("== %s (第 %d 项) ==" % (label, k))
    refs(v)
