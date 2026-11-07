# -*- coding: utf-8 -*-
"""Append the local CA to cacert.pem (both game root and sandbox)."""
import os, shutil, time

CA = os.path.join(os.getcwd(), "CODOLServer", "lobby3074", "codol_ca.pem")
ca = open(CA, "rb").read()
print("CA pem %d bytes" % len(ca))

for p in [r"COD OL\cacert.pem",
          r"run_codol_001\sandbox_ifs1_20260923\cacert.pem",
          r"run_codol_001\sandbox_datafix_20260929\cacert.pem"]:
    if not os.path.isfile(p):
        print("  SKIP (missing): %s" % p); continue
    raw = open(p, "rb").read()
    if b"CODOL-LOCAL" in raw or b"CODOL Local Lobby CA" in raw:
        print("  already contains CODOL CA: %s" % p); continue
    bak = p + ".bak_z7ca_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(p, bak)
    if not raw.endswith(b"\n"):
        raw += b"\n"
    open(p, "wb").write(raw + ca)
    back = open(p, "rb").read()
    print("  %s" % p)
    print("     %d -> %d bytes  contains CA: %s"
          % (len(raw), len(back), b"CODOL Local Lobby CA" in back))
    print("     backup: %s" % bak)
