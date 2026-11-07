#!/usr/bin/env python3
"""抽取所有 'XX 06 status 0f DWServiceStatus' 模式, 反推 [len][serviceName]。
同时抽取所有 'bind_demonware...StatusChange' 函数名与所属 controller。
这构成 本地 RE 的 DW 服务名清单 (非 ol-mod)。
"""
import re
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()
N = len(data)

print("=== 模式: [len][serviceName] 06 'status' 0f 'DWServiceStatus' ===")
needle = b"\x06status\x0fDWServiceStatus"
i = 0; rows = []
while True:
    p = data.find(needle, i)
    if p < 0: break
    i = p + 1
    # p-1 是 serviceName 的最后一个字节; 向前找 [len]
    # 尝试 len 1..32: 检查 data[p-1-L] == L 且 区间为 ascii
    svc = None
    for L in range(1, 33):
        start = p - L
        if start < 0: break
        if data[start-1] == L and all(32 <= b < 127 for b in data[start:p]):
            svc = data[start:p].decode("latin1")
            break
    rows.append((p, svc))

seen = {}
for p, svc in rows:
    seen.setdefault(svc, []).append(p)
print("不同 serviceName = %d" % len(seen))
for svc in sorted(seen, key=lambda x: (x is None, x)):
    print("  %-24r  x%d  %s" % (svc, len(seen[svc]), ["0x%X"%q for q in seen[svc][:4]]))

print("\n=== 所有 'bind_demonware*StatusChange' 函数名 ===")
i = 0; names = {}
while True:
    p = data.find(b"bind_demonware", i)
    if p < 0: break
    i = p + 1
    hi = p
    while hi < N and 32 <= data[hi] < 127: hi += 1
    s = data[p:hi].decode("latin1")
    names.setdefault(s, []).append(p)
for s in sorted(names):
    print("  %-60r x%d" % (s, len(names[s])))

print("\n=== 所有 'bind_*StatusChange' 函数名 (更宽) ===")
i = 0; names2 = {}
while True:
    p = data.find(b"bind_", i)
    if p < 0: break
    i = p + 1
    hi = p
    while hi < N and 32 <= data[hi] < 127: hi += 1
    s = data[p:hi].decode("latin1")
    if "StatusChange" in s:
        names2.setdefault(s, []).append(p)
for s in sorted(names2):
    print("  %-60r x%d" % (s, len(names2[s])))
