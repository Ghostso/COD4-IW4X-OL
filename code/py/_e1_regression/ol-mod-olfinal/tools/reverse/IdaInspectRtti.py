"""Resolve MSVC x86 RTTI strings to complete object locators and vtables."""

from __future__ import annotations

import pathlib

import ida_bytes
import ida_funcs
import ida_lines
import ida_pro
import ida_segment
import ida_ua
import idautils
import idc


def format_address(address: int) -> str:
    name = idc.get_name(address) or ""
    return f"0x{address:08X}" + (f" {name}" if name else "")


def is_code_address(address: int) -> bool:
    segment = ida_segment.getseg(address)
    return segment is not None and segment.type == ida_segment.SEG_CODE


def inspect_query(query: str, max_slots: int) -> list[str]:
    lines = ["=" * 80, f"QUERY {query}", "=" * 80]
    matches = [item for item in idautils.Strings() if query.casefold() in str(item).casefold()]
    if not matches:
        return lines + ["<no matches>"]

    for item in matches:
        type_descriptor = item.ea - 8
        lines.append(f"RTTI_STRING {format_address(item.ea)}: {str(item)}")
        lines.append(f"TYPE_DESCRIPTOR {format_address(type_descriptor)}")
        locator_addresses: set[int] = set()
        for reference in idautils.XrefsTo(type_descriptor):
            locator = reference.frm - 12
            if ida_bytes.get_dword(locator + 12) == type_descriptor:
                locator_addresses.add(locator)

        if not locator_addresses:
            lines.append("  <no complete object locator references>")
            continue

        for locator in sorted(locator_addresses):
            lines.append(f"COMPLETE_OBJECT_LOCATOR {format_address(locator)}")
            vtables: set[int] = set()
            for reference in idautils.XrefsTo(locator):
                if ida_bytes.get_dword(reference.frm) == locator:
                    vtables.add(reference.frm + 4)

            for vtable in sorted(vtables):
                lines.append(f"  VTABLE {format_address(vtable)}")
                for reference in idautils.XrefsTo(vtable):
                    owner = ida_funcs.get_func(reference.frm)
                    owner_address = owner.start_ea if owner is not None else reference.frm
                    lines.append(
                        f"    VTABLE_XREF {format_address(reference.frm)} "
                        f"owner={format_address(owner_address)} type={reference.type}"
                    )
                for index in range(max_slots):
                    slot = vtable + index * 4
                    target = ida_bytes.get_dword(slot)
                    if not is_code_address(target):
                        break
                    function = ida_funcs.get_func(target)
                    owner = function.start_ea if function is not None else target
                    disassembly = ida_lines.generate_disasm_line(target, 0) or ""
                    lines.append(
                        f"    [{index:02d}] {format_address(slot)} -> {format_address(owner)} "
                        f"{ida_lines.tag_remove(disassembly)}"
                    )
    return lines


def main() -> None:
    arguments = list(idc.ARGV[1:])
    if len(arguments) < 2:
        raise SystemExit("usage: IdaInspectRtti.py OUTPUT QUERY [QUERY ...]")
    output = pathlib.Path(arguments[0])
    output.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for query in arguments[1:]:
        lines.extend(inspect_query(query, 32))
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Exported RTTI for {len(arguments) - 1} queries to {output}")
    ida_pro.qexit(0)


if __name__ == "__main__":
    main()
