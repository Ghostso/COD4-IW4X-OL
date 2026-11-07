#!/usr/bin/env python3
"""Read-only disassembly helpers for the CODOL live image."""

import argparse
import json
import struct
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM


IMAGE_BASE = 0x400000
DEFAULT_IMAGE = (
    Path(__file__).resolve().parents[1]
    / "_mainline"
    / "_dyn100_run_20260925_182324"
    / "live"
    / "image_best.bin"
)


def va_to_offset(va):
    offset = va - IMAGE_BASE
    if offset < 0:
        raise ValueError("VA is below image base: 0x%08X" % va)
    return offset


def read_u32(image, va):
    offset = va_to_offset(va)
    if offset + 4 > len(image):
        raise ValueError("VA is outside image: 0x%08X" % va)
    return struct.unpack_from("<I", image, offset)[0]


def read_c_string(image, va, max_len=4096):
    offset = va_to_offset(va)
    if offset < 0 or offset >= len(image):
        return None
    end = image.find(b"\x00", offset, min(len(image), offset + max_len))
    if end < 0:
        return None
    raw = image[offset:end]
    try:
        return raw.decode("ascii")
    except UnicodeDecodeError:
        return None


def disassemble(image, start_va, end_va):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    start = va_to_offset(start_va)
    end = min(va_to_offset(end_va), len(image))
    return list(md.disasm(image[start:end], start_va))


def render(insns):
    lines = []
    for insn in insns:
        lines.append(
            "%08X  %-24s %s %s"
            % (
                insn.address,
                insn.bytes.hex(),
                insn.mnemonic,
                insn.op_str,
            )
        )
    return "\n".join(lines)


def find_direct_calls(image, target_va):
    matches = []
    for offset in range(0, len(image) - 4):
        if image[offset] != 0xE8:
            continue
        rel = struct.unpack_from("<i", image, offset + 1)[0]
        call_va = IMAGE_BASE + offset
        destination = call_va + 5 + rel
        if destination == target_va:
            matches.append(call_va)
    return matches


def find_immediate_refs(image, target_va):
    matches = []
    needle = struct.pack("<I", target_va)
    start = 0
    while True:
        offset = image.find(needle, start)
        if offset < 0:
            break
        matches.append(IMAGE_BASE + offset)
        start = offset + 1
    return matches


def find_vtable_calls(image, vtable_va):
    """Find indirect calls through slots at offsets +0x00 through +0xFF."""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    matches = []
    for insn in md.disasm(image, IMAGE_BASE):
        if insn.mnemonic != "call" or not insn.operands:
            continue
        operand = insn.operands[0]
        if operand.type != X86_OP_MEM:
            continue
        mem = operand.mem
        if mem.base != 0 or mem.index != 0:
            continue
        delta = mem.disp - vtable_va
        if 0 <= delta <= 0xFF and delta % 4 == 0:
            matches.append((insn.address, delta, "%s %s" % (insn.mnemonic, insn.op_str)))
    return matches


def dump_data(image, va, size):
    offset = va_to_offset(va)
    raw = image[offset : offset + size]
    lines = []
    for row in range(0, len(raw), 16):
        chunk = raw[row : row + 16]
        hex_part = " ".join("%02X" % value for value in chunk)
        asc_part = "".join(
            chr(value) if 32 <= value < 127 else "." for value in chunk
        )
        lines.append("%08X  %-47s  %s" % (va + row, hex_part, asc_part))
    return "\n".join(lines)


def command_disasm(args):
    image = Path(args.image).read_bytes()
    insns = disassemble(image, args.start, args.end)
    print(render(insns))
    print("instruction_count=%d" % len(insns))


def command_xrefs(args):
    image = Path(args.image).read_bytes()
    result = {
        "target": "0x%08X" % args.target,
        "direct_calls": ["0x%08X" % value for value in find_direct_calls(image, args.target)],
        "immediate_refs": [
            "0x%08X" % value for value in find_immediate_refs(image, args.target)
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))


def command_pointer(args):
    image = Path(args.image).read_bytes()
    pointer = read_u32(image, args.pointer_va)
    result = {
        "pointer_va": "0x%08X" % args.pointer_va,
        "value": "0x%08X" % pointer,
        "inside_image": IMAGE_BASE <= pointer < IMAGE_BASE + len(image),
    }
    if result["inside_image"]:
        result["value_u32"] = "0x%08X" % read_u32(image, pointer)
        result["value_string"] = read_c_string(image, pointer, 256)
    print(json.dumps(result, indent=2, sort_keys=True))


def command_dump(args):
    image = Path(args.image).read_bytes()
    print(dump_data(image, args.start, args.size))


def command_string(args):
    image = Path(args.image).read_bytes()
    value = read_c_string(image, args.va, args.max_len)
    if value is None:
        print("(not an ASCII NUL-terminated string)")
        return
    print(value)


def command_vtable(args):
    image = Path(args.image).read_bytes()
    slots = []
    for delta in range(0, args.size, 4):
        slot_va = args.vtable + delta
        try:
            pointer = read_u32(image, slot_va)
        except ValueError:
            break
        slots.append(
            {
                "offset": "+0x%02X" % delta,
                "slot_va": "0x%08X" % slot_va,
                "value": "0x%08X" % pointer,
                "inside_image": IMAGE_BASE <= pointer < IMAGE_BASE + len(image),
            }
        )
    print(json.dumps(slots, indent=2, sort_keys=True))


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default=str(DEFAULT_IMAGE))
    subparsers = parser.add_subparsers(dest="command", required=True)

    disasm_parser = subparsers.add_parser("disasm")
    disasm_parser.add_argument("start", type=lambda value: int(value, 0))
    disasm_parser.add_argument("end", type=lambda value: int(value, 0))
    disasm_parser.set_defaults(func=command_disasm)

    xrefs_parser = subparsers.add_parser("xrefs")
    xrefs_parser.add_argument("target", type=lambda value: int(value, 0))
    xrefs_parser.set_defaults(func=command_xrefs)

    pointer_parser = subparsers.add_parser("pointer")
    pointer_parser.add_argument("pointer_va", type=lambda value: int(value, 0))
    pointer_parser.set_defaults(func=command_pointer)

    dump_parser = subparsers.add_parser("dump")
    dump_parser.add_argument("start", type=lambda value: int(value, 0))
    dump_parser.add_argument("size", type=lambda value: int(value, 0))
    dump_parser.set_defaults(func=command_dump)

    string_parser = subparsers.add_parser("string")
    string_parser.add_argument("va", type=lambda value: int(value, 0))
    string_parser.add_argument("--max-len", type=int, default=4096)
    string_parser.set_defaults(func=command_string)

    vtable_parser = subparsers.add_parser("vtable")
    vtable_parser.add_argument("vtable", type=lambda value: int(value, 0))
    vtable_parser.add_argument("--size", type=lambda value: int(value, 0), default=0x80)
    vtable_parser.set_defaults(func=command_vtable)
    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
