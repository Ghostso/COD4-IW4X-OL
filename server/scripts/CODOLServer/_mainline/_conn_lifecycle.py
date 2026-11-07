"""Summarize the per-process AFD socket lifecycle from an elevated capture.

Reads run_codol_001/runs/NET_CAPTURE_*/game_etw.jsonl (kernel AFD events for
the game pid only) and prints connect/accept/closesocket events plus a
per-remote-endpoint byte/time summary.  Read-only diagnostic helper.
"""
from __future__ import annotations

import json
import sys


def load(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def ep_of(o):
    # AFD reuses the kernel endpoint pointer across connections, so key by
    # handle (which carries a "#generation" suffix) rather than by ep.
    return o.get("handle") or o.get("ep") or "?"


def addr_of(o):
    a = o.get("addr") or o.get("peer") or o.get("remote") or o.get("name")
    if isinstance(a, dict):
        return "%s:%s" % (a.get("ip", "?"), a.get("port", "?"))
    if a is None:
        return ""
    return str(a)


def main():
    path = sys.argv[1]
    rows = [r for r in load(path) if "api" in r]

    print("== connection lifecycle ==")
    for o in rows:
        api = o.get("api")
        if api in ("connect", "disconnect", "closesocket", "accept",
                   "listen", "bind", "socket"):
            print("%9.3f %-12s fam=%-8s type=%-11s proto=%-12s %s %s"
                  % (o.get("t", -1), api, o.get("family", ""),
                     o.get("type", ""), o.get("proto", ""),
                     ep_of(o)[:22], addr_of(o)))

    print()
    print("== per-endpoint totals (t, bytes-ish) ==")
    agg = {}
    for o in rows:
        api = o.get("api")
        ep = ep_of(o)
        if api in ("connect", "accept"):
            d = agg.setdefault(ep, {"first": o.get("t", -1), "last": 0,
                                    "send": 0, "recv": 0, "addr": ""})
            a = addr_of(o)
            if a:
                d["addr"] = a
            continue
        if api not in ("send", "recv", "sendto", "recvfrom"):
            continue
        d = agg.setdefault(ep, {"first": o.get("t", -1), "last": 0,
                                "send": 0, "recv": 0, "addr": ""})
        d["last"] = max(d["last"], o.get("t", 0))
        if d["first"] < 0:
            d["first"] = o.get("t", -1)
        if api in ("send", "sendto"):
            d["send"] += 1
        else:
            d["recv"] += 1
    for ep, d in sorted(agg.items(), key=lambda x: x[1]["first"]):
        if d["send"] + d["recv"] == 0:
            continue
        print("%-24s %8.3f..%8.3f  send=%-5d recv=%-5d %s"
              % (ep[:24], d["first"], d["last"], d["send"], d["recv"],
                 d["addr"]))


if __name__ == "__main__":
    sys.exit(main())
