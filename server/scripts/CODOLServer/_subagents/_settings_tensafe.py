#!/usr/bin/env python3
"""Read-only inspection of TenProxy.dll / TerSafe.dll for config provenance."""

import argparse
import json
import re
from pathlib import Path

import pefile
from capstone import CS_ARCH_X86, CS_MODE_32, Cs


GAME_DIR = Path(__file__).resolve().parents[2] / "COD OL"

KEYWORDS = [
    "Software\\",
    "Activision",
    "Call of Duty",
    "codol",
    "CODOL",
    "Tencent",
    "tencent",
    "RegOpenKey",
    "RegQuery",
    "RegGet",
    "host",
    "Host",
]


def load(path):
    return pefile.PE(str(path), fast_load=True)


def summarize_exports(path):
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
    )
    rows = []
    exports = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    if exports is None:
        return rows
    for symbol in exports.symbols:
        rows.append(
            {
                "name": symbol.name.decode("ascii", "replace")
                if symbol.name
                else None,
                "ordinal": symbol.ordinal,
                "rva": "0x%08X" % symbol.address,
                "va": "0x%08X" % (pe.OPTIONAL_HEADER.ImageBase + symbol.address),
            }
        )
    return rows


def scan_strings(path, min_len=4):
    raw = Path(path).read_bytes()
    pattern = re.compile(rb"[\x20-\x7e]{%d,}" % min_len)
    return [(match.start(), match.group().decode("ascii")) for match in pattern.finditer(raw)]


def find_strings(path, needles):
    hits = []
    for offset, value in scan_strings(path):
        for needle in needles:
            if needle.lower() in value.lower():
                hits.append({"offset": offset, "string": value, "needle": needle})
    return hits


def disassemble_export(path, symbol_name, count):
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
    )
    exports = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    if exports is None:
        raise SystemExit("no exports")
    target = None
    for symbol in exports.symbols:
        if symbol.name and symbol.name.decode("ascii", "replace") == symbol_name:
            target = pe.OPTIONAL_HEADER.ImageBase + symbol.address
            break
    if target is None:
        raise SystemExit("export not found: %s" % symbol_name)
    offset = pe.get_offset_from_rva(target - pe.OPTIONAL_HEADER.ImageBase)
    image = Path(path).read_bytes()[offset : offset + count * 16]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    lines = []
    for insn in md.disasm(image, target):
        lines.append(
            "%08X  %-20s %s %s"
            % (insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str)
        )
        if len(lines) >= count:
            break
    return lines


def list_sections(path):
    pe = pefile.PE(str(path), fast_load=True)
    rows = []
    for section in pe.sections:
        rows.append(
            {
                "name": section.Name.rstrip(b"\x00").decode("ascii", "replace"),
                "va": "0x%08X" % (pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress),
                "vsize": "0x%X" % section.Misc_VirtualSize,
                "raw": "0x%X" % section.SizeOfRawData,
                "entropy": round(section.get_entropy(), 3),
            }
        )
    return rows


def command_exports(args):
    print(json.dumps(summarize_exports(args.path), indent=2, sort_keys=True))


def command_sections(args):
    print(json.dumps(list_sections(args.path), indent=2, sort_keys=True))


def command_scan(args):
    print(json.dumps(find_strings(args.path, args.needle), indent=2, sort_keys=True))


def command_disasm(args):
    print("\n".join(disassemble_export(args.path, args.symbol, args.count)))


def build_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    exports_parser = subparsers.add_parser("exports")
    exports_parser.add_argument("path")
    exports_parser.set_defaults(func=command_exports)

    sections_parser = subparsers.add_parser("sections")
    sections_parser.add_argument("path")
    sections_parser.set_defaults(func=command_sections)

    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("path")
    scan_parser.add_argument("needle", nargs="+")
    scan_parser.set_defaults(func=command_scan)

    disasm_parser = subparsers.add_parser("disasm")
    disasm_parser.add_argument("path")
    disasm_parser.add_argument("symbol")
    disasm_parser.add_argument("--count", type=int, default=120)
    disasm_parser.set_defaults(func=command_disasm)
    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
