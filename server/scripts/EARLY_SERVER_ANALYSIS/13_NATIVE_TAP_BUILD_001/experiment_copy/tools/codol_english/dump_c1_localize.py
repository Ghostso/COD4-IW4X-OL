#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
dump_c1_localize.py -- list every LocalizeEntry (asset type 27) the shipped
Call of Duty Online 1.1.1.13 zones carry, with its Chinese (GBK) value.

    python tools/codol_english/dump_c1_localize.py [-o c1_localize.json]

Output: {zone: [[index, name, approx, value_hex|null], ...]} -- the same
shape the first English pass used (loc_full.json).  ``approx`` is "~" when
the name or value was a de-duplicated block-3 reference that
tools/codol_zone_assets.py's RefResolver placed heuristically.

build_ff.py uses it to (1) emit only names C1 really has, so the English
zone never adds localize-pool entries C1 would not have had, and (2) compare
the format tokens of each English value with the Chinese one.

Needs the alpha0022 zone reader (CODOL_ALPHA0022) and C1.exe for the zone key;
inflated zones are cached under %TEMP%\codol_zones by that reader.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
ALPHA = os.environ.get("CODOL_ALPHA0022", r"D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13"
                       r"\CODOL\1.1.1.13_server\alpha0022")
for _p in (ALPHA, os.path.join(ALPHA, "zones")):  # zone_assets.py moved into zones/
    if _p not in sys.path:
        sys.path.insert(0, _p)
import codol_zone_assets as cza  # noqa: E402  (also puts alpha0022 on sys.path)

za = cza.za
T_LOCALIZE = 27
DEFAULT_OUT = os.path.join(os.environ.get("TEMP", "."), "codol_english", "c1_localize.json")


def dump_zone(z):
    rows = cza.list_zone(z)
    ents, vrefs = [], []
    for a in z.assets:
        if a.type != T_LOCALIZE:
            continue
        b = a.blob
        vp = struct.unpack_from("<I", b, 0)[0]
        val = None
        if vp == 0xFFFFFFFF:
            e = b.index(b"\0", 8)
            val = b[8:e].hex()
        elif vp not in (0, 0xFFFFFFFE):
            vrefs.append((a.index, (vp - 1) & 0x0FFFFFFF, a.offset + za.ASSET_BASE, 0xFF))
        name = rows[a.index][1]
        approx = rows[a.index][2]
        ents.append([a.index, name, approx, val])
    if vrefs:
        res = cza.RefResolver(z.data, {}).resolve(vrefs)
        for e in ents:
            if e[3] is None:
                fo, exact = res.get(e[0], (None, False))
                if fo is not None:
                    e[3] = z.data[fo:z.data.index(b"\0", fo)].hex()
                    if not exact:
                        e[2] = "~"
    return ents


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-o", "--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    ffdir = za.ff_dir()
    out = {}
    for fn in sorted(os.listdir(ffdir)):
        if not fn.endswith(".ff"):
            continue
        zn = fn[:-3]
        try:
            z = za.open_zone(zn)
        except Exception as ex:  # a zone the reader cannot open has no strings for us
            print("skip %s: %s" % (zn, ex))
            continue
        if not any(a.type == T_LOCALIZE for a in z.assets):
            continue
        ents = dump_zone(z)
        out[zn] = ents
        print("%-42s %5d localize, %4d without a value, %4d unresolved names"
              % (zn, len(ents), sum(1 for e in ents if e[3] is None),
                 sum(1 for e in ents if e[1].startswith("<"))))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
