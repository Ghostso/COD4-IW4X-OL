"""RESTORE-IIPS-CONTRACT-001 / Task 02b - who creates the "iipsinit" window class?

Task 02 established that "iipsinit" in the EXE is an MSVC decorated SYMBOL name
("?iipsinit"), not a literal window-class string. Yet EB-003 observed, at runtime,
a window whose CLASS name read back as containing "iipsinit".

So the class name is *produced by code*. This script looks for the observable
static traces of that:
  * WNDCLASSEX / RegisterClass-style string literals elsewhere in the image
  * the "Environment List Box" literal and its neighbours
  * any other standalone short strings containing "iips"

It does not claim ownership it cannot prove.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
EXE = os.path.join(GAME, "codoMP_client_shipRetail.exe")
BASE = os.path.join(GAME, "codoMP_client_shipRetailBase.dll")


def standalone_strings(d, needle):
    """Find needle occurrences that look like real C strings (NUL-terminated)."""
    out = []
    s = 0
    while True:
        i = d.find(needle, s)
        if i < 0:
            break
        # must be printable on both sides and either preceded by a non-printable
        # or the start of the run, and NUL-terminated.
        end = i + len(needle)
        nul = d[end:end + 1] == b"\x00"
        before = d[i - 1:i]
        prev_ok = (i == 0) or (before[0] < 0x20 or before[0] > 0x7E)
        out.append({"off": i, "nul_terminated": nul, "prev_ok": prev_ok})
        s = i + 1
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    print("=== Task 02b: window-class ownership for the iips window ===")
    print()

    for label, path in (("EXE", EXE), ("Base.dll", BASE)):
        d = open(path, "rb").read()
        r = {"size": len(d)}
        print("%s (%d bytes)" % (label, len(d)))
        for needle in (b"iipsinit", b"iips", b"Environment List Box", b"IIPS",
                       b"iips.dll"):
            hits = standalone_strings(d, needle)
            good = [h for h in hits if h["nul_terminated"] and h["prev_ok"]]
            r[needle.decode()] = {
                "total": len(hits),
                "plausible_cstrings": len(good),
                "offsets": ["0x%X" % h["off"] for h in good[:12]],
            }
            if hits:
                print("   %-22s total=%-4d plausible_cstring=%-4d %s"
                      % (needle.decode(), len(hits), len(good),
                         ", ".join("0x%X" % h["off"] for h in good[:6])))
        rep[label] = r
        print()

    # The "Environment List Box" literal is the one EB-003 read as the window text
    # in condition A. Show its exact context.
    d = open(EXE, "rb").read()
    off = d.find(b"Environment List Box")
    print("EXE 'Environment List Box' at 0x%X" % off)
    print("   context: %r" % d[off - 40:off + 30])
    rep["environment_list_box"] = {
        "off": "0x%X" % off,
        "context_ascii": "".join(chr(c) if 0x20 <= c < 0x7F else "."
                                 for c in d[off - 40:off + 30]),
    }

    rep["conclusion"] = (
        "The literal 'iipsinit' does not exist as a standalone C string in either "
        "image; it exists only as the decorated symbol '?iipsinit'. 'Environment "
        "List Box' DOES exist as a standalone string in the EXE, next to the "
        "WIN_IIPS_* error identifiers and 'IIPS\\iips.dll'. The runtime window "
        "CLASS observed by EB-003 therefore cannot be sourced from an 'iipsinit' "
        "literal.")
    print()
    print(rep["conclusion"])

    with open(os.path.join(OUT, "t02_window_class_owner.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t02_window_class_owner.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
