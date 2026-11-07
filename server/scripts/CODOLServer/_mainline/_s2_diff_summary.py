# -*- coding: utf-8 -*-
"""S2-D: summarize _s2_iips_diff.json and classify .text patches."""
import sys, json, struct
from collections import Counter

try:
    import capstone
except Exception:
    capstone = None


def main():
    path = sys.argv[1]
    d = json.load(open(path, encoding="utf-8"))
    runs = d["diff_runs"]
    print("diff_regions", d["diff_region_count"], "diff_bytes", d["diff_byte_total"])
    print("sections", Counter(r["b_sec"] for r in runs))
    print()
    print("ALL RUNS")
    for r in runs:
        a = bytes.fromhex(r["a_head"])
        b = bytes.fromhex(r["b_head"])
        print("%-10s %-6s len=%-4d a=%s b=%s" % (r["off"], r["b_sec"], r["len"], a[:20].hex(), b[:20].hex()))

    text_runs = [r for r in runs if r["b_sec"] == ".text"]
    print()
    print("TEXT RUNS:", len(text_runs))
    for r in text_runs:
        a = bytes.fromhex(r["a_head"])
        b = bytes.fromhex(r["b_head"])
        print("---", r["off"], "va", r["a_va"], "len", r["len"])
        print("A", a.hex(" "))
        print("B", b.hex(" "))
        if capstone:
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
            for tag, buf, addr in [("A", a, 0x10000000 + int(r["a_va"], 16) - 0x10000000), ("B", b, 0x10000000 + int(r["a_va"], 16) - 0x10000000)]:
                for insn in md.disasm(buf[:min(len(buf), 32)], addr):
                    print(" ", tag, hex(insn.address), insn.mnemonic, insn.op_str)


if __name__ == "__main__":
    main()
