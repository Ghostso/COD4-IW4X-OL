#!/usr/bin/env python3
"""B7: 全镜像扫描所有 `.?A` 局域类 mangled 名, 抽 `?<n>` 与终止符, 看是否与 62 例一致."""
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def cstr_at(f, maxlen=400):
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    try:
        return s.decode("latin1")
    except Exception:
        return None


# 任意 `.?A` 起点
pat = re.compile(rb"\.\?A([A-Za-z0-9_?]+?)@")
found = []
for m in pat.finditer(d):
    s = cstr_at(m.start())
    if s is None:
        continue
    found.append((VA + m.start(), s))

print("`.?A...@` 串总数: %d" % len(found))

# 看第二个 @ 之后是否紧接 ?<n>
NUM = re.compile(r"^\.\?A(V|U|T|W4)([A-Za-z0-9_]+?)@\?([0-9A-P]+)(@?)")
forms = Counter()
rows = []
plain = []
for va, s in found:
    mm = NUM.match(s)
    if mm:
        typ, name, num, sep = mm.groups()
        forms["有@(B)" if sep else "无@(A)"] += 1
        rows.append((va, typ, name, num, sep, s))
    else:
        plain.append((va, s))

print("匹配 `.?A<type><name>@?<n>(@?)` : %d ; 其他 .?A 串: %d" % (len(rows), len(plain)))
print("形态计数:", dict(forms))
print()

# 数字->十进制
DIG = {chr(ord("0") + i): i for i in range(10)}
DIG.update({chr(ord("A") + i): 10 + i for i in range(16)})


def dec(s):
    v = 0
    for ch in s:
        v = v * 26 + DIG[ch]
    return v


print("=== 匹配到的 %d 条 (按 数值) ===" % len(rows))
for va, typ, name, num, sep, s in sorted(rows, key=lambda r: dec(r[3])):
    tag = "B" if sep else "A"
    print("  n=%-4d [%s] %-3s %-40s 0x%08X" % (dec(num), tag, sep or "-", name, va))
print()

print("=== 其他 .?A 串 (%d) (前 60) ===" % len(plain))
for va, s in plain[:60]:
    print("  0x%08X  %s" % (va, s))
