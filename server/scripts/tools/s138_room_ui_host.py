#!/usr/bin/env python3
"""138: 找房间 UI 的宿主 —— ① RTTI 里所有含 room/party/lobby/gamebrowser 的类
② 所有 UiCpp* 类名（不限于有 SF_Handler 的）
③ CEF 相关 Codo* 接口
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()

names = {}
for m in re.finditer(rb"\.\?A[VU][A-Za-z0-9_@?$<>,\-]{2,120}@@", d):
    names[VA + m.start()] = m.group().decode("latin1")
print("RTTI 总数", len(names))


def short(nm):
    s = nm
    for sep in ("AV", "AU"):
        if sep in s:
            s = s.split(sep, 1)[1]
            break
    return s.split("@@")[0]


for kw in ["UiCpp", "Room", "room", "Party", "party", "Lobby", "lobby",
           "GameBrowser", "gamebrowser", "Codo", "Cef", "CEF", "Browser"]:
    hit = [(va, short(nm)) for va, nm in names.items() if kw in nm]
    if hit:
        print("\n== '%s' : %d ==" % (kw, len(hit)))
        for va, s in sorted(hit)[:40]:
            print("   0x%08X  %s" % (va, s))
