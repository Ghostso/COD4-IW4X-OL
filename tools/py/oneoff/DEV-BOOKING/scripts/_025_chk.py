# -*- coding: utf-8 -*-
import os, re
p = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\accepted_state.txt"
lines = [l for l in open(p, encoding="utf-8", errors="replace").read().splitlines() if " SAM " not in l]
print("non-SAM lines =", len(lines))
def g(l, k):
    m = re.search(k + r"=([0-9A-Fa-fx\-]+)", l)
    return m.group(1) if m else None
armed = [l for l in lines if g(l, "this278") not in (None, "0x0000", "0xFFFF")]
print("non-SAM rows with this278 armed (not 0000/FFFF) =", len(armed))
for l in armed[:20]:
    print("   ", l[:150])
h288 = [l for l in lines if (g(l, "this288_byte") or "") == "1"]
print("non-SAM rows with this288_byte=1 =", len(h288))
print()
print("--- 6/14 timestamps (server log) ---")
lp = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\lobby_srv.log"
for l in open(lp, encoding="utf-8", errors="replace"):
    if "task=14" in l and "解密成功" in l:
        print("   ", l[:11].strip(), "|", l.split("payload")[0].strip()[-60:])
