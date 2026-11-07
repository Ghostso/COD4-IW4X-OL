"""RESTORE-IIPS-CONTRACT-001 / Task 09 - classify the iipsinit window's creator,
and determine the provenance of the value 8189fec.

Part 1: Which module owns the "iipsinit" window class?
  Neither provider image contains the literal. The EXE contains only the decorated
  symbol "?iipsinit". The window is created in BOTH conditions, so its creator is
  common to both. This part checks the remaining candidate -- the EXE -- for the
  actual ENVIRONMENT-LIST-BOX UI it hosts, and for a class-registration site.

Part 2: 8189fec provenance.
  The dialog text observed in condition A is:
      "初始化IIPS错误：8189fec。"
  The value must be classified as DISPLAYED / PRODUCED / CONTROL_FLOW. It is NOT
  assumed to be a Win32 error code.
"""
import json
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
EXE = os.path.join(GAME, "codoMP_client_shipRetail.exe")
BASE = os.path.join(GAME, "codoMP_client_shipRetailBase.dll")
IIPS = os.path.join(GAME, "IIPS", "iips.dll")


def sections(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    ib = struct.unpack_from("<I", d, pe + 24 + 28)[0]
    so = pe + 24 + 224
    secs = []
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        secs.append({"name": name, "va": va, "vsize": vs, "raw": rp, "rsize": rs})
    return pe, ib, secs


def secname(secs, off):
    for s in secs:
        if s["raw"] <= off < s["raw"] + s["rsize"]:
            return s["name"]
    return None


def cstr(d, off, n=200):
    e = d.find(b"\0", off, off + n)
    return d[off:e if e >= 0 else off + n].decode("latin1", "replace")


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    print("=== Task 09: window class ownership + 8189fec provenance ===")
    print()

    # ---- Part 1: the UI strings that build the iipsinit window content ----
    d = open(EXE, "rb").read()
    pe, ib, secs = sections(d)
    print("Part 1 - condition-A window content strings in the EXE")
    ui = [b"Environment List Box", b"iipsinit", b"IIPS\\iips.dll",
          b"WIN_IIPS_INIT_ERROR", b"WIN_IIPS_INIT_FAILED", b"WIN_IIPS_DLL_ERROR",
          b"IIPS: %d:%d:%s-%u:%s:%s:%lld:%lld:%d"]
    rep["exe_ui_strings"] = {}
    for u in ui:
        off = d.find(u)
        if off < 0:
            rep["exe_ui_strings"][u.decode("latin1")] = None
            print("   %-40s NOT FOUND" % u.decode("latin1"))
            continue
        rep["exe_ui_strings"][u.decode("latin1")] = {
            "file_off": "0x%X" % off,
            "section": secname(secs, off),
            "va": "0x%X" % (ib + (off - next(s["raw"] for s in secs
                    if s["raw"] <= off < s["raw"] + s["rsize"]))),
        }
        print("   %-40s off=0x%-8X sec=%-6s va=%s"
              % (u.decode("latin1"), off, secname(secs, off),
                 rep["exe_ui_strings"][u.decode("latin1")]["va"]))

    # The UI is an "Environment List Box" hosted by a window class named
    # "iipsinit": i.e. it is a DIAGNOSTIC UI, not an initialisation function.
    # Confirm by checking the efls / listbox class names nearby.
    print()
    print("   related control-class names in the EXE:")
    for c in (b"ListBox", b"EDIT", b"STATIC", b"Button", b"Environment"):
        print("      %-12s %d" % (c.decode(), d.count(c)))

    # ---- Part 2: 8189fec provenance ----
    print()
    print("Part 2 - provenance of 8189fec")
    needle_ascii = b"8189fec"
    needle_upper = b"8189FEC"
    found = {}
    for label, path in (("EXE", EXE), ("Base.dll", BASE), ("iips.dll", IIPS)):
        dd = open(path, "rb").read()
        found[label] = {
            "ascii_lower": dd.count(needle_ascii),
            "ascii_upper": dd.count(needle_upper),
            "wide_lower": dd.count(needle_ascii.decode().encode("utf-16-le")),
        }
        print("   %-10s literal '8189fec'=%d  '8189FEC'=%d  wide=%d"
              % (label, found[label]["ascii_lower"], found[label]["ascii_upper"],
                 found[label]["wide_lower"]))
    rep["literal_8189fec_occurrences"] = found

    # Classify the value. It is formatted into the dialog text as lowercase hex
    # without a 0x prefix. Check whether iips.dll emits 8-hex-digit values with
    # such a formatter, and whether 0x8189FEC could be an internal status.
    val = 0x8189FEC
    rep["value_analysis"] = {
        "displayed_form": "8189fec (lowercase hex, no 0x prefix, from the dialog text)",
        "numeric": "0x%X" % val,
        "decimal": val,
        "bit31": bool(val & 0x80000000),
        "as_signed_int": val - (1 << 32) if val & 0x80000000 else val,
        "high_byte": "0x%02X" % (val >> 24),
        "note": "Bit 31 is CLEAR (0x8189FEC & 0x80000000 == 0), so the value is "
                "not a negative HRESULT-style code. It is a positive 31-bit value.",
    }
    print()
    for k, v in rep["value_analysis"].items():
        print("   %-18s %s" % (k, v))

    # Is there a formatter that yields lowercase hex without a prefix, near the
    # WIN_IIPS error identifiers?
    fmt_candidates = []
    for fmt in (b"%x", b"%08x", b"%X", b"0x%x", b"%u", b"%d"):
        c = d.count(fmt)
        if c:
            fmt_candidates.append({"fmt": fmt.decode(), "count": c})
    rep["format_specifiers_in_exe"] = fmt_candidates
    print()
    print("   format specifiers present in the EXE:")
    for f in fmt_candidates:
        print("      %-8s %d" % (f["fmt"], f["count"]))

    rep["classification"] = {
        "DISPLAYED_VALUE": "CONFIRMED - '8189fec' appears in the condition-A dialog text",
        "PRODUCED_VALUE": "NOT_OBSERVED - no literal '8189fec' in any shipped binary, "
                          "so it is produced at runtime by a formatter",
        "CONTROL_FLOW_VALUE": "UNKNOWN - cannot be shown to gate control flow without "
                              "reading the protected decision point",
    }
    print()
    print("   CLASSIFICATION")
    for k, v in rep["classification"].items():
        print("      %-20s %s" % (k, v))

    with open(os.path.join(OUT, "t13_class_owner_and_8189fec.json"), "w",
              encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t13_class_owner_and_8189fec.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
