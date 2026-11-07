#!/usr/bin/env python3
"""Read-only static probe for EX-068 native-to-TenProxy edges.

The CODOL images mix ordinary PE sections with TP3/TVM0 virtualized regions.
This script therefore reports both raw-file-backed and virtual-only evidence
instead of treating a decoded instruction as proof that a call is reachable.
"""

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

ANCHORS = (
    b"TenProxy.dll",
    b"Invoke",
    b"TCLS_SHAREDMEMEMORY",
    b"TenP_TS_",
    b"LdrLoadDll",
    b"LoadLibraryA",
    b"LoadLibraryW",
    b"LoadLibraryExA",
    b"LoadLibraryExW",
    b"GetProcAddress",
    b"GameSignature",
    b"JumpSignature",
    b"GetCurrentProcessId",
    b"OpenFileMappingW",
    b"CreateFileMappingW",
)


def anchor_rvas(image: PEImage, needle: bytes) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    start = 0
    while True:
        pos = image.data.find(needle, start)
        if pos < 0:
            break
        pair = image.raw_to_rva(pos)
        if pair is not None:
            hits.append(pair)
        start = pos + 1
    return hits


def pointer_refs(image: PEImage, target_rva: int, value_width: int = 4) -> list[int]:
    return image.immediate_refs(image.va(target_rva), value_width)


def containing_function(image: PEImage, site: int) -> int:
    return image.find_function_start(site)


def describe(image: PEImage, site: int, before: int = 0x30, after: int = 0x50) -> list[str]:
    lines: list[str] = []
    for insn in image.instruction_window(site, before=before, after=after):
        lines.append(image.format_insn(insn))
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("module", choices=MODULES)
    parser.add_argument("--anchor", action="append", default=[])
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--max-refs", type=int, default=40)
    args = parser.parse_args()

    image = PEImage(MODULES[args.module])
    print(f"module={args.module} base=0x{image.base:X} size=0x{image.size:X}")
    selected = tuple(value.encode("ascii") for value in args.anchor) or ANCHORS
    seen_refs: set[tuple[int, int]] = set()
    for needle in selected:
        hits = anchor_rvas(image, needle)
        print(f"ANCHOR {needle.decode(errors='replace')!r} occurrences={len(hits)}")
        for target, section in hits[: args.max_refs]:
            refs = pointer_refs(image, target)
            print(f"  rva=0x{target:X} section={section} direct_refs={len(refs)}")
            for ref in refs[: args.max_refs]:
                key = (target, ref)
                if key in seen_refs:
                    continue
                seen_refs.add(key)
                sec = image.section_for_rva(ref)
                fn = containing_function(image, ref)
                print(
                    f"    ref=0x{ref:X} section={sec.name if sec else '?'} "
                    f"function=0x{fn:X}"
                )
                if args.describe:
                    for line in describe(image, ref):
                        print(f"      {line}")
        if len(hits) > args.max_refs:
            print(f"  ... {len(hits) - args.max_refs} more occurrences")


if __name__ == "__main__":
    main()
