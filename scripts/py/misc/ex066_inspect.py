"""Disposable EX-066 inspection helpers.

This script is intentionally narrow.  The final reproducible artifact
generator is ex066_analyze.py.
"""

from __future__ import annotations

import argparse
import re
import sys

from ex066_common import PEImage


TCLS = "WeGame/tcls/tcls_core.exe"


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")


def show_window(image: PEImage, site: int, before: int, after: int) -> None:
    print("=" * 78)
    print("site=0x%X function=0x%X" % (
        site, image.find_function_start(site)
    ))
    print("=" * 78)
    for insn in image.instruction_window(site, before, after):
        print(image.format_insn(insn))


def show_range(image: PEImage, start: int, end: int) -> None:
    for insn in image.iter_code(start, end):
        print(image.format_insn(insn))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=TCLS)
    parser.add_argument("--range", nargs=2, type=lambda x: int(x, 0))
    parser.add_argument("--sites", nargs="+", type=lambda x: int(x, 0))
    parser.add_argument("--callers-of", nargs="+", type=lambda x: int(x, 0))
    parser.add_argument("--refs-of", nargs="+", type=lambda x: int(x, 0))
    parser.add_argument("--import-callers", nargs="+")
    parser.add_argument("--strings")
    parser.add_argument("--vtable", nargs="+", type=lambda x: int(x, 0))
    parser.add_argument("--before", type=lambda x: int(x, 0), default=0x80)
    parser.add_argument("--after", type=lambda x: int(x, 0), default=0x120)
    parser.add_argument("--callers", action="store_true")
    args = parser.parse_args()

    image = PEImage(args.module)
    if args.range:
        show_range(image, *args.range)
    for site in args.sites or []:
        show_window(image, site, args.before, args.after)
        if args.callers:
            print("callers:", [hex(x) for x in image.callers_to(site)])
    for target in args.callers_of or []:
        print("callers of 0x%X: %s" % (
            target, [hex(x) for x in image.callers_to(target)]
        ))
    for target in args.refs_of or []:
        print("refs to RVA 0x%X: %s" % (
            target, [hex(x) for x in image.immediate_refs(image.va(target))]
        ))
    for name in args.import_callers or []:
        matches = [
            (rva, dll, symbol)
            for rva, (dll, symbol) in image.imports.items()
            if name.lower() in symbol.lower()
        ]
        for rva, dll, symbol in matches:
            refs = image.immediate_refs(image.va(rva))
            print("%s!%s IAT=0x%X callers/refs=%s" % (
                dll, symbol, rva, [hex(x) for x in refs]
            ))
    if args.strings:
        pattern = re.compile(args.strings, re.IGNORECASE)
        for rva, text in image.find_ascii_strings(pattern.pattern):
            print("ascii 0x%X %r" % (rva, text))
        for rva, text in image.find_wide_strings(pattern.pattern):
            print("utf16 0x%X %r" % (rva, text))
    for rva in args.vtable or []:
        raw = image.read(rva, 0x200)
        ptrs = [
            int.from_bytes(raw[i:i + 4], "little")
            for i in range(0, len(raw) - 3, 4)
        ]
        print("vtable RVA 0x%X:" % rva)
        for index, ptr in enumerate(ptrs):
            target = image.rva(ptr)
            if target is None or not image.is_executable(target):
                break
            print("  [%02d] 0x%08X -> sub_%X" % (index, ptr, target))


if __name__ == "__main__":
    main()
