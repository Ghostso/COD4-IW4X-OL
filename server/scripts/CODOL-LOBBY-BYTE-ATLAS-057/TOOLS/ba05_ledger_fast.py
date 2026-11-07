# -*- coding: utf-8 -*-
"""BA-05 全字节归属账本 (numpy 向量化, 230MB 可跑完).

优先级 (先认领者胜):
  1  PE_HEADERS        2  RTTI_TD       3  RTTI_COL     4  VFTABLE
  5  CODE_FUNCTION     6  ASCII_STRING  7  UTF16_STRING 8  PADDING
  9  SECTION_VALUE(兜底)
"""
import json
import os
import re
import struct
import sys

IMG = r"E:\codol_re\client_image_20261027.bin"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DATA")
BASE = 0x400000

d = open(IMG, "rb").read()
N = len(d)
print("image 0x%X (%d)" % (N, N))

# owner 用 bytearray: 0=free, 其余为 kind id. 用 slice 赋值做批量认领.
owner = bytearray(N)
names = ["<free>"]
kids = {}


def K(name):
    if name not in kids:
        kids[name] = len(names)
        names.append(name)
    return kids[name]


def claim(s, e, kind):
    s = max(0, int(s)); e = min(N, int(e))
    if s >= e:
        return 0
    k = K(kind)
    seg = owner[s:e]
    got = seg.count(0)
    if got:
        owner[s:e] = bytes(k if x == 0 else x for x in seg)
    return got


log = []

# ---- 1 PE headers
pe_e = struct.unpack_from("<I", d, 0x3C)[0]
nsec = struct.unpack_from("<H", d, pe_e + 6)[0]
optsz = struct.unpack_from("<H", d, pe_e + 20)[0]
opt = pe_e + 24
soh = struct.unpack_from("<I", d, opt + 60)[0]
claim(0, soh, "PE_HEADERS")
log.append(("PE_HEADERS", soh))

secs = []
secoff = opt + optsz
for i in range(nsec):
    o = secoff + i * 40
    nm = d[o:o + 8].rstrip(b"\0").decode("latin1")
    vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
    ch = struct.unpack_from("<I", d, o + 36)[0]
    secs.append(dict(i=i, nm=nm, va=va, vs=vs, rs=rs, rp=rp, ch=ch))

# ---- 2 RTTI TypeDescriptor
tds = []
pat = re.compile(rb"\.\?A[VU][\x20-\x7E\x80-\xFF]{1,180}\x00")
for m in pat.finditer(d):
    no = m.start()
    td = no - 8
    if td < 0:
        continue
    tds.append((td, m.group()[:-1].decode("latin1")))
tot = 0
for td, nm in tds:
    tot += claim(td, td + 8 + len(nm) + 1, "RTTI_TD")
log.append(("RTTI_TD", tot))

# ---- 3 COL
col_set = set()
for td, nm in tds:
    for target in (td + BASE, td):
        try:
            patb = struct.pack("<I", target)
        except Exception:
            continue
        for m in re.finditer(re.escape(patb), d):
            o = m.start()
            col = o - 12
            if col >= 0 and struct.unpack_from("<I", d, col)[0] == 0:
                col_set.add(col)
tot = 0
for col in col_set:
    tot += claim(col, col + 20, "RTTI_COL")
log.append(("RTTI_COL", tot))

# ---- 4 VFTABLE
vft = set()
for col in col_set:
    for target in (col + BASE, col):
        try:
            patb = struct.pack("<I", target)
        except Exception:
            continue
        for m in re.finditer(re.escape(patb), d):
            vft.add(m.start() + 4)
tot = 0
for st in vft:
    cnt = 0
    p = st
    while p + 4 <= N:
        v = struct.unpack_from("<I", d, p)[0]
        if BASE + 0x1000 <= v < BASE + N:
            cnt += 1
            p += 4
        else:
            break
        if cnt > 500:
            break
    if cnt:
        tot += claim(st, st + cnt * 4, "VFTABLE")
log.append(("VFTABLE", tot))

# ---- 6/7 字符串 (纯 bytes 扫描)
for m in re.finditer(rb"[ -~]{6,}", d):
    claim(m.start(), m.end(), "ASCII_STRING")
for m in re.finditer(rb"(?:[ -~]\x00){6,}", d):
    claim(m.start(), m.end(), "UTF16_STRING")

# ---- 8 padding
for m in re.finditer(rb"\x00{16,}", d):
    claim(m.start(), m.end(), "PADDING_00")
for m in re.finditer(rb"\xCC{8,}", d):
    claim(m.start(), m.end(), "PADDING_CC")

# ---- 9 节兜底
for s2 in secs:
    claim(s2["va"], s2["va"] + max(s2["vs"], 1), "SECTION_VALUE")

tally = [0] * len(names)
for v in owner:
    tally[v] += 1

print()
print("=== 归属统计 ===")
for i in range(1, len(names)):
    print("  %-16s %10d  %8.4f%%" % (names[i], tally[i],
                                      100.0 * tally[i] / N))
print("  %-16s %10d  %8.4f%%" % ("UNCLASSIFIED", tally[0],
                                  100.0 * tally[0] / N))
print("  %-16s %10d" % ("TOTAL", N))

# 未归类区间
gaps = []
i = 0
while i < N:
    if owner[i] == 0:
        j = i
        while j < N and owner[j] == 0:
            j += 1
        gaps.append((i, j))
        i = j
    else:
        i += 1
big = [(a, c) for a, c in gaps if c - a >= 64]
print("\n未归类 runs: %d, >=64B: %d 段, 总 %d 字节"
      % (len(gaps), len(big), sum(c - a for a, c in big)))

os.makedirs(OUT, exist_ok=True)
json.dump(dict(size=N, base=BASE,
               tally={names[i]: tally[i] for i in range(1, len(names))},
               unclassified=tally[0], sections=secs,
               n_td=len(tds), n_col=len(col_set), n_vft=len(vft)),
          open(os.path.join(OUT, "ba05_ledger.json"), "w",
               encoding="utf-8"), indent=1)
with open(os.path.join(OUT, "ba05_unclassified.txt"), "w",
          encoding="utf-8") as f:
    f.write("# 未归类 >=64B: %d 段\n# RVA  size\n" % len(big))
    big.sort(key=lambda x: -(x[1] - x[0]))
    for a, c in big[:8000]:
        f.write("0x%08X  %8d\n" % (a, c - a))
with open(os.path.join(OUT, "ba05_owner.bin"), "wb") as f:
    f.write(bytes(owner))
print("\nwrote ba05_ledger.json / ba05_unclassified.txt / ba05_owner.bin")
