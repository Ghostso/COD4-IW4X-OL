#!/usr/bin/env python3
"""从解出的字符串表抽取 Demonware 服务目录: 'Xxx::taskN' / 'Xxx::method' 形态。
这是 本地逆向 证据 (二进制字符串), 权威高于 ol-mod。
"""
import re, collections
P = r"D:\BaiduNetdiskDownload\使命召唤OL\_LEARN_TESTOL_DELIVERY2\decoded\str-Alwaysoffline.txt"
lines = open(P, "r", encoding="utf-8", errors="replace").read().splitlines()
print("总行数:", len(lines))

pat = re.compile(r"^([A-Za-z][A-Za-z0-9_]*?)(2?)::([A-Za-z0-9_]+)$")
svc = collections.defaultdict(set)
other = []
for ln in lines:
    m = pat.match(ln.strip())
    if m:
        name, gen, meth = m.group(1), m.group(2), m.group(3)
        svc[name + gen].add(meth)
    elif "::" in ln and len(ln) < 60:
        other.append(ln.strip())

print("\n=== 形如 'Service::method' 的服务 (%d 个服务名) ===" % len(svc))
for name in sorted(svc):
    meths = sorted(svc[name])
    print("  %-22s (%d) %s" % (name, len(meths), meths[:14]))

print("\n=== 其它含 '::' 的短串 (前80) ===")
for s in other[:80]:
    print("   ", s)
