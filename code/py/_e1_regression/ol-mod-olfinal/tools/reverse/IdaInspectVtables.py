"""Batch-export vtable entries and their containing functions from IDA.

Run through IDA, for example:
  idat.exe -A -S"tools/reverse/IdaInspectVtables.py out.txt 0x101888b0:8" input.i64
"""

from __future__ import annotations

import pathlib

import ida_bytes
import ida_funcs
import ida_hexrays
import ida_kernwin
import ida_lines
import ida_pro
import idautils
import idc


def format_address(address: int) -> str:
    name = idc.get_name(address) or ""
    return f"0x{address:08X}" + (f" {name}" if name else "")


def export_function(address: int) -> str:
    function = ida_funcs.get_func(address)
    if function is None:
        return f"No function contains {format_address(address)}\n"

    lines = [
        f"FUNCTION {format_address(function.start_ea)} - 0x{function.end_ea:08X}",
        "PSEUDOCODE",
    ]
    try:
        lines.extend(str(ida_hexrays.decompile(function.start_ea)).splitlines())
    except Exception as error:
        lines.append(f"<decompile failed: {error!r}>")

    lines.append("DISASSEMBLY")
    for instruction_address in idautils.FuncItems(function.start_ea):
        disassembly = ida_lines.generate_disasm_line(instruction_address, 0) or ""
        lines.append(f"0x{instruction_address:08X}: {ida_lines.tag_remove(disassembly)}")
    return "\n".join(lines)


def export_vtable(address: int, count: int) -> str:
    lines = ["=" * 80, f"VTABLE {format_address(address)} ({count} entries)"]
    targets: list[int] = []
    for index in range(count):
        slot = address + index * 4
        target = ida_bytes.get_dword(slot)
        lines.append(f"[{index:02d}] {format_address(slot)} -> {format_address(target)}")
        if target not in targets:
            targets.append(target)
    for target in targets:
        lines.extend(["", export_function(target)])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    arguments = list(idc.ARGV[1:])
    if len(arguments) < 2:
        raise SystemExit("usage: IdaInspectVtables.py OUTPUT ADDRESS:COUNT [ADDRESS:COUNT ...]")
    output = pathlib.Path(arguments[0])
    tables = []
    for value in arguments[1:]:
        address, count = value.split(":", 1)
        tables.append((int(address, 0), int(count, 0)))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(export_vtable(*table) for table in tables), encoding="utf-8")
    print(f"Exported {len(tables)} vtables to {output}")
    ida_pro.qexit(0)


if __name__ == "__main__":
    main()
