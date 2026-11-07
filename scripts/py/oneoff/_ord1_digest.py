"""Digest the ordinal-1 lifecycle dynamic trace into human-readable form."""
import collections
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def codeof(d):
    m = re.search(r"code=(0x[0-9A-Fa-f]+)", d)
    return m.group(1) if m else "?"


def main():
    rows = list(csv.DictReader((ROOT / "base_ordinal1_dynamic_trace.csv").open(encoding="utf-8-sig")))
    print("total events", len(rows))

    c = collections.Counter(r["detail"].split(" code=")[-1].split(" ")[0]
                            for r in rows if r["kind"] == "EXCEPTION")
    print("\n=== exception code histogram ===")
    for k, v in c.most_common():
        print("  ", k, v)

    print("\n=== non-int3 exceptions ===")
    for r in rows:
        if r["kind"] == "EXCEPTION" and codeof(r["detail"]) != "0x80000003":
            print("  ", r["timestamp_s"], r["phase"], r["detail"][:230])

    print("\n=== ORDINAL1_ENTRY ===")
    for r in rows:
        if r["kind"] == "ORDINAL1_ENTRY":
            print("  ", r["timestamp_s"], "tid=" + r["thread_id"], r["detail"])

    print("\n=== ORDINAL1_HOP ===")
    for r in rows:
        if r["kind"] == "ORDINAL1_HOP":
            print("  ", r["timestamp_s"], "tid=" + r["thread_id"], r["detail"])

    print("\n=== EXEC_REGION_NEW / NEW_EXEC_REGION_HIT ===")
    for r in rows:
        if r["kind"] in ("EXEC_REGION_NEW", "NEW_EXEC_REGION_HIT"):
            print("  ", r["timestamp_s"], r["kind"], r["detail"][:200])

    print("\n=== CREATE_THREAD ===")
    for r in rows:
        if r["kind"] == "CREATE_THREAD":
            print("  ", r["timestamp_s"], r["phase"], "tid=" + r["thread_id"], r["detail"])

    print("\n=== EXIT_THREAD ===")
    for r in rows:
        if r["kind"] == "EXIT_THREAD":
            print("  ", r["timestamp_s"], r["phase"], "tid=" + r["thread_id"], r["detail"])

    print("\n=== EXIT_PROCESS ===")
    for r in rows:
        if r["kind"] == "EXIT_PROCESS":
            print("  ", r["timestamp_s"], r["detail"])


if __name__ == "__main__":
    sys.exit(main())
