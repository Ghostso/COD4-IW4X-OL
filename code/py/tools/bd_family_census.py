#!/usr/bin/env python3
"""bd 层 RTTI 类族普查: 服务名族 bd<Service>* —— 与服务名表一一对应的本地证据。"""
import re
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()

# 收集所有 .?AV/U...@@
classes = []
for m in re.finditer(rb"\.\?A[VU][ -~]{2,100}?@@", data):
    s = m.group(0).decode("latin1")
    classes.append((m.start(), s))

# 服务根词
roots = ["Messaging", "Storage", "Profiles", "Marketplace", "Matchmaking",
         "TitleUtilities", "ContentUnlock", "RichPresence", "Friends", "Bandwidth",
         "Leaderboard", "LeaderBoard", "Tencent", "Lobby", "Mail", "Clan", "Party"]
print("=== bd<Root>* 类族 ===")
for root in roots:
    hits = [(o, s) for o, s in classes if root in s and s.startswith(".?AVbd")]
    if hits:
        print("\n[%s] %d 类:" % (root, len(hits)))
        for o, s in hits[:30]:
            print("   0x%08X  %s" % (o, s))
    else:
        # 试试不带 bd 前缀
        hits2 = [(o, s) for o, s in classes if root in s]
        if hits2:
            print("\n[%s] (非bd前缀) %d 类: %s" % (root, len(hits2), [s for o,s in hits2[:8]]))

# 所有以 .?AVbd 开头的类 (bd 层全貌)
print("\n\n=== 所有 .?AVbd* 类 (前120) ===")
bds = [(o,s) for o,s in classes if s.startswith(".?AVbd") or s.startswith(".?AUbd")]
print("总数:", len(bds))
for o,s in bds[:120]:
    print("  0x%08X  %s" % (o,s))
