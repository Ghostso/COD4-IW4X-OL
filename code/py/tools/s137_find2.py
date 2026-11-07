#!/usr/bin/env python3
"""137: search exact byte patterns in image, report VA."""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()


def find(pat):
    out, pos = [], 0
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        out.append(VA + i)
    return out


pats = {
    "bare \\0playlist\\0": b"\x00playlist\x00",
    "playlist (sp)": b"playlist ",
    "playlist %d;": b"playlist %d;",
    "playlistnum": b"playlistNum",
    "playlistid": b"playlistId",
    "2587 (mmstart tmpl)": b"2587",
    "playlist_": b"playlist_",
}
for name, pat in pats.items():
    hs = find(pat)
    print("== %s : %d ==" % (name, len(hs)))
    for h in hs[:30]:
        f = h - VA
        print("   0x%08X  %r" % (h, d[max(0, f - 8):f + len(pat) + 12]))
