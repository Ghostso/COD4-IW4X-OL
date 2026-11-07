# -*- coding: utf-8 -*-
"""CODOL Booking P1/P2 static tracing helpers.

Read-only. Never writes the image or Golden tree.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs
from capstone.x86 import (  # noqa: F401
    X86_OP_IMM,
    X86_OP_MEM,
    X86_OP_REG,
)


ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
IMG_PATH = (
    ROOT
    / "CODOLServer"
    / "_mainline"
    / "_dyn100_run_20260925_182324"
    / "live"
    / "image_best.bin"
)
BASE = 0x400000


def load_image() -> tuple[bytes, Cs]:
    data = IMG_PATH.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    return data, md


def disasm(img: bytes, start: int, end: int, md: Cs) -> list:
    assert start >= BASE and end > start
    off = start - BASE
    code = img[off : off + (end - start)]
    return list(md.disasm(code, start))


def print_disasm(img: bytes, md: Cs, start: int, end: int) -> None:
    print(f"=== 0x{start:08X} .. 0x{end:08X} ===")
    for ins in disasm(img, start, end, md):
        print(
            f"0x{ins.address:08X}  {ins.bytes.hex():<22} "
            f"{ins.mnemonic} {ins.op_str}"
        )


def find_refs(data: bytes, value: int) -> list[int]:
    return [BASE + i for i in range(len(data) - 3) if data[i : i + 4] == struct.pack("<I", value)]


def find_direct_calls(data: bytes, target: int) -> list[int]:
    out = []
    for i in range(len(data) - 5):
        if data[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", data, i + 1)[0]
        if BASE + i + 5 + rel == target:
            out.append(BASE + i)
    return out


def find_indirect_callers(data: bytes, md: Cs, disp: int, limit: int = 0) -> list[dict]:
    """Find mov reg,[reg+disp32] / mov reg,[reg+disp32] ; call reg pairs.

    This is deliberately syntax-based rather than fixed opcode based.
    It scans candidate displacement hits, validates that the instruction
    starting 2 bytes earlier is a memory load, then disassembles the next few
    instructions and requires a call to the loaded register.
    """
    pattern = struct.pack("<I", disp)
    out: list[dict] = []
    seen: set[int] = set()
    pos = 0
    while True:
        hit = data.find(pattern, pos)
        if hit < 0:
            break
        pos = hit + 1
        if hit < 2:
            continue
        va = BASE + hit
        b1, b0 = data[hit - 2], data[hit - 1]
        if not (b1 == 0x8B and 0x80 <= b0 <= 0xBF and (b0 & 7) != 4):
            continue
        start = va - 2
        if start in seen:
            continue
        insns = disasm(data, start, start + 0x20, md)
        if not insns:
            continue
        first = insns[0]
        if first.address != start or first.mnemonic != "mov":
            continue
        if not first.operands or first.operands[0].type != X86_OP_REG:
            continue
        dst = first.reg_name(first.operands[0].reg)
        for nxt in insns[1:4]:
            if nxt.mnemonic == "call" and dst in nxt.op_str:
                seen.add(start)
                out.append(
                    {
                        "load_va": start,
                        "load": f"{first.mnemonic} {first.op_str}",
                        "call_va": nxt.address,
                        "call": f"{nxt.mnemonic} {nxt.op_str}",
                    }
                )
                break
        if limit and len(out) >= limit:
            break
    return out


def cmd_disasm(args) -> None:
    img, md = load_image()
    print_disasm(img, md, args.start, args.end)


def cmd_refs(args) -> None:
    img, _ = load_image()
    for value in args.values:
        refs = find_refs(img, value)
        calls = find_direct_calls(img, value)
        print(
            f"0x{value:08X} refs={[hex(x) for x in refs] or 'none'} "
            f"direct_calls={[hex(x) for x in calls] or 'none'}"
        )


def cmd_vcall(args) -> None:
    img, md = load_image()
    for disp in args.disps:
        hits = find_indirect_callers(img, md, disp)
        print(f"disp=0x{disp:X}: {len(hits)} register-sourced indirect calls")
        for h in hits:
            print(
                f"  0x{h['load_va']:08X}  {h['load']:<42} "
                f"-> 0x{h['call_va']:08X}  {h['call']}"
            )


def cmd_vtable(args) -> None:
    img, _ = load_image()
    off = args.vtable - BASE
    print(f"vtable @0x{args.vtable:X} (base 0x{args.vtable:X})")
    for n in range(args.count):
        slot = off + n * 4
        if slot + 4 > len(img):
            break
        value = struct.unpack_from("<I", img, slot)[0]
        mark = ""
        if value in set(args.highlight):
            mark = "  <==="
        print(f"+0x{n*4:03X}  [{n:02d}]  0x{value:08X}{mark}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("disasm")
    p.add_argument("start", type=lambda s: int(s, 0))
    p.add_argument("end", type=lambda s: int(s, 0))
    p.set_defaults(func=cmd_disasm)

    p = sub.add_parser("refs")
    p.add_argument("values", nargs="+", type=lambda s: int(s, 0))
    p.set_defaults(func=cmd_refs)

    p = sub.add_parser("vcall")
    p.add_argument("disps", nargs="+", type=lambda s: int(s, 0))
    p.set_defaults(func=cmd_vcall)

    p = sub.add_parser("vtable")
    p.add_argument("vtable", type=lambda s: int(s, 0))
    p.add_argument("count", nargs="?", type=int, default=100)
    p.add_argument("highlight", nargs="*", type=lambda s: int(s, 0))
    p.set_defaults(func=cmd_vtable)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
