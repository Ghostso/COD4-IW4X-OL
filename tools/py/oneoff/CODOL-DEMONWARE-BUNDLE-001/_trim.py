# -*- coding: utf-8 -*-
import os, shutil
ROOT  = r"D:\BaiduNetdiskDownload\使命召唤OL"
STAGE = os.path.join(ROOT, "CODOL-DEMONWARE-EVIDENCE-BUNDLE-20261012")
bk = os.path.join(STAGE, "06_SUMMARY_INDEX", "02_LOBBY_REPRODUCTION", "DEV-BOOKING-SPECS")
if os.path.isdir(bk):
    shutil.rmtree(bk)
os.makedirs(bk, exist_ok=True)
src = os.path.join(ROOT, "DEV-BOOKING")
keep = ["BOOKING_PROTOCOL_SPEC-001.md","BOOKING_PROTOCOL_SPEC-002.md","BOOKING_PROTOCOL_SPEC-003.md",
        "BOOKING_PROTOCOL_SPEC-004.md","BOOKING_CLIENT_CONTRACT-001.md","BOOKING_STATE-001.md",
        "BOOKING-RESPONSE-DISPATCH-004.md","BOOKING-CONNECT-PATH-007.md",
        "PVE-BATTLE-CONTRACT-LINEAGE-021.md","PVE-MATCHING-ACCEPTED-GATE-CLOSURE-022.md",
        "OLMOD-CODOL-BOOKING-BATTLE-BRIDGE-030.md","PVE-ACCEPTED-DISPATCH-026.md"]
for f in keep:
    p = os.path.join(src, f)
    if os.path.isfile(p):
        shutil.copy2(p, os.path.join(bk, f))
print("DEV-BOOKING-SPECS ->", len(os.listdir(bk)), "files")
print("bundle dirs:", [d for d in sorted(os.listdir(STAGE))])
