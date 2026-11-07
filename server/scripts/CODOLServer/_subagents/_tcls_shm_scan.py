#!/usr/bin/env python3
"""Read-only TCLS shared-memory chain scanner for the CODOL runtime image.

Pure static analysis. No process is launched, no file is written outside the
report directory, no network state is touched.

The runtime image is a decrypted PE snapshot of the game module
(codoMP_client_shipRetail.exe) loaded at base 0x400000:

    offset = VA - 0x400000

Only ASCII output is produced so the script is safe on a GBK console.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

import capstone
import pefile

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="backslashreplace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
IMAGE = (PROJECT / "CODOLServer" / "_mainline"
         / "_dyn100_run_20260925_182324" / "live" / "image_best.bin")

IMAGE_BASE = 0x400000
CFG_BLOCK = 0x331C5C0
CFG_SIZE = 0xD40


def load_image(path: Path = IMAGE):
    data = path.read_bytes()
    pe = pefile.PE(str(path), fast_load=True)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    return pe, data, md


def sections(pe):
    out = []
    for sec in pe.sections:
        out.append({
            "name": sec.Name.rstrip(b"\x00").decode("latin1"),
            "va": sec.VirtualAddress,
            "vsize": sec.Misc_VirtualSize,
            "raw": sec.PointerToRawData,
            "rawsize": sec.SizeOfRawData,
        })
    return out


def read_va(data, va, size):
    off = va - IMAGE_BASE
    if off < 0 or off + size > len(data):
        return None
    return data[off:off + size]


def cstr(data, va, limit=512):
    raw = read_va(data, va, limit)
    if raw is None:
        return None
    end = raw.find(b"\x00")
    if end < 0:
        end = len(raw)
    try:
        return raw[:end].decode("gbk")
    except UnicodeDecodeError:
        return raw[:end].decode("latin1", "replace")


def wstr(data, va, limit=512):
    raw = read_va(data, va, limit * 2)
    if raw is None:
        return None
    out = []
    for i in range(0, len(raw) - 1, 2):
        ch = raw[i] | (raw[i + 1] << 8)
        if ch == 0:
            break
        out.append(chr(ch))
    return "".join(out)


def cmd_find(args):
    pe, data, md = load_image()
    needles = [n.encode("ascii") for n in args.needle]
    report = {"image": str(IMAGE), "size": len(data),
              "sections": sections(pe), "hits": []}
    for needle in needles:
        wide = b"".join(bytes([c, 0]) for c in needle)
        for label, pat in (("ascii", needle), ("utf16", wide)):
            pos = 0
            count = 0
            while True:
                pos = data.find(pat, pos)
                if pos < 0:
                    break
                count += 1
                if len(report["hits"]) < 4000:
                    report["hits"].append({
                        "needle": needle.decode("latin1"),
                        "enc": label,
                        "va": hex(IMAGE_BASE + pos),
                        "offset": hex(pos),
                    })
                pos += 1
            print("HIT %-34s %-6s count=%d" % (needle.decode("latin1"), label, count))
    out = HERE / "_tcls_find.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("WROTE", out)


def cmd_xrefs(args):
    """Find absolute (imm32) references to a VA inside the image."""
    pe, data, md = load_image()
    for spec in args.va:
        va = int(spec, 16)
        needle = struct.pack("<I", va)
        hits = []
        pos = 0
        while True:
            pos = data.find(needle, pos)
            if pos < 0:
                break
            hits.append(pos)
            pos += 1
        print("XREF va=0x%08X count=%d" % (va, len(hits)))
        for off in hits[:args.limit]:
            print("   at 0x%08X" % (IMAGE_BASE + off))


def cmd_disasm(args):
    pe, data, md = load_image()
    start = int(args.start, 16)
    end = int(args.end, 16)
    raw = read_va(data, start, end - start)
    if raw is None:
        raise SystemExit("range outside image: 0x%X-0x%X" % (start, end))
    off = 0
    while off < len(raw):
        insn = next(md.disasm(raw[off:], start + off), None)
        if insn is None:
            off += 1
            continue
        note = ""
        if insn.mnemonic in ("call", "jmp") and insn.operands:
            op = insn.operands[0]
            if op.type == capstone.x86.X86_OP_IMM:
                tgt = op.imm
                s = cstr(data, tgt, 96)
                if s and all(32 <= ord(c) < 127 for c in s) and len(s) > 3:
                    note = '  ; "%s"' % s
        print("0x%08X  %-22s %-7s %s%s" % (
            insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str, note))
        off += insn.size


def cmd_layout(args):
    """Walk the writers of the 0xD40 configuration block."""
    pe, data, md = load_image()
    block = CFG_BLOCK
    raw = read_va(data, block, CFG_SIZE)
    print("CFG block VA 0x%08X size 0x%X offset_in_image 0x%X" %
          (block, CFG_SIZE, block - IMAGE_BASE))
    print("static bytes present:", raw is not None)
    # find imm32 references to the block base and each +0x18 slot
    for off in (0x00, 0x04, 0x18, 0x98, 0x9C, 0xB0, 0x538):
        va = block + off
        needle = struct.pack("<I", va)
        hits = []
        pos = 0
        while True:
            pos = data.find(needle, pos)
            if pos < 0:
                break
            hits.append(IMAGE_BASE + pos)
            pos += 1
        print("  field +0x%03X VA 0x%08X imm32_refs=%d %s" %
              (off, va, len(hits),
               " ".join("0x%08X" % h for h in hits[:12])))


def cmd_strings(args):
    pe, data, md = load_image()
    for spec in args.va:
        va = int(spec, 16)
        print("ASCII  0x%08X %r" % (va, cstr(data, va)))
        print("UTF16  0x%08X %r" % (va, wstr(data, va)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("find")
    p.add_argument("needle", nargs="+")
    p.set_defaults(func=cmd_find)

    p = sub.add_parser("xrefs")
    p.add_argument("va", nargs="+")
    p.add_argument("--limit", type=int, default=40)
    p.set_defaults(func=cmd_xrefs)

    p = sub.add_parser("disasm")
    p.add_argument("start")
    p.add_argument("end")
    p.set_defaults(func=cmd_disasm)

    p = sub.add_parser("layout")
    p.set_defaults(func=cmd_layout)

    p = sub.add_parser("strings")
    p.add_argument("va", nargs="+")
    p.set_defaults(func=cmd_strings)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
