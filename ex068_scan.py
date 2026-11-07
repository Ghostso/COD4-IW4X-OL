#!/usr/bin/env python3
"""Focused read-only scans for the EX-068 native protocol boundary."""

from __future__ import annotations

import argparse
from pathlib import Path

from capstone.x86 import X86_OP_IMM, X86_OP_MEM

from ex066_common import PEImage


ROOT = Path(__file__).resolve().parent
MODULES = {
    "codo": ROOT / "COD OL" / "codoMP_client_shipRetail.exe",
    "base": ROOT / "COD OL" / "codoMP_client_shipRetailBase.dll",
    "proxy": ROOT / "COD OL" / "TenProxy.dll",
    "clientbase": ROOT / "COD OL" / "TCLS" / "ClientBase.dll",
    "client": ROOT / "COD OL" / "TCLS" / "Client.exe",
    "tcls": ROOT / "COD OL" / "TCLS" / "Tenio" / "TCLS.dll",
    "core": ROOT / "WeGame" / "tcls" / "tcls_core.exe",
    "iips_restore": ROOT / "COD OL" / "IIPS" / "IIPSLaunchRestore.dll",
    "iips": ROOT / "COD OL" / "IIPS" / "iips.dll",
}


def data_hits(image: PEImage, needle: bytes) -> list[tuple[int, int]]:
    hits: list[tuple[int, int]] = []
    start = 0
    while True:
        offset = image.data.find(needle, start)
        if offset < 0:
            break
        pair = image.raw_to_rva(offset)
        if pair is not None:
            hits.append((pair[0], pair[1]))
        start = offset + 1
    return hits


def value_refs(image: PEImage, target_rva: int) -> list[tuple[int, int, str]]:
    values = {
        "va": image.va(target_rva),
        "rva": target_rva,
        "raw": image.rva_to_raw(target_rva) or -1,
    }
    hits: list[tuple[int, int, str]] = []
    for name, value in values.items():
        if value < 0 or value > 0xFFFFFFFF:
            continue
        needle = int(value).to_bytes(4, "little")
        for rva, section in data_hits(image, needle):
            hits.append((rva, value, f"{name}:{section}"))
    return sorted(set(hits))


def immediate_hits(image: PEImage, value: int) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    for insn in image.iter_code():
        for operand in insn.operands:
            if operand.type == X86_OP_IMM and operand.imm == value:
                hits.append(
                    (
                        insn.address - image.base,
                        insn.mnemonic,
                        insn.op_str,
                    )
                )
                break
    return hits


def iat_calls(image: PEImage, names: set[str]) -> list[tuple[int, str, int]]:
    by_slot = {
        slot: name
        for slot, (_dll, name) in image.imports.items()
        if name in names
    }
    hits: list[tuple[int, str, int]] = []
    for insn in image.iter_code():
        if insn.mnemonic not in ("call", "jmp") or not insn.operands:
            continue
        operand = insn.operands[0]
        if operand.type != X86_OP_MEM or operand.mem.base != 0:
            continue
        slot = image.rva(operand.mem.disp)
        if slot in by_slot:
            site = insn.address - image.base
            hits.append((site, by_slot[slot], image.find_function_start(site)))
    return hits


def print_hits(
    label: str,
    hits: list[tuple[int, str, str]],
    image: PEImage,
    describe: bool,
) -> None:
    print(f"{label}: {len(hits)}")
    for rva, mnemonic, op_str in hits:
        section = image.section_for_rva(rva)
        function = image.find_function_start(rva)
        print(
            f"  site=0x{rva:X} function=0x{function:X} "
            f"section={section.name if section else '?'} {mnemonic} {op_str}"
        )
        if describe:
            for insn in image.instruction_window(rva, 0x20, 0x30):
                print(f"    {image.format_insn(insn)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("module", choices=MODULES)
    parser.add_argument("--string", action="append", default=[])
    parser.add_argument("--eval", action="append", type=lambda value: int(value, 0))
    parser.add_argument("--rva-ref", action="append", type=lambda value: int(value, 0))
    parser.add_argument("--around", action="append", type=lambda value: int(value, 0))
    parser.add_argument(
        "--function",
        action="append",
        type=lambda value: int(value, 0),
    )
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--max", type=int, default=200)
    args = parser.parse_args()

    image = PEImage(MODULES[args.module])
    print(
        f"module={args.module} base=0x{image.base:X} size=0x{image.size:X} "
        f"entry=0x{image.entry:X}"
    )

    for text in args.string:
        needle = text.encode("ascii")
        hits = data_hits(image, needle)
        print(f"STRING {text!r}: {len(hits)}")
        for rva, section in hits[: args.max]:
            refs = value_refs(image, rva)
            print(f"  rva=0x{rva:X} section={section} refs={len(refs)}")
            for ref_rva, value, kind in refs[: args.max]:
                ref_section = image.section_for_rva(ref_rva)
                print(
                    f"    ref=0x{ref_rva:X} "
                    f"section={ref_section.name if ref_section else '?'} {kind}"
                )

    for value in args.eval or []:
        print_hits(
            f"IMMEDIATE 0x{value:X}",
            immediate_hits(image, value),
            image,
            args.describe,
        )

    for target in args.rva_ref or []:
        hits = value_refs(image, target)
        print(f"RVA REF 0x{target:X}: {len(hits)}")
        for rva, value, kind in hits[: args.max]:
            section = image.section_for_rva(rva)
            print(
                f"  ref=0x{rva:X} section={section.name if section else '?'} "
                f"value=0x{value:X} {kind}"
            )

    for target in args.around or []:
        print(f"AROUND 0x{target:X}")
        section = image.section_for_rva(target)
        print(
            f"  section={section.name if section else '?'} "
            f"raw={image.rva_to_raw(target)} "
            f"function=0x{image.find_function_start(target):X}"
        )
        for insn in image.instruction_window(target, 0x30, 0x80):
            print(f"    {image.format_insn(insn)}")

    for target in args.function or []:
        insns = image.disassemble_function(target, limit=20000)
        print(
            f"FUNCTION 0x{target:X}: {len(insns)} instructions "
            f"range=0x{min(insns):X}-0x{max(insns):X}"
        )
        for insn in insns.values():
            print(f"    {image.format_insn(insn)}")

    calls = iat_calls(
        image,
        {
            "LoadLibraryA",
            "LoadLibraryW",
            "LoadLibraryExA",
            "LoadLibraryExW",
            "GetProcAddress",
            "LdrLoadDll",
        },
    )
    print(f"DYNAMIC LOADER CALLS: {len(calls)}")
    for site, name, function in calls[: args.max]:
        section = image.section_for_rva(site)
        print(
            f"  site=0x{site:X} function=0x{function:X} "
            f"section={section.name if section else '?'} {name}"
        )
        if args.describe:
            for ref in image.callers_to(function)[:20]:
                print(f"    caller=0x{ref:X}")


if __name__ == "__main__":
    main()
