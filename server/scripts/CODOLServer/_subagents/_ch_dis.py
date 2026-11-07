"""Read-only disassembler for the CODOL runtime-decrypted image (subagent C2).

Usage:
  python _ch_dis.py disasm 0xB88CC0 0xB88F70
  python _ch_dis.py calls  0xB9A9E0
  python _ch_dis.py xref   0x81A76A8
  python _ch_dis.py dump   0x331C5D8 0x40
  python _ch_dis.py bytes  0xB88CC0 0x20

The image is the runtime-decrypted process image captured from live memory.
It is mapped at base 0x400000, so file offset = VA - 0x400000 for the .tp3
region that is actually present in the file.
"""

import json
import os
import re
import struct
import sys

import capstone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
IMAGE = os.path.join(
    REPO,
    "CODOLServer",
    "_mainline",
    "_dyn100_run_20260925_182324",
    "live",
    "image_best.bin",
)

IMAGE_BASE = 0x400000
IMAGE_SIZE = 0x0A65000  # actual file size, NOT SizeOfImage 0xE659000


def load_image():
    with open(IMAGE, "rb") as fh:
        return fh.read()


def va_to_off(va):
    off = va - IMAGE_BASE
    if off < 0 or off >= IMAGE_SIZE:
        raise ValueError(
            "VA %#x is outside the bytes present in the image (max VA %#x)"
            % (va, IMAGE_BASE + IMAGE_SIZE - 1)
        )
    return off


def parse_int(text):
    text = text.strip()
    return int(text, 16) if text.lower().startswith("0x") else int(text, 10)


def disasm(start, end, image=None):
    if image is None:
        image = load_image()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = False
    data = image[va_to_off(start): va_to_off(end)]
    out = []
    for insn in md.disasm(data, start):
        out.append((insn.address, insn.size, insn.mnemonic, insn.op_str))
    return out


def fmt(rows):
    lines = []
    for addr, size, mn, ops in rows:
        raw = " ".join("%02x" % b for b in load_image()[va_to_off(addr): va_to_off(addr) + size])
        lines.append("%08X  %-20s %-8s %s" % (addr, raw, mn, ops))
    return "\n".join(lines)


def calls_in(start, end):
    rows = disasm(start, end)
    out = []
    for addr, size, mn, ops in rows:
        if mn in ("call", "jmp") and re.match(r"^0x[0-9a-f]+$", ops):
            out.append((addr, mn, int(ops, 16)))
    return out


def xrefs_to(target, image=None):
    """Find absolute references to a VA (mov/push/cmp with imm32)."""
    if image is None:
        image = load_image()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    hits = []
    data = image[:IMAGE_SIZE]
    pat = struct.pack("<I", target)
    idx = data.find(pat)
    while idx != -1:
        va = IMAGE_BASE + idx
        hits.append(va)
        idx = data.find(pat, idx + 1)
    return sorted(hits)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1].lower()
    if cmd == "disasm":
        start = parse_int(sys.argv[2])
        end = parse_int(sys.argv[3]) if len(sys.argv) > 3 else start + 0x100
        print(fmt(disasm(start, end)))
    elif cmd == "calls":
        start = parse_int(sys.argv[2])
        end = parse_int(sys.argv[3]) if len(sys.argv) > 3 else start + 0x400
        for addr, mn, tgt in calls_in(start, end):
            print("%08X  %-5s 0x%08X" % (addr, mn, tgt))
    elif cmd == "xref":
        target = parse_int(sys.argv[2])
        for va in xrefs_to(target):
            print("raw imm32 at %08X" % va)
    elif cmd == "dump":
        start = parse_int(sys.argv[2])
        size = parse_int(sys.argv[3]) if len(sys.argv) > 3 else 0x40
        image = load_image()
        off = va_to_off(start)
        blob = image[off:off + size]
        for i in range(0, len(blob), 16):
            chunk = blob[i:i + 16]
            hexs = " ".join("%02x" % b for b in chunk)
            txt = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            print("%08X  %-47s  %s" % (start + i, hexs, txt))
    elif cmd == "bytes":
        start = parse_int(sys.argv[2])
        size = parse_int(sys.argv[3]) if len(sys.argv) > 3 else 0x20
        image = load_image()
        off = va_to_off(start)
        print(" ".join("%02x" % b for b in image[off:off + size]))
    else:
        print("unknown command %r" % cmd)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
