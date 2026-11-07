# -*- coding: utf-8 -*-
with open(r"REF_LOBBY_KIT\n10_live_run_a2.txt", "r", encoding="utf-8", errors="ignore") as f:
    lines_good = [l.strip() for l in f if "[t=" in l]

with open(r"REF_LOBBY_KIT\n10_interactive_test_a5.txt", "r", encoding="utf-8", errors="ignore") as f:
    lines_bad = [l.strip() for l in f if "[t=" in l]

print("=== GOOD RUN (n10_live_run_a2.txt) ===")
for l in lines_good[:15]:
    print(" ", l)

print("\n=== BAD RUN (n10_interactive_test_a5.txt) ===")
for l in lines_bad[:15]:
    print(" ", l)