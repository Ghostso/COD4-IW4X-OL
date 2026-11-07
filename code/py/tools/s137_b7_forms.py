#!/usr/bin/env python3
"""B7: 两种 mangled 形态的 SF_Handler 全量导出 + 分析."""
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

# 更宽松: 直接匹配 .?AU<Name>_SF_Handler@ 然后取到该字符串结束
HEAD = re.compile(rb"\.\?AU([A-Za-z0-9_]+)_SF_Handler@")


def cstr(f, maxlen=400):
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    return d[f:e].decode("latin1")


DIG = {chr(ord("0") + i): i for i in range(10)}
DIG.update({chr(ord("A") + i): 10 + i for i in range(16)})


def dec(s):
    v = 0
    for ch in s:
        v = v * 26 + DIG[ch]
    return v


rows = []
for m in HEAD.finditer(d):
    s = cstr(m.start())
    if s is None:
        continue
    rows.append((VA + m.start(), m.group(1).decode("latin1"), s))

print("total _SF_Handler mangled strings: %d" % len(rows))
print()

# 解析每个: 形如 .?AU<Name>_SF_Handler@?<ORD>(@)??Init@UiCpp<View>@@...
PARSE = re.compile(
    r"^\.\?AU([A-Za-z0-9_]+)_SF_Handler@\?([0-9A-Z]+)(@?)\?\?Init@(UiCpp[A-Za-z0-9_]+)@@")
entries = []
bad = []
for va, h, s in rows:
    mm = PARSE.match(s)
    if not mm:
        bad.append((va, s))
        continue
    h2, ords, at, view = mm.group(1), mm.group(2), mm.group(3), mm.group(4)
    entries.append({
        "va": va, "name": h2, "ords": ords, "at": at, "view": view,
        "n": dec(ords), "form": "B(有@)" if at else "A(无@)", "s": s})

print("parsed: %d ; unparsed: %d" % (len(entries), len(bad)))
for va, s in bad:
    print("   UNPARSED 0x%08X  %s" % (va, s))
print()

a = [e for e in entries if e["form"] == "A(无@)"]
b = [e for e in entries if e["form"] == "B(有@)"]
print("=== 形态统计 ===")
print("A(无@ ...?<n>??Init...): %d" % len(a))
print("B(有@ ...?<n>@??Init...): %d" % len(b))
for lab, lst in (("A", a), ("B", b)):
    ns = sorted(e["n"] for e in lst)
    print("  %s n 范围: %d..%d  (min=%d max=%d)" % (lab, ns[0], ns[-1], ns[0], ns[-1]))
    print("      n 列表:", ns)
    cat = defaultdict(int)
    for e in lst:
        cat["AS_*" if e["name"].startswith("AS_") else ("On*" if e["name"].startswith("On") else "?")] += 1
    print("      名字类别:", dict(cat))
    vw = defaultdict(int)
    for e in lst:
        vw[e["view"]] += 1
    print("      所属 View:", dict(vw))
print()

print("=== 全部 62 条 (按 View, n) ===")
g = defaultdict(list)
for e in entries:
    g[e["view"]].append(e)
for view in sorted(g):
    print("\n-- %s (%d) --" % (view, len(g[view])))
    for e in sorted(g[view], key=lambda x: x["n"]):
        print("   n=%-4d ?%s%-3s %-8s 0x%08X %s" % (
            e["n"], e["ords"], e["at"] or "", e["form"], e["va"], e["name"]))
print()

# 同名双形态
print("=== 同名同时出现在两种形态 (按 Name 全局) ===")
byname = defaultdict(set)
byvn = defaultdict(set)
for e in entries:
    byname[e["name"]].add(e["form"])
    byvn[(e["view"], e["name"])].add(e["form"])
hit = False
for nm, forms in sorted(byname.items()):
    if len(forms) == 2:
        hit = True
        print("  NAME BOTH: %s" % nm)
        for e in entries:
            if e["name"] == nm:
                print("      %-22s n=%-4d 0x%08X  %s" % (e["view"], e["n"], e["va"], e["form"]))
if not hit:
    print("  (无 - 按 Name)")
print()
print("=== 同名双形态 (按 View+Name) ===")
for (view, nm), forms in sorted(byvn.items()):
    if len(forms) == 2:
        print("  %s :: %s" % (view, nm))
        for e in entries:
            if e["view"] == view and e["name"] == nm:
                print("      n=%-4d ?%s%s 0x%08X  %s" % (e["n"], e["ords"], e["at"], e["va"], e["form"]))
