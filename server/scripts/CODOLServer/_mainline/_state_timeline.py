"""Print the distinct state transitions from an observer state CSV.

Read-only diagnostic: collapses consecutive identical snapshots and prints
the fields that matter for the lobby protocol chase.
"""
from __future__ import annotations

import csv
import sys

WANT = ["t", "dw_state_name", "sub_state", "uA50", "last_err",
        "lobReqC8", "lobReq5e8", "lobReq644", "lobReq5ec", "lobReq5f0",
        "lobReq9c", "lobReq640", "obj_stage", "obj_code", "obj240",
        "obj1400", "lob1400", "lob240", "http_state", "http_status",
        "lob_http_state", "lob_http_status", "cfg_applied", "lobby_sub"]

# Fields whose value changes are what actually signals progress.  Volatile
# counters (lob_http_state, obj240, ...) are ignored for the transition key
# so the output stays readable.
KEY = ["dw_state_name", "sub_state", "uA50", "last_err", "lobReqC8",
       "lobReq5e8", "lobReq644", "lobReq5ec", "lobReq5f0", "lobReq9c",
       "lobReq640", "obj_stage", "obj_code", "lob1400", "lob240",
       "cfg_applied", "lobby_sub"]


def main():
    path = sys.argv[1]
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rdr = csv.DictReader(fh)
        cols = [c for c in WANT if c in rdr.fieldnames]
        keys = [c for c in KEY if c in rdr.fieldnames]
        prev = None
        for row in rdr:
            key = tuple(row.get(c, "") for c in keys)
            if key == prev:
                continue
            prev = key
            print(" ".join("%s=%s" % (c, row.get(c, "")) for c in cols))


if __name__ == "__main__":
    sys.exit(main())
