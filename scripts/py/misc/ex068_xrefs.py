#!/usr/bin/env python3
"""Targeted xref scanner for EX-068 strings, constants, and object offsets."""

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


def refs_to_value(image: PEImage, value: int, width: int = 4) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    if not 0 <= value <= (1 << (width * 8)) - 1:
        return hits
    needle = value.to_bytes(width, "little")
    start = 0
    while True:
        offset = image.data.find(needle, start)
        if offset < 0:
            break
        pair = image.raw_to_rva(offset)
        if pair is not None:
            hits.append(pair)
        start = offset + 1
    return hits


def refs_to_string(image: PEImage, value: str) -> list[dict[str, object]]:
    needle = value.encode("utf-8")
    hits: list[dict[str, object]] = []
    start = 0
    while True:
        offset = image.data.find(needle, start)
        if offset < 0:
            break
        pair = image.raw_to_rva(offset)
        if pair is not None:
            target, section = pair
            data_refs = refs_to_value(image, image.va(target))
            rva_refs = refs_to_value(image, target)
            hits.append(
                {
                    "target": target,
                    "section": section,
                    "va_refs": [rva for rva, _ in data_refs],
                    "rva_refs": [rva for rva, _ in rva_refs],
                }
            )
        start = offset + 1
    return hits


def displacement_hits(image: PEImage, value: int) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for insn in image.iter_code():
        for operand in insn.operands:
            if (
                operand.type == X86_OP_MEM
                and operand.mem.disp == value
                and operand.mem.base != 0
            ):
                hits.append(
                    (
                        insn.address - image.base,
                        f"{insn.mnemonic} {insn.op_str}",
                    )
                )
                break
    return hits


def immediate_hits(image: PEImage, value: int) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for insn in image.iter_code():
        for operand in insn.operands:
            if operand.type == X86_OP_IMM and operand.imm == value:
                hits.append(
                    (
                        insn.address - image.base,
                        f"{insn.mnemonic} {insn.op_str}",
                    )
                )
                break
    return hits


def print_context(image: PEImage, site: int, before: int, after: int) -> None:
    for insn in image.instruction_window(site, before, after):
        try:
            print(f"      {image.format_insn(insn)}")
        except UnicodeEncodeError:
            print(
                f"      0x{insn.address - image.base:05X} "
                f"{insn.mnemonic} {insn.op_str.encode('ascii', 'backslashreplace').decode()}"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("module", choices=MODULES)
    parser.add_argument("--string", action="append", default=[])
    parser.add_argument("--value", action="append", type=lambda x: int(x, 0))
    parser.add_argument("--displacement", action="append", type=lambda x: int(x, 0))
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--max", type=int, default=80)
    args = parser.parse_args()

    image = PEImage(MODULES[args.module])
    print(f"module={args.module} base=0x{image.base:X} size=0x{image.size:X}")
    for text in args.string:
        print(f"STRING {text!r}")
        for hit in refs_to_string(image, text)[: args.max]:
            print(
                f"  target=0x{hit['target']:X} section={hit['section']} "
                f"va_refs={len(hit['va_refs'])} rva_refs={len(hit['rva_refs'])}"
            )
            for site in (hit["va_refs"] + hit["rva_refs"])[: args.max]:
                section = image.section_for_rva(site)
                print(
                    f"    ref=0x{site:X} function=0x{image.find_function_start(site):X} "
                    f"section={section.name if section else '?'}"
                )
                if args.describe:
                    print_context(image, site, 0x20, 0x50)
    for value in args.value or []:
        hits = immediate_hits(image, value)
        print(f"VALUE 0x{value:X}: {len(hits)}")
        for site, text in hits[: args.max]:
            section = image.section_for_rva(site)
            print(
                f"  site=0x{site:X} function=0x{image.find_function_start(site):X} "
                f"section={section.name if section else '?'} {text}"
            )
            if args.describe:
                print_context(image, site, 0x20, 0x50)
    for value in args.displacement or []:
        hits = displacement_hits(image, value)
        print(f"DISPLACEMENT +0x{value:X}: {len(hits)}")
        for site, text in hits[: args.max]:
            section = image.section_for_rva(site)
            print(
                f"  site=0x{site:X} function=0x{image.find_function_start(site):X} "
                f"section={section.name if section else '?'} {text}"
            )
            if args.describe:
                print_context(image, site, 0x20, 0x50)


if __name__ == "__main__":
    main()
