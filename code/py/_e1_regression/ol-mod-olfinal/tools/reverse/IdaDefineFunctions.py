"""Define missed IDA functions at explicit addresses, then export them."""

from __future__ import annotations

import pathlib

import ida_auto
import ida_funcs
import ida_hexrays
import ida_lines
import ida_pro
import ida_ua
import idautils
import idc


def export_function(address: int) -> str:
    function = ida_funcs.get_func(address)
    if function is None:
        return f"Could not define function at 0x{address:08X}\n"

    lines = [
        "=" * 80,
        f"FUNCTION 0x{function.start_ea:08X} {idc.get_name(function.start_ea) or ''} "
        f"- 0x{function.end_ea:08X}",
        "",
        "PSEUDOCODE",
        "-" * 80,
    ]
    try:
        lines.extend(str(ida_hexrays.decompile(function.start_ea)).splitlines())
    except Exception as error:
        lines.append(f"<decompile failed: {error!r}>")

    lines.extend(["", "DISASSEMBLY", "-" * 80])
    for instruction in idautils.FuncItems(function.start_ea):
        text = ida_lines.generate_disasm_line(instruction, 0) or ""
        lines.append(f"0x{instruction:08X}: {ida_lines.tag_remove(text)}")
    return "\n".join(lines)


def main() -> None:
    arguments = list(idc.ARGV[1:])
    if len(arguments) < 2:
        raise SystemExit("usage: IdaDefineFunctions.py OUTPUT ADDRESS [ADDRESS ...]")

    output = pathlib.Path(arguments[0])
    addresses = [int(value, 0) for value in arguments[1:]]
    for address in addresses:
        if ida_funcs.get_func(address) is None:
            ida_ua.create_insn(address)
            ida_funcs.add_func(address)
    ida_auto.auto_wait()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n".join(export_function(address) for address in addresses), encoding="utf-8")
    print(f"Defined and exported {len(addresses)} functions to {output}")
    ida_pro.qexit(0)


if __name__ == "__main__":
    main()
