"""EB-003 Agent 03 - how does the Engine actually obtain GetResourceManagerII?

The EXE does not import iips.dll; it only contains the string "iips.dll", so it
resolves the provider dynamically. This locates the literal strings the Engine
uses for that resolution and reports exactly which export *names* it asks for.

A name-based lookup is ordinal-layout independent; an ordinal-based lookup is not.
That distinction is the whole question for whether LocalRM_v3 can be a drop-in
provider, so it is established from bytes rather than assumed.
"""
import json
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore003", "evidence")

TARGETS = [
    b"iips.dll",
    b"GetResourceManagerII",
    b"ReleaseResourceManagerII",
    b"GetResourceManager",
    b"ReleaseResourceManager",
    b"iips",
]


def scan(path, label, out):
    d = open(path, "rb").read()
    res = {"file": label, "size": len(d), "hits": []}
    for t in TARGETS:
        start = 0
        found = []
        while True:
            i = d.find(t, start)
            if i < 0:
                break
            # For short needles require NUL-termination to avoid ASCII noise.
            term = d[i + len(t):i + len(t) + 1]
            exact = term in (b"\x00", b"")
            found.append({"off": i, "nul_terminated": exact,
                          "preview": d[max(0, i - 8):i + len(t) + 4]
                          .decode("latin1", "replace")})
            start = i + 1
        # Wide (UTF-16LE) form
        wide = t.decode("latin1").encode("utf-16-le")
        start = 0
        wfound = []
        while True:
            i = d.find(wide, start)
            if i < 0:
                break
            wfound.append({"off": i})
            start = i + 1
        res["hits"].append({
            "needle": t.decode("latin1"),
            "ascii_count": len(found),
            "ascii_nul_terminated": sum(1 for f in found if f["nul_terminated"]),
            "wide_count": len(wfound),
            "samples": found[:6],
        })
    out.append(res)
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    out = []
    for label, rel in [
        ("codoMP_client_shipRetail.exe", "codoMP_client_shipRetail.exe"),
        ("codoMP_client_shipRetailBase.dll", "codoMP_client_shipRetailBase.dll"),
    ]:
        scan(os.path.join(GAME, rel), label, out)

    print("=== EB-003 Agent 03: dynamic resolution strings ===")
    for r in out:
        print("\n%s (%d bytes)" % (r["file"], r["size"]))
        for h in r["hits"]:
            if h["ascii_count"] == 0 and h["wide_count"] == 0:
                continue
            print("  %-26s ascii=%-3d (nul-term %-3d) wide=%d"
                  % (h["needle"], h["ascii_count"], h["ascii_nul_terminated"], h["wide_count"]))
            for s in h["samples"][:3]:
                if s["nul_terminated"]:
                    print("        off=0x%-8X %r" % (s["off"], s["preview"]))

    with open(os.path.join(OUT, "a03_dynamic_resolution.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % os.path.join(OUT, "a03_dynamic_resolution.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
