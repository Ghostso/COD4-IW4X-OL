# -*- coding: utf-8 -*-
import os
targets = {
 "image_best.bin": r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin",
 "client.exe": r"COD OL\codoMP_client_shipRetail.exe",
}
needles = [b"mmstart", b"mmbook", b"start_map_rotate_once", b"sv_resetServer",
           b"mmbook accepted", b"playlist", b"2486", b"3265", b"2489",
           b"sv_map", b"DedicatedBooking", b"Instantmessage"]
for name, p in targets.items():
    if not os.path.exists(p):
        print(name, "MISSING"); continue
    d = open(p, "rb").read()
    print("=== %s  (%d bytes) ===" % (name, len(d)))
    for n in needles:
        c = d.count(n)
        idx = d.find(n)
        ctx = ""
        if idx >= 0:
            s = d[max(0, idx-40):idx+80]
            ctx = "".join(chr(b) if 32 <= b < 127 else "." for b in s)
        print("   %-22s count=%-4d  %s" % (n.decode(), c, ctx))
    print()
