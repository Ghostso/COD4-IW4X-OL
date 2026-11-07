#!/usr/bin/env python3
"""138: 找房间内 UI 刷新回调 —— 在 62 个 SF_Handler 之外，扩大扫 `?AU<Name>_SF_Handler@?...@@Init@<任意类>`。
重点找: ready / team / vote / roomstate / member 相关名字。
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()

# 任意类的 _SF_Handler（不只 UiCpp*）
PAT = re.compile(rb"\.\?A[VU]([A-Za-z0-9_]+)_SF_Handler@\?[0-9A-Z]+@*\?\?Init@([A-Za-z0-9_]+)@@")
hits = {}
for m in PAT.finditer(d):
    name = m.group(1).decode("latin1")
    cls = m.group(2).decode("latin1")
    hits.setdefault(cls, []).append((name, VA + m.start()))

print("总类数 %d ; 总 handler %d" % (len(hits), sum(len(v) for v in hits.values())))
for cls in sorted(hits):
    print("\n== %s : %d ==" % (cls, len(hits[cls])))
    for nm, va in sorted(hits[cls]):
        print("   0x%08X  %s" % (va, nm))

print("\n\n=== 关键字命中（ready/team/vote/member/roomstate/gamestart）===")
KW = ["ready", "Ready", "team", "Team", "vote", "Vote", "member", "Member",
      "roomstate", "RoomState", "gamestart", "GameStart", "start", "Start", "countdown"]
for cls in sorted(hits):
    for nm, va in hits[cls]:
        if any(k in nm for k in KW):
            print("   0x%08X  %-28s  %s" % (va, cls, nm))
