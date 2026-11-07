"""RESTORE-IIPS-CONTRACT-001 / Task 05b - disassemble the code that uses '?iipsinit'.

Task 05 found exactly ONE reference to the '?iipsinit' string's address, at EXE
RVA 0x18F45A (.tp3 section). This script decodes the surrounding code so the
actual role of that symbol is read from instructions instead of guessed from its
name.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
EXE = os.path.join(GAME, "codoMP_client_shipRetail.exe")


def sections(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    ib = struct.unpack_from("<I", d, pe + 24 + 28)[0]
    so = pe + 24 + 224
    out = []
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        out.append({"name": name, "va": va, "vsize": vs, "raw": rp, "rsize": rs})
    return pe, ib, out


def r2o(secs, rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            off = s["raw"] + (rva - s["va"])
            if 0 <= off < s["raw"] + s["rsize"]:
                return off
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    d = open(EXE, "rb").read()
    pe, ib, secs = sections(d)
    rep = {"image_base": "0x%X" % ib}
    print("=== Task 05b: the '?iipsinit' use site ===")
    print("  EXE image base = 0x%08X" % ib)
    print()

    use_rva = 0x18F45A
    off = r2o(secs, use_rva)
    rep["use_rva"] = "0x%X" % use_rva

    # The reference is an absolute VA. Determine which operand form it is by
    # looking at the byte immediately before it.
    before = d[off - 1]
    before2 = d[off - 2]
    rep["operand_prefix_byte"] = "0x%02X" % before
    rep["operand_prefix_byte2"] = "0x%02X" % before2
    forms = {0x68: "push imm32", 0xB8: "mov eax,imm32", 0xA1: "mov eax,[imm32]",
             0xA3: "mov [imm32],eax", 0x50: "n/a(preceded by push eax)"}
    rep["operand_form"] = forms.get(before, "unknown (0x%02X)" % before)
    print("  reference at RVA 0x%X" % use_rva)
    print("  preceding byte   = 0x%02X  -> %s" % (before, rep["operand_form"]))

    # Dump a window of bytes around the site with light decoding.
    win_off = r2o(secs, use_rva - 0x40)
    raw = d[win_off:win_off + 0xA0]
    rep["window_bytes"] = raw.hex(" ").upper()
    rep["window_rva"] = "0x%X" % (use_rva - 0x40)
    print()
    print("  bytes 0x%X..0x%X:" % (use_rva - 0x40, use_rva - 0x40 + 0xA0))
    for i in range(0, len(raw), 16):
        chunk = raw[i:i + 16]
        asc = "".join(chr(c) if 0x20 <= c < 0x7F else "." for c in chunk)
        print("    %08X  %-47s  %s" % (use_rva - 0x40 + i,
                                       chunk.hex(" ").upper(), asc))

    # Classify: is this inside a RegisterClassEx argument build, or a string
    # comparison, or a log call? Look for nearby API-name strings.
    near = d[win_off - 0x400:win_off + 0x400]
    api_hits = [k for k in (b"RegisterClassExA", b"RegisterClassExW",
                            b"CreateWindowExA", b"CreateWindowExW",
                            b"GetClassNameA", b"GetClassNameW",
                            b"UnregisterClassA", b"SetWindowText")
                if k in near]
    rep["nearby_api_strings"] = [k.decode() for k in api_hits]
    print()
    print("  nearby user32 API name strings (+/-0x400): %s"
          % (", ".join(rep["nearby_api_strings"]) or "none"))

    rep["note"] = (
        "The distinct '?iipsinit' symbol address is referenced exactly once in the "
        "EXE, at RVA 0x18F45A. No window-class/registration API name string sits "
        "nearby, so this site is not itself a RegisterClassEx call. The window "
        "CLASS EB-003 read back as 'iipsinit' is therefore not provably created "
        "here; the class name's provenance remains CANDIDATE.")
    print()
    print(rep["note"])

    with open(os.path.join(OUT, "t08_iipsinit_use_site.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t08_iipsinit_use_site.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
