"""Batch-export IDA string matches, xrefs, and owning pseudocode."""

from __future__ import annotations

import pathlib

import ida_funcs
import ida_hexrays
import ida_lines
import ida_pro
import idautils
import idc


def clean(value: str) -> str:
    return ida_lines.tag_remove(value).replace("\r", "\\r").replace("\n", "\\n")


def main() -> None:
    arguments = list(idc.ARGV[1:])
    if len(arguments) < 2:
        raise SystemExit("usage: IdaFindStringXrefs.py OUTPUT QUERY [QUERY ...]")
    output = pathlib.Path(arguments[0])
    queries = [value.casefold() for value in arguments[1:]]
    strings = list(idautils.Strings())
    owner_functions: set[int] = set()
    lines: list[str] = []

    for query in queries:
        lines.extend(["=" * 80, f"QUERY {query}", "=" * 80])
        matches = [item for item in strings if query in str(item).casefold()]
        if not matches:
            lines.append("<no matches>")
            continue
        for item in matches:
            lines.append(f"STRING 0x{item.ea:08X}: {clean(str(item))}")
            for reference in idautils.XrefsTo(item.ea):
                function = ida_funcs.get_func(reference.frm)
                owner = function.start_ea if function is not None else reference.frm
                owner_functions.add(owner)
                lines.append(
                    f"  XREF 0x{reference.frm:08X} owner=0x{owner:08X} "
                    f"name={idc.get_name(owner) or ''} type={reference.type}"
                )

    for address in sorted(owner_functions):
        lines.extend(["", "=" * 80, f"PSEUDOCODE 0x{address:08X} {idc.get_name(address) or ''}", "=" * 80])
        try:
            lines.extend(str(ida_hexrays.decompile(address)).splitlines())
        except Exception as error:
            lines.append(f"<decompile failed: {error!r}>")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Exported {len(owner_functions)} owning functions to {output}")
    ida_pro.qexit(0)


if __name__ == "__main__":
    main()
