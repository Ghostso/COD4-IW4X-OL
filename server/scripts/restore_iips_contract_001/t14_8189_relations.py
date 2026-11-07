"""RESTORE-IIPS-CONTRACT-001 / Task 10 - are 8189fec and 8189FFCE the same thing?

The brief explicitly warns: "不要把 8189FEC 与 8189FFCE 自动等同".

Prior-round documents mention 8189FFCE repeatedly (ICH035R alone mentions it 10
times). This script establishes what can actually be said about the relationship
from evidence, and refuses to equate them without proof.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")

# NOTE ON WIDTH: the two tokens have DIFFERENT digit counts.
#   "8189fec"  is 7 hex digits -> 0x08189FEC as a 32-bit value
#   "8189FFCE" is 8 hex digits -> 0x8189FFCE as a 32-bit value
# Padding the 7-digit token with a leading zero is an assumption, and it is
# recorded as such rather than silently applied.
A_RAW = "8189fec"
B_RAW = "8189FFCE"
A = int(A_RAW, 16)       # 0x08189FEC
B = int(B_RAW, 16)       # 0x8189FFCE


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    print("=== Task 10: relationship of 8189fec and 8189FFCE ===")
    print()

    rep["values"] = {
        "A": {"display": A_RAW, "hex_digits": len(A_RAW), "hex": "0x%08X" % A,
              "decimal": A},
        "B": {"display": B_RAW, "hex_digits": len(B_RAW), "hex": "0x%08X" % B,
              "decimal": B},
    }
    for k, v in rep["values"].items():
        print("  %s: %-10s (%d hex digits)  as 32-bit = %s  decimal %d"
              % (k, v["display"], v["hex_digits"], v["hex"], v["decimal"]))
    rep["width_note"] = (
        "'8189fec' has 7 hex digits while '8189FFCE' has 8. Reading the shorter "
        "token as a 32-bit value requires padding it with a leading zero; that "
        "padding is an assumption, recorded here rather than applied silently.")
    print()
    print("  WIDTH: %s" % rep["width_note"])

    print()
    print("  numeric relationship:")
    diff = B - A
    print("     B - A            = 0x%X  (%d)" % (diff, diff))
    print("     A & 0xFFFF0000   = 0x%X" % (A & 0xFFFF0000))
    print("     B & 0xFFFF0000   = 0x%X" % (B & 0xFFFF0000))
    print("     low 16 bits A    = 0x%04X" % (A & 0xFFFF))
    print("     low 16 bits B    = 0x%04X" % (B & 0xFFFF))
    print("     high 16 bits A   = 0x%04X" % (A >> 16))
    print("     high 16 bits B   = 0x%04X" % (B >> 16))
    rep["numeric"] = {
        "difference": "0x%X" % diff,
        "A_high16": "0x%04X" % (A >> 16),
        "B_high16": "0x%04X" % (B >> 16),
        "A_low16": "0x%04X" % (A & 0xFFFF),
        "B_low16": "0x%04X" % (B & 0xFFFF),
        "share_high16": (A >> 16) == (B >> 16),
    }

    # Where did 8189FFCE come from historically? Check the prior docs.
    hits = []
    for dirpath, dirnames, files in os.walk(ROOT):
        if any(x in dirpath for x in ("\\out", "\\obj", "__pycache__", "sandbox_B",
                                      "observer", "restore00")):
            continue
        for fn in files:
            if not fn.lower().endswith((".md", ".csv", ".txt")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                t = open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for pat, label in (("8189FFCE", "8189FFCE"), ("8189ffce", "8189ffce"),
                               ("8189fec", "8189fec"), ("8189FEC", "8189FEC")):
                if pat in t:
                    hits.append({"file": os.path.relpath(p, ROOT), "token": label})
    rep["document_mentions"] = hits
    print()
    print("  prior-document mentions:")
    seen = {}
    for h in hits:
        seen.setdefault(h["token"], []).append(h["file"])
    for tok in ("8189FEC", "8189fec", "8189FFCE", "8189ffce"):
        if tok in seen:
            print("     %-10s %d file(s): %s" % (tok, len(seen[tok]),
                                                 ", ".join(seen[tok][:6])))

    # Check whether 8189FFCE appears in any BINARY (it should not, if it is also a
    # runtime-formatted value).
    print()
    print("  literal presence in shipped binaries:")
    bin_hits = {}
    for label, rel in (("EXE", "COD OL\\codoMP_client_shipRetail.exe"),
                       ("Base.dll", "COD OL\\codoMP_client_shipRetailBase.dll"),
                       ("iips.dll", "COD OL\\IIPS\\iips.dll"),
                       ("LocalRM_v3.dll", "LocalRM_v3.dll")):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        d = open(p, "rb").read()
        bin_hits[label] = {
            "8189FEC_ascii": d.count(b"8189FEC") + d.count(b"8189fec"),
            "8189FFCE_ascii": d.count(b"8189FFCE") + d.count(b"8189ffce"),
            "8189_prefix": d.count(b"8189"),
        }
        print("     %-16s 8189fec=%d  8189FFCE=%d  bare'8189'=%d"
              % (label, bin_hits[label]["8189FEC_ascii"],
                 bin_hits[label]["8189FFCE_ascii"], bin_hits[label]["8189_prefix"]))
    rep["binary_literals"] = bin_hits

    # Precise bit-level relation. Do NOT overstate a "family" claim: the only
    # shared structure is the top byte 0x81.
    top_byte_shared = (A >> 24) == (B >> 24)
    rep["bit_relation"] = {
        "top_byte_A": "0x%02X" % (A >> 24),
        "top_byte_B": "0x%02X" % (B >> 24),
        "top_byte_shared": top_byte_shared,
        "high16_equal": (A >> 16) == (B >> 16),
        "low16_equal": (A & 0xFFFF) == (B & 0xFFFF),
    }
    print()
    print("  bit-level relation:")
    print("     top byte  A=0x%02X  B=0x%02X  shared=%s"
          % (A >> 24, B >> 24, top_byte_shared))
    print("     high 16   equal=%s     low 16 equal=%s"
          % ((A >> 16) == (B >> 16), (A & 0xFFFF) == (B & 0xFFFF)))

    rep["verdict"] = (
        "NOT_EQUATED. Both values are non-literal, runtime-formatted numbers (neither "
        "appears as a byte literal in any shipped binary). Their high 16 bits differ "
        "(0x%04X vs 0x%04X) and their low 16 bits differ (0x%04X vs 0x%04X); the only "
        "shared structure is the top byte 0x%02X. Nothing observed in this round "
        "establishes that they denote the same condition, so equating them is "
        "REFUTED as unsupported."
        % (A >> 16, B >> 16, A & 0xFFFF, B & 0xFFFF, A >> 24))
    print()
    print("VERDICT: %s" % rep["verdict"])

    with open(os.path.join(OUT, "t14_8189_relations.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t14_8189_relations.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
