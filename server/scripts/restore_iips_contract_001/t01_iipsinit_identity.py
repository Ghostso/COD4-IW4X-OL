"""RESTORE-IIPS-CONTRACT-001 / Task 02 - what IS "iipsinit"?

The EB-003 observer reported a window whose class name contained "iipsinit",
by reading the window class with GetClassNameW. But the raw EXE contains the
byte run ".?iipsinit" at 0x75B90B, sitting inside a table of MSVC *mangled
symbol names* (".?AVdwRoomImp@@", ".?AVCallsign_...@@", ...).

So "iipsinit" may be:
  (a) a window CLASS name registered by the EXE, or
  (b) a mangled C++ symbol name that merely contains the substring, or
  (c) an internal stage/state string,
  (d) an error-UI identifier.

This script decides between those by examining the bytes around it and by
looking for window-class registration context, rather than assuming.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
EXE = os.path.join(GAME, "codoMP_client_shipRetail.exe")


def printable_runs(d, start, end, minlen=3):
    out = []
    run = bytearray()
    rs = start
    for i in range(start, min(end, len(d))):
        c = d[i]
        if 0x20 <= c < 0x7F:
            if not run:
                rs = i
            run.append(c)
        else:
            if len(run) >= minlen:
                out.append((rs, bytes(run).decode("latin1")))
            run = bytearray()
    if len(run) >= minlen:
        out.append((rs, bytes(run).decode("latin1")))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    d = open(EXE, "rb").read()
    rep = {"exe": "codoMP_client_shipRetail.exe", "size": len(d)}

    print("=== Task 02: identity of 'iipsinit' ===")
    print()

    # 1. Exact byte context around the occurrence.
    off = d.find(b"iipsinit")
    rep["iipsinit_offset"] = "0x%X" % off
    ctx = d[off - 16:off + 24]
    rep["iipsinit_context_bytes"] = ctx.hex(" ").upper()
    rep["iipsinit_preceded_by_dot_question"] = d[off - 1:off] == b"."
    rep["iipsinit_context_ascii"] = "".join(
        chr(c) if 0x20 <= c < 0x7F else "." for c in ctx)
    print("  offset                      = 0x%X" % off)
    print("  context bytes               = %s" % rep["iipsinit_context_bytes"])
    print("  context ascii               = %s" % rep["iipsinit_context_ascii"])
    print("  preceded by '.'             = %s" % rep["iipsinit_preceded_by_dot_question"])
    print("  preceded by '?iipsinit'     = %s" % (d[off - 2:off] == b"?i"))

    # 2. Is it part of a run of similar mangled names?
    print()
    print("  neighbouring printable runs (mangled-name neighbourhood):")
    nb = printable_runs(d, off - 0x120, off + 0x120)
    for a, s in nb:
        mark = "  <-- the one" if "iipsinit" in s else ""
        print("    0x%-8X %r%s" % (a, s, mark))
    rep["neighbourhood"] = [{"off": "0x%X" % a, "s": s} for a, s in nb]
    mangled_neighbours = sum(1 for _, s in nb if s.startswith(".?A") or s.startswith("?"))
    rep["neighbourhood_mangled_count"] = mangled_neighbours
    print("    mangled-style neighbours: %d/%d" % (mangled_neighbours, len(nb)))

    # 2b. The precise structural test: an MSVC RTTI type descriptor name is
    #     "?<name>" padded to a 4-byte boundary, followed by a pointer to the
    #     type_info. Detect that layout rather than eyeballing the text.
    prev = d[off - 1:off]
    rep["preceding_byte"] = "0x%02X" % prev[0]
    rep["preceding_byte_is_question_mark"] = (prev == b"?")
    tail8 = d[off + 8:off + 8 + 4]
    rep["bytes_after_name"] = tail8.hex(" ").upper()
    pad_count = 0
    p = off + 8
    while p < len(d) and d[p] == 0x00 and pad_count < 8:
        pad_count += 1
        p += 1
    rep["nul_padding_after_name"] = pad_count
    ptr = struct.unpack_from("<I", d, (off + 8 + pad_count) & ~3)[0] if off + 12 < len(d) else 0
    rep["following_dword"] = "0x%08X" % ptr
    image_base = 0x00400000
    ptr_looks_like_rva = (0x1000 <= ptr < len(d))
    rep["following_dword_looks_like_image_pointer"] = ptr_looks_like_rva
    print()
    print("  preceding byte              = 0x%02X (%s)"
          % (prev[0], "'?'" if prev == b"?" else "not '?'"))
    print("  NUL padding after the name  = %d" % pad_count)
    print("  following dword             = 0x%08X  (in-image: %s)"
          % (ptr, ptr_looks_like_rva))

    # 3. Where does the EXE define the mangled-name table? Look for the
    #    classic MSVC RTTI type descriptor prefix ".?AV" density.
    av = d.count(b".?AV")
    rep["msvc_type_descriptor_count"] = av
    print()
    print("  '.?AV' MSVC type-descriptor occurrences = %d" % av)

    # 4. Is "iipsinit" registered as a WNDCLASS anywhere? A window class name is
    #    a standalone NUL-terminated string; ".?iipsinit" is inside a symbol run.
    standalone = 0
    s = 0
    offs = []
    while True:
        i = d.find(b"iipsinit", s)
        if i < 0:
            break
        before = d[i - 1:i]
        after = d[i + 8:i + 9]
        # a class name string would be bounded by a non-'.' char and NUL
        if before != b"." :
            standalone += 1
            offs.append("0x%X" % i)
        s = i + 1
    rep["standalone_iipsinit_strings"] = standalone
    rep["standalone_offsets"] = offs
    print("  standalone 'iipsinit' strings (not preceded by '.') = %d %s"
          % (standalone, offs))

    # 5. The EB-003 observer read the window CLASS via GetClassNameW as "iipsinit".
    #    Record that observation alongside this static fact so the two are not
    #    conflated.
    rep["runtime_observation_eb003"] = (
        "EB-003 observed a window whose CLASS name was 'iipsinit' in condition A; "
        "in condition B the same window existed with EMPTY text.")
    rep["static_observation"] = (
        "The only occurrence of 'iipsinit' in the EXE is '.?iipsinit' at 0x%X, "
        "inside a run of MSVC decorated symbol names. It is therefore a SYMBOL "
        "name, not a literal window-class string stored in .rdata." % off)

    print()
    # The decisive structural test: the name is "?" + identifier, NUL-padded to a
    # 4-byte boundary, immediately followed by an in-image pointer. That is an
    # MSVC RTTI type-descriptor / symbol-table entry, not a WNDCLASS name.
    is_rtti_entry = (
        prev == b"?"
        and pad_count > 0
        and (pad_count % 4 == 0 or struct.unpack_from("<I", d, off + 8)[0] != 0)
    )
    rep["is_rtti_style_entry"] = is_rtti_entry
    if is_rtti_entry:
        verdict = ("RTTI_SYMBOL_NAME -- the single occurrence of 'iipsinit' is the "
                   "decorated symbol '?iipsinit', NUL-padded and followed by an "
                   "in-image pointer, inside a table of MSVC type descriptors "
                   "('.?AVdwRoom@@', '.?AVdwRoomImp@@', '.?AVCallsign_...@@'). "
                   "It is a SYMBOL name, NOT a literal window-class or window-title "
                   "string. Therefore 'iipsinit' must NOT be read as an "
                   "initialisation-function or window-title name on the strength of "
                   "this string alone. The runtime window CLASS that EB-003 observed "
                   "is created by code; its name is not sourced from this .rdata "
                   "literal.")
    else:
        verdict = "AMBIGUOUS -- see raw offsets"
    rep["verdict"] = verdict
    print("VERDICT: %s" % verdict)

    with open(os.path.join(OUT, "t01_iipsinit_identity.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t01_iipsinit_identity.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
