"""Export instructions and owning pseudocode that access a structure offset."""

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


def main() -> None:
    arguments = list(idc.ARGV[1:])
    if len(arguments) != 2:
        raise SystemExit("usage: IdaFindMemberAccesses.py OUTPUT OFFSET")

    output = pathlib.Path(arguments[0])
    offset = int(arguments[1], 0)
    owners: set[int] = set()
    lines = [f"MEMBER OFFSET 0x{offset:X}", "=" * 80]

    for function_address in idautils.Functions():
        for address in idautils.FuncItems(function_address):
            instruction = ida_ua.insn_t()
            if ida_ua.decode_insn(instruction, address) <= 0:
                continue
            matching_operands = [
                index
                for index, operand in enumerate(instruction.ops)
                if operand.type == ida_ua.o_displ and operand.addr == offset
            ]
            if not matching_operands:
                continue
            function = ida_funcs.get_func(address)
            owner = function.start_ea if function is not None else address
            owners.add(owner)
            disassembly = ida_lines.tag_remove(ida_lines.generate_disasm_line(address, 0) or "")
            lines.append(
                f"{format_address(address)} owner={format_address(owner)} "
                f"operands={','.join(map(str, matching_operands))}: {disassembly}"
            )

    for owner in sorted(owners):
        lines.extend(["", "=" * 80, f"PSEUDOCODE {format_address(owner)}", "=" * 80])
        try:
            lines.extend(str(ida_hexrays.decompile(owner)).splitlines())
        except Exception as error:
            lines.append(f"<decompile failed: {error!r}>")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Exported {len(owners)} functions accessing offset 0x{offset:X} to {output}")
    ida_pro.qexit(0)


if __name__ == "__main__":
    main()
