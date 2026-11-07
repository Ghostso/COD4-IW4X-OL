# -*- coding: utf-8 -*-
import os, re
K = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT"
lines = open(os.path.join(K, "lobby_srv.log"), encoding="utf-8", errors="replace").read().splitlines()
cur = None
hist = []
rst = []
for i, l in enumerate(lines):
    m = re.search(r"\u5927\u5385\u8fde\u63a5\u5efa\u7acb \('([^']+)', (\d+)\)", l)
    if m:
        cur = m.group(2)
        hist.append([cur, i, [], 0, 0, 0])
    if cur and hist:
        if "push 'mmbook accepted'" in l:
            hist[-1][2].append(i)
        if "0x85 \u63a8\u9001" in l:
            hist[-1][3] += 1
        if "\u5bf9\u7aef\u5173\u95ed" in l:
            hist[-1][4] += 1
        if "recv" in l and "10054" in l:
            hist[-1][5] += 1
            rst.append(cur)
print("connections tracked:", len(hist))
print()
print("=== all connections that received an accepted push ===")
for c, i, pl, pc, fin, r in hist:
    if pl or r:
        print("   conn %-7s start_line=%-5d push_decisions=%-2d push_frames=%-2d peer_closed=%-2d rst=%d" %
              (c, i, len(pl), pc, fin, r))
print()
print("=== RST connections (%s) : events between their establish and the RST ===" % ",".join(rst))
for c, i, pl, pc, fin, r in hist:
    if r:
        print("   --- conn %s (from line %d) ---" % (c, i))
        j = i
        shown = 0
        while j < len(lines) and shown < 22:
            l = lines[j]
            if ("task=14" in l or "push" in l or "0x85" in l or "recv" in l or "\u5bf9\u7aef\u5173\u95ed" in l
                    or "\u8fde\u63a5\u7ed3\u675f" in l or "\u8fde\u63a5\u5efa\u7acb" in l):
                tag = ""
                if "task=14" in l: tag = "REQ6_14"
                elif "push '" in l: tag = "PUSH_DECISION"
                elif "0x85 \u63a8\u9001" in l: tag = "PUSH_FRAME"
                elif "0x85 \u5e94\u7b54" in l: tag = "ACK"
                elif "recv" in l: tag = "*** RST ***"
                elif "\u5bf9\u7aef\u5173\u95ed" in l: tag = "PEER_CLOSED"
                elif "\u8fde\u63a5\u7ed3\u675f" in l: tag = "CONN_END"
                elif "\u8fde\u63a5\u5efa\u7acb" in l: tag = "CONN_EST"
                if tag in ("REQ6_14", "PUSH_DECISION", "PUSH_FRAME", "ACK", "*** RST ***", "PEER_CLOSED", "CONN_END", "CONN_EST"):
                    print("      %4d %-12s %s" % (j, tag, l[:80]))
                    shown += 1
            j += 1
