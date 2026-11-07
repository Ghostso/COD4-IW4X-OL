# -*- coding: utf-8 -*-
"""
_s1_va_xref.py - find direct code xrefs to a target VA in a PE image.

Strategy:
  1. locate named ASCII anchors, compute VA = ImageBase + RVA
  2. scan executable sections for the little-endian 32-bit VA (push/mov/lea imm)
  3. also scan for the VA appearing inside an indirect pointer table (data)
  4. disassemble a window around each direct hit with Capstone

Pure static analysis.
"""
import os
import struct
import sys

import capstone
import pefile

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL"
EXE = os.path.join(ROOT, "codoMP_client_shipRetail.exe")

ANCHORS = [
    "@SF_UI_DW_LIVE_CONNECTING_FAILED",
    "@SF_UI_DW_LIVE_DISCONNECTED",
    "@SF_UI_DW_LIVE_CERT_FAILED",
    "BD_LOBBY_CONNECTED",
    "DW_LOBBY_CONNECTED",
    "DW_LOBBY_ERROR",
    "dwLogonStart",
    "BD_LOBBY_PROTOCOL_VERSION_FAILURE",
    "BD_LOBBY_INTERNAL_FAILURE",
    "BD_MAX_ERROR_CODE",
    "Unknown bdLobbyErrorCode",
    "BD_NOT_CONNECTED",
    "BD_SEND_FAILED",
    "cppOnDWConnected",
    "cppOnDWDisconnected",
    "title_id",
    "tencent_ticket",
]


def load_sections(pe):
    out = []
    for s in pe.sections:
        out.append(
            {
                "name": s.Name.rstrip(b"\x00").decode("latin-1"),
                "va": s.VirtualAddress,
                "vsize": s.Misc_VirtualSize,
                "raw": s.PointerToRawData,
                "rawsize": s.SizeOfRawData,
                "chars": s.Characteristics,
            }
        )
    return out


def off_to_va(secs, image_base, off):
    for s in secs:
        if s["raw"] <= off < s["raw"] + s["rawsize"]:
            return image_base + s["va"] + (off - s["raw"]), s
    return None, None


def va_to_off(secs, image_base, va):
    for s in secs:
        if image_base + s["va"] <= va < image_base + s["va"] + s["rawsize"]:
            return s["raw"] + (va - image_base - s["va"]), s
    return None, None


def is_exec(sec):
    return bool(sec["chars"] & 0x20000000)


def find_strings(blob, secs, image_base):
    found = {}
    for name in ANCHORS:
        pat = name.encode("ascii")
        hits = []
        start = 0
        while True:
            i = blob.find(pat, start)
            if i < 0:
                break
            va, sec = off_to_va(secs, image_base, i)
            if va is not None:
                hits.append({"off": i, "va": va, "sec": sec["name"]})
            start = i + 1
        found[name] = hits
    return found


def scan_code_for_va(blob, secs, target_va):
    pat = struct.pack("<I", target_va)
    hits = []
    for s in secs:
        if not is_exec(s):
            continue
        raw = s["raw"]
        end = min(raw + s["rawsize"], len(blob))
        start = raw
        while True:
            i = blob.find(pat, start, end)
            if i < 0:
                break
            hits.append({"off": i, "va": None, "sec": s["name"], "secva": s["va"]})
            start = i + 1
    return hits


MD = None


def disasm_window(blob, secs, image_base, off, back=40, fwd=96):
    global MD
    if MD is None:
        MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        MD.detail = True
    start = max(0, off - back)
    chunk = blob[start: off + fwd]
    base_va = None
    for s in secs:
        if s["raw"] <= start < s["raw"] + s["rawsize"]:
            base_va = image_base + s["va"] + (start - s["raw"])
            break
    if base_va is None:
        return []
    out = []
    for insn in MD.disasm(chunk, base_va):
        out.append(
            {
                "va": insn.address,
                "bytes": insn.bytes.hex(),
                "mnemonic": insn.mnemonic,
                "op_str": insn.op_str,
                "size": insn.size,
            }
        )
    return out


def find_function_start(blob, secs, image_base, hit_va, limit=0x3000):
    """Heuristic: nearest preceding MSVC/Tencent prologue."""
    off, sec = va_to_off(secs, image_base, hit_va)
    if off is None:
        return None, None
    lo = max(sec["raw"], off - limit)
    pats = [b"\x55\x8b\xec", b"\x55\x89\xe5", b"\x6a\xff\x68", b"\x83\xec"]
    best = None
    for pat in pats:
        i = blob.rfind(pat, lo, off)
        if i >= 0 and (best is None or i > best):
            best = i
    if best is None:
        return None, None
    va, _ = off_to_va(secs, image_base, best)
    return va, best


def scan_pointer_tables(blob, secs, target_va):
    """Find 4-byte LE target VA anywhere in non-exec sections (pointer tables)."""
    pat = struct.pack("<I", target_va)
    hits = []
    for s in secs:
        if is_exec(s):
            continue
        raw = s["raw"]
        end = min(raw + s["rawsize"], len(blob))
        start = raw
        while True:
            i = blob.find(pat, start, end)
            if i < 0:
                break
            va, _ = off_to_va(secs, image_base, i)
            hits.append({"off": i, "va": va, "sec": s["name"]})
            start = i + 1
    return hits


def main():
    with open(EXE, "rb") as fh:
        blob = fh.read()
    pe = pefile.PE(EXE, fast_load=True)
    image_base = pe.OPTIONAL_HEADER.ImageBase
    secs = load_sections(pe)
    pe.close()

    print("ImageBase 0x%08X" % image_base)
    found = find_strings(blob, secs, image_base)

    for name, hits in found.items():
        print("=" * 78)
        print("ANCHOR %s  (%d occurrence(s))" % (name, len(hits)))
        for h in hits:
            print("  str @ off=0x%08X va=0x%08X sec=%s" % (h["off"], h["va"], h["sec"]))
        for h in hits:
            target = h["va"]
            code_hits = scan_code_for_va(blob, secs, target)
            ptr_hits = scan_pointer_tables(blob, secs, target)
            print("  -> direct code refs: %d   data/pointer refs: %d" % (
                len(code_hits), len(ptr_hits)))
            for c in code_hits:
                fstart, foff = find_function_start(blob, secs, image_base, c["off"])
                print("     [code] off=0x%08X sec=%s func~0x%s" % (
                    c["off"], c["sec"],
                    ("%08X" % fstart) if fstart else "?"))
                for insn in disasm_window(blob, secs, image_base, c["off"], back=24, fwd=48):
                    mark = " <=" if insn["va"] == off_to_va(secs, image_base, c["off"])[0] else ""
                    print("        0x%08X  %-22s %s%s" % (
                        insn["va"], insn["bytes"], insn["mnemonic"] + " " + insn["op_str"], mark))
            for p in ptr_hits:
                print("     [data] off=0x%08X va=0x%08X sec=%s" % (p["off"], p["va"], p["sec"]))


if __name__ == "__main__":
    main()
