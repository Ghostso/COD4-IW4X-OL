# -*- coding: utf-8 -*-
"""028: rebuild per-cycle event timeline from EXISTING logs only (read-only)."""
import os, re, sys
K = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT"
logs = []
for d, pat in ((K, "lobby_srv.log"), ("DEV-BOOKING\_025", "lobby_srv.log.pre025")):
    p = os.path.join(d, pat)
    if os.path.exists(p):
        logs.append((p, os.path.getsize(p)))
print("available server logs:")
for p, s in logs:
    print("   %-58s %d B" % (p, s))
print()

p = os.path.join(K, "lobby_srv.log")
lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
print("total lines:", len(lines))

# collect events
ev = []
for i, l in enumerate(lines):
    if "task=14" in l and "service=6" in l:
        ev.append((i, l[:11].strip(), "REQUEST_6_14"))
    elif "push 'mmbook accepted'" in l:
        ev.append((i, l[:11].strip(), "PUSH_DECISION"))
    elif "0x85 推送" in l and "type=2" in l:
        ev.append((i, l[:11].strip(), "PUSH_FRAME_WRITTEN"))
    elif "0x85 应答" in l and "service=6" in l and "task=14" in l:
        ev.append((i, l[:11].strip(), "ACK_6_14"))
    elif "对端关闭" in l:
        ev.append((i, l[:11].strip(), "PEER_CLOSED"))
    elif "大厅连接结束" in l:
        ev.append((i, l[:11].strip(), "CONN_END"))
    elif "大厅连接建立" in l:
        ev.append((i, l[:11].strip(), "CONN_ESTABLISHED"))
print("events found:", len(ev))
print()
# group into cycles: start at each PUSH_DECISION, take surrounding window
starts = [k for k, e in enumerate(ev) if e[2] == "PUSH_DECISION"]
shown = 0
for k in starts:
    if shown >= 6: break
    lo = max(0, k - 2); hi = min(len(ev), k + 6)
    print("=== cycle #%d (line %d) ===" % (shown + 1, ev[k][0]))
    for j in range(lo, hi):
        print("   line %-6d %s  %s" % (ev[j][0], ev[j][1], ev[j][2]))
    shown += 1
print()
print("=== close-direction evidence hunt ===")
for kw in ("reset", "RST", "WinError", "10054", "ConnectionReset", "重置", "FIN", "shutdown", "断开"):
    hits = [(i, l) for i, l in enumerate(lines) if kw.lower() in l.lower()]
    print("   %-16s hits=%d %s" % (kw, len(hits), (hits[0][1][:80] if hits else "")))
