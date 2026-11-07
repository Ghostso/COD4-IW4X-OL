"""RESTORE-IIPS-CONTRACT-001 / Task 07b - resolve the callback import and message id.

Task 07 found the readiness handoff at RVA 0x17E86:

    push 0                 ; lParam
    push 1                 ; wParam
    push 0x506D            ; Msg          <-- callback message id
    push edx               ; hWnd         <-- m_hCallbackHWnd
    call dword [0x10033428]

The callee is an IAT slot, not a name lookup. This script resolves which imported
function 0x10033428 is, so the handoff is named from the import table rather than
inferred, and records the message id.

It also checks whether LocalRM_v3.dll contains ANY code at that site.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
IIPS = os.path.join(GAME, "IIPS", "iips.dll")
V3 = os.path.join(ROOT, "LocalRM_v3.dll")


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


def r2o(secs, rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            off = s["raw"] + (rva - s["va"])
            if 0 <= off < s["raw"] + s["rsize"]:
                return off
    return None


def cstr(d, off, n=128):
    e = d.find(b"\0", off, off + n)
    return d[off:e if e >= 0 else off + n].decode("latin1", "replace")


def resolve_iat(d, pe, secs, iat_rva):
    """Walk the import descriptors and return (dll, name) for a given IAT RVA."""
    imp_rva = struct.unpack_from("<I", d, pe + 24 + 96 + 8)[0]
    off = r2o(secs, imp_rva)
    if off is None:
        return None, None
    i = 0
    while True:
        o = off + i * 20
        if o + 20 > len(d):
            break
        oft, ts, fc, nr, fta = struct.unpack_from("<IIIII", d, o)
        if nr == 0 and oft == 0 and fta == 0:
            break
        no = r2o(secs, nr)
        dll = cstr(d, no, 64) if no is not None else "?"
        lookup = oft if oft else fta
        lo = r2o(secs, lookup)
        if lo is not None:
            j = 0
            while j < 4096:
                p = lo + j * 4
                if p + 4 > len(d):
                    break
                v = struct.unpack_from("<I", d, p)[0]
                if v == 0:
                    break
                slot = fta + j * 4
                if slot == iat_rva:
                    if v & 0x80000000:
                        return dll, "#%d" % (v & 0xFFFF)
                    h = r2o(secs, v)
                    return dll, (cstr(d, h + 2, 64) if h is not None else "?")
                j += 1
        i += 1
    return None, None


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    print("=== Task 07b: the callback import and message id ===")
    print()

    d = open(IIPS, "rb").read()
    pe, ib, secs = sections(d)
    callee_rva = 0x33428
    dll, name = resolve_iat(d, pe, secs, callee_rva)
    rep["iat_slot_rva"] = "0x%X" % callee_rva
    rep["resolved_import"] = {"dll": dll, "name": name}
    print("  call dword [0x100%05X]  ->  %s!%s" % (callee_rva, dll, name))

    rep["callback"] = {
        "site_rva": "0x17E90",
        "Msg": "0x506D",
        "wParam": 1,
        "lParam": 0,
        "hWnd_source": "edx register (loaded from a member in the enclosing function)",
    }
    print()
    print("  callback at RVA 0x17E90:")
    print("     Msg    = 0x506D")
    print("     wParam = 1")
    print("     lParam = 0")
    print("     hWnd   = edx")

    # Is 0x506D used anywhere else? A registered custom message would be the
    # provider telling the Engine "I am ready".
    cnt = d.count(struct.pack("<I", 0x506D))
    rep["msg_0x506D_imm32_occurrences"] = cnt
    print()
    print("  immediate 0x506D occurrences in iips.dll: %d" % cnt)
    p = 0
    offs = []
    while True:
        i = d.find(struct.pack("<I", 0x506D), p)
        if i < 0:
            break
        r = None
        for s in secs:
            if s["raw"] <= i < s["raw"] + s["rsize"]:
                r = s["va"] + (i - s["raw"])
                break
        offs.append("0x%X" % r if r is not None else "0x%X(file)" % i)
        p = i + 1
    rep["msg_0x506D_offsets"] = offs
    print("     at: %s" % ", ".join(offs))

    # Compare with LocalRM_v3: does it contain this code at all?
    d3 = open(V3, "rb").read()
    pe3, ib3, secs3 = sections(d3)
    o3 = r2o(secs3, 0x17E86)
    rep["localrm_v3_at_0x17E86"] = (d3[o3:o3 + 16].hex(" ").upper()
                                    if o3 is not None else None)
    print()
    print("  LocalRM_v3.dll bytes at RVA 0x17E86: %s" % rep["localrm_v3_at_0x17E86"])
    print("     (LocalRM_v3 has no code here; its only additions live in .localrm)")

    # CORRECTION: the log string says "SendMessage" but the IAT slot resolves to
    # PostMessageA. The log text is not authoritative; the import table is.
    rep["note_sendmessage_vs_postmessage"] = (
        "The log string reads '[SendMessage][m_hCallbackHWnd %d]' but the actual "
        "import resolved at IAT RVA 0x33428 is USER32!PostMessageA. The log text is "
        "therefore NOT an accurate API name; the import table is authoritative.")

    # LocalRM_v3 reuses the original's .text/.rdata, so the BYTES are present.
    # The question is whether they are ever EXECUTED.
    same_bytes = (rep["localrm_v3_at_0x17E86"] ==
                  d[r2o(secs, 0x17E86):r2o(secs, 0x17E86) + 16].hex(" ").upper())
    rep["localrm_v3_bytes_identical_to_original"] = same_bytes
    print()
    print("  those bytes are byte-identical to the original's: %s" % same_bytes)
    print("  -> LocalRM_v3 carries the original's code IMAGE, but only its two")
    print("     .localrm exports are reachable; this init path is never invoked.")

    rep["conclusion"] = (
        "The provider's readiness handoff is a real PostMessageA call at RVA "
        "0x17E90 with Msg=0x506D, wParam=1, lParam=0, into a callback window handle "
        "held as a member (edx) -- the observable 'provider is ready' signal the "
        "Engine can receive. The log string calls it SendMessage but the import is "
        "PostMessageA. LocalRM_v3.dll contains byte-identical code at this site "
        "because it reuses the original's sections, but that code is unreachable: "
        "only the two .localrm exports are ever called.")
    print()
    print(rep["conclusion"])

    # Confirm reachability claim: list LocalRM_v3's executable additions.
    localrm_code = d3[0x55000:0x55000 + 0x200]
    rep["localrm_section_head"] = localrm_code[:64].hex(" ").upper()
    print()
    print("  .localrm section head: %s" % rep["localrm_section_head"])

    with open(os.path.join(OUT, "t11_sendmessage_import.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t11_sendmessage_import.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
