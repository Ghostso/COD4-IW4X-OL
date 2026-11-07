#!/usr/bin/env python3
"""Focused read-only probes used while reconstructing EX-067."""

from __future__ import annotations

import argparse
from pathlib import Path

from ex066_common import PEImage
from capstone.x86 import X86_OP_IMM, X86_OP_MEM


ROOT = Path(__file__).resolve().parent
CORE = ROOT / "WeGame" / "tcls" / "tcls_core.exe"
PROXY = ROOT / "COD OL" / "TenProxy.dll"
TCLS = ROOT / "COD OL" / "TCLS" / "Tenio" / "TCLS.dll"
CLIENTBASE = ROOT / "COD OL" / "TCLS" / "ClientBase.dll"
TPSVCBASE = ROOT / "COD OL" / "TCLS" / "tpsvcBase.dll"
BASE = ROOT / "COD OL" / "codoMP_client_shipRetailBase.dll"
IIPS = ROOT / "COD OL" / "IIPS" / "IIPSLaunchRestore.dll"
CLIENT = ROOT / "COD OL" / "TCLS" / "Client.exe"
CODO = ROOT / "COD OL" / "codoMP_client_shipRetail.exe"


def hexr(value: int | None) -> str:
    return "UNKNOWN" if value is None else f"0x{value:X}"


def print_window(image: PEImage, start: int, size: int) -> None:
    rva = start
    end = start + size
    while rva < end:
        insn = image.disasm_one(rva)
        if insn is None:
            rva += 1
            continue
        print(image.format_insn(insn))
        rva += insn.size


def print_function(image: PEImage, start: int, limit: int = 5000) -> None:
    for rva, insn in image.disassemble_function(start, limit=limit).items():
        print(image.format_insn(insn))


def find_function(image: PEImage, target: int) -> int | None:
    """Find the nearest preceding ret-free prologue governing target."""
    sec = image.section_for_rva(target)
    if not sec:
        return None
    lo = sec.rva
    candidates: list[int] = []
    for rva in range(lo, target + 1):
        insn = image.disasm_one(rva)
        if insn is None:
            continue
        b = insn.bytes
        if b.startswith(b"\x55\x8b\xec") or b.startswith(b"\x55\x89\xe5"):
            candidates.append(rva)
    for candidate in reversed(candidates):
        insns = image.disassemble_function(candidate, limit=12000)
        if target in insns:
            return candidate
    return candidates[-1] if candidates else None


def immediate_refs(image: PEImage, rva: int) -> list[int]:
    return image.immediate_refs(image.va(rva))


def call_sites(image: PEImage, target: int) -> list[int]:
    return [
        insn.address - image.base
        for insn in image.iter_code()
        if insn.mnemonic == "call"
        and insn.operands
        and insn.operands[0].type == X86_OP_IMM
        and insn.operands[0].imm == image.va(target)
    ]


def import_callers(image: PEImage, import_name: str) -> list[int]:
    result: list[int] = []
    iats = {
        rva
        for rva, (_dll, name) in image.imports.items()
        if name == import_name
    }
    for insn in image.iter_code():
        if insn.mnemonic != "call" or not insn.operands:
            continue
        op = insn.operands[0]
        if op.type == X86_OP_MEM and op.mem.base == 0:
            if image.rva(op.mem.disp) in iats:
                result.append(insn.address - image.base)
    return result


def dump_imports(image: PEImage) -> None:
    for rva, (dll, name) in sorted(image.imports.items()):
        print(f"0x{rva:X} {dll}!{name}")


def dump_exports(image: PEImage) -> None:
    for rva, name in sorted(image.exports.items()):
        print(f"0x{rva:X} {name}")


def dump_vtable(image: PEImage, rva: int, count: int = 64) -> None:
    for index in range(count):
        slot = rva + index * 4
        value = int.from_bytes(image.read(slot, 4), "little")
        target = image.rva(value)
        if target is None:
            break
        print(f"[{index:02d}] slot=0x{slot:X} value=0x{value:X} rva=0x{target:X}")


def dump_strings(image: PEImage, pattern: str) -> None:
    import re

    compiled = re.compile(re.escape(pattern), re.IGNORECASE)
    for rva, text in image.find_ascii_strings(compiled.pattern):
        print(f"ascii 0x{rva:X} {text!r}")
    for rva, text in image.find_wide_strings(compiled.pattern):
        print(f"utf16 0x{rva:X} {text!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command")
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    image_paths = {
        "core": CORE,
        "proxy": PROXY,
        "tcls": TCLS,
        "clientbase": CLIENTBASE,
        "tpsvcbase": TPSVCBASE,
        "base": BASE,
        "iips": IIPS,
        "client": CLIENT,
        "codo": CODO,
    }
    images = {
        name: PEImage(path)
        for name, path in image_paths.items()
    }

    if args.command == "imports":
        dump_imports(images[args.args[0]])
    elif args.command == "exports":
        dump_exports(images[args.args[0]])
    elif args.command == "vtable":
        image = images[args.args[0]]
        rva = int(args.args[1], 0)
        count = int(args.args[2], 0) if len(args.args) > 2 else 64
        dump_vtable(image, rva, count)
    elif args.command == "strings":
        image = images[args.args[0]]
        dump_strings(image, args.args[1])
    elif args.command == "find":
        image = images[args.args[0]]
        target = int(args.args[1], 0)
        fn = find_function(image, target)
        print(f"target=0x{target:X} function={hexr(fn)}")
    elif args.command == "function":
        image = images[args.args[0]]
        start = int(args.args[1], 0)
        print_function(image, start)
    elif args.command == "window":
        image = images[args.args[0]]
        start = int(args.args[1], 0)
        size = int(args.args[2], 0)
        print_window(image, start, size)
    elif args.command == "xref":
        image = images[args.args[0]]
        target = int(args.args[1], 0)
        print("calls", [hex(x) for x in call_sites(image, target)])
        print("imm", [hex(x) for x in immediate_refs(image, target)])
    elif args.command == "api":
        image = images[args.args[0]]
        print([hex(x) for x in import_callers(image, args.args[1])])
    else:
        raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
