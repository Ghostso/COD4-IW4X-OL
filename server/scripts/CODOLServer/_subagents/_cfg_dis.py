#!/usr/bin/env python3
"""Read-only disassembly helper for the CODOL live image (subagent B).

Usage:
  python _cfg_dis.py disasm 0xB88CC0 0xB88F80
  python _cfg_dis.py calls  0xB88CC0
  python _cfg_dis.py xref   0x331C5C0
  python _cfg_dis.py dump   0x331C5C0 0x40
"""

import struct
import sys
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone import CsError

IMAGE_BASE = 0x400000
DEFAULT_IMAGE = (
    Path(__file__).resolve().parents[1]
    / "_mainline"
    / "_dyn100_run_20260925_182324"
    / "live"
    / "image_best.bin"
)

MD = Cs(CS_ARCH_X86, CS_MODE_32)
MD.detail = True


def load_image(path=None):
    return Path(path or DEFAULT_IMAGE).read_bytes()


def off(va):
    return va - IMAGE_BASE


def u32(image, va):
    return struct.unpack_from("<I", image, off(va))[0]


def disasm(image, start, end):
    return list(MD.disasm(image[off(start):off(end)], start))


def render(image, start, end):
    lines = []
    for insn in disasm(image, start, end):
        line = "%08X  %-24s %s %s" % (
            insn.address,
            insn.bytes.hex(),
            insn.mnemonic,
            insn.op_str,
        )
        lines.append(line)
    return "\n".join(lines)


def direct_calls(image, target):
    hits = []
    for i in range(0, len(image) - 5):
        if image[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", image, i + 1)[0]
        if IMAGE_BASE + i + 5 + rel == target:
            hits.append(IMAGE_BASE + i)
    return hits


def imm_refs(image, target):
    needle = struct.pack("<I", target)
    hits = []
    start = 0
    while True:
        i = image.find(needle, start)
        if i < 0:
            return hits
        hits.append(IMAGE_BASE + i)
        start = i + 1


def dump(image, va, size):
    raw = image[off(va):off(va) + size]
    out = []
    for row in range(0, len(raw), 16):
        chunk = raw[row:row + 16]
        hexs = " ".join("%02X" % b for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append("%08X  %-47s  %s" % (va + row, hexs, asc))
    return "\n".join(out)


def cmd_disasm(image, argv):
    start, end = int(argv[0], 0), int(argv[1], 0)
    print(render(image, start, end))


def cmd_calls(image, argv):
    target = int(argv[0], 0)
    print("direct_calls_to_0x%08X:" % target)
    for va in direct_calls(image, target):
        print("  0x%08X" % va)
    print("immediate_refs_to_0x%08X:" % target)
    for va in imm_refs(image, target):
        print("  0x%08X" % va)


def cmd_xref(image, argv):
    cmd_calls(image, argv)


def cmd_dump(image, argv):
    va, size = int(argv[0], 0), int(argv[1], 0)
    print(dump(image, va, size))


def cmd_fields(image, argv):
    base, size = int(argv[0], 0), int(argv[1], 0)
    limit = base + size
    refs = {}
    try:
        insns = MD.disasm(image, IMAGE_BASE)
    except CsError:
        insns = []
    for insn in insns:
        targets = []
        for operand in insn.operands:
            if operand.type == X86_OP_MEM:
                mem = operand.mem
                if mem.base == 0 and mem.index == 0 and base <= mem.disp < limit:
                    targets.append(mem.disp)
            elif operand.type == X86_OP_IMM and base <= operand.imm < limit:
                targets.append(operand.imm)
        for target in sorted(set(targets)):
            refs.setdefault(target, []).append(
                "%08X  %-24s %s %s"
                % (
                    insn.address,
                    insn.bytes.hex(),
                    insn.mnemonic,
                    insn.op_str,
                )
            )
    for target in sorted(refs):
        print("OFFSET +0x%03X  VA 0x%08X" % (target - base, target))
        for line in refs[target]:
            print("  " + line)


def main():
    argv = sys.argv[1:]
    image = load_image()
    command = argv[0]
    rest = argv[1:]
    if command == "disasm":
        cmd_disasm(image, rest)
    elif command in ("calls", "xref"):
        cmd_calls(image, rest)
    elif command == "dump":
        cmd_dump(image, rest)
    elif command == "fields":
        cmd_fields(image, rest)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
