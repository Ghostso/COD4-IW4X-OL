"""Export IDA data/code references and the pseudocode of owning functions."""

from __future__ import annotations

import pathlib

import ida_funcs
import ida_hexrays
import ida_pro
import idautils
import idc


def format_address(address: int) -> str:
    name = idc.get_name(address) or ""
    return f"0x{address:08X}" + (f" {name}" if name else "")


def main() -> None:
    arguments = list(idc.ARGV[1:])
    if len(arguments) < 2:
        raise SystemExit("usage: IdaInspectXrefs.py OUTPUT ADDRESS [ADDRESS ...]")

    output = pathlib.Path(arguments[0])
    addresses = [int(value, 0) for value in arguments[1:]]
    owners: set[int] = set()
    lines: list[str] = []

    for address in addresses:
        lines.extend(["=" * 80, f"XREFS TO {format_address(address)}", "=" * 80])
        references = list(idautils.XrefsTo(address))
        if not references:
            lines.append("<no references>")
        for reference in references:
            function = ida_funcs.get_func(reference.frm)
            owner = function.start_ea if function is not None else reference.frm
            if function is not None:
                owners.add(owner)
            lines.append(
                f"{format_address(reference.frm)} from {format_address(owner)} type={reference.type}"
            )

    for owner in sorted(owners):
        lines.extend(["", "=" * 80, f"PSEUDOCODE {format_address(owner)}", "=" * 80])
        try:
            lines.extend(str(ida_hexrays.decompile(owner)).splitlines())
        except Exception as error:
            lines.append(f"<decompile failed: {error!r}>")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Exported {len(owners)} owning functions to {output}")
    ida_pro.qexit(0)


if __name__ == "__main__":
    main()
