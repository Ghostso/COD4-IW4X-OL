"""Batch-export pseudocode and disassembly for selected IDA addresses.

Run through IDA, for example:
  idat.exe -A -S"tools/reverse/IdaInspectFunctions.py out.txt 0x1004284c FunctionName" input.i64
"""

from __future__ import annotations

import pathlib

import ida_funcs
import ida_hexrays
import ida_lines
import ida_pro
import ida_ua
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
        "=" * 80,
        f"FUNCTION {format_address(function.start_ea)} - 0x{function.end_ea:08X}",
        "",
        "PSEUDOCODE",
        "-" * 80,
    ]
    try:
        pseudocode = ida_hexrays.decompile(function.start_ea)
        lines.extend(str(pseudocode).splitlines())
    except Exception as error:
        lines.append(f"<decompile failed: {error!r}>")

    lines.extend(["", "DISASSEMBLY", "-" * 80])
    calls: set[int] = set()
    for instruction_address in idautils.FuncItems(function.start_ea):
        disassembly = ida_lines.generate_disasm_line(instruction_address, 0) or ""
        lines.append(f"0x{instruction_address:08X}: {ida_lines.tag_remove(disassembly)}")
        if ida_ua.print_insn_mnem(instruction_address).casefold() == "call":
            for reference in idautils.CodeRefsFrom(instruction_address, False):
                calls.add(reference)

    lines.extend(["", "DIRECT CALL TARGETS", "-" * 80])
    lines.extend(format_address(target) for target in sorted(calls))
    lines.extend(["", "XREFS TO FUNCTION", "-" * 80])
    for reference in idautils.XrefsTo(function.start_ea):
        owner = ida_funcs.get_func(reference.frm)
        owner_address = owner.start_ea if owner is not None else reference.frm
        lines.append(f"{format_address(reference.frm)} from {format_address(owner_address)} type={reference.type}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    arguments = list(idc.ARGV[1:])
    if len(arguments) < 2:
        raise SystemExit("usage: IdaInspectFunctions.py OUTPUT ADDRESS_OR_NAME [ADDRESS_OR_NAME ...]")
    output = pathlib.Path(arguments[0])
    addresses: list[int] = []
    for value in arguments[1:]:
        try:
            address = int(value, 0)
        except ValueError:
            address = idc.get_name_ea_simple(value)
            if address == idc.BADADDR:
                raise SystemExit(f"unknown IDA name: {value}")
        addresses.append(address)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(export_function(address) for address in addresses), encoding="utf-8")
    print(f"Exported {len(addresses)} functions to {output}")
    ida_pro.qexit(0)


if __name__ == "__main__":
    main()
