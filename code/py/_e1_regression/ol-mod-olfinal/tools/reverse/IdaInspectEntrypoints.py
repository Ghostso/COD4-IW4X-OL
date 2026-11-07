"""Export entrypoint and exported-function pseudocode from the active IDA database."""

from __future__ import annotations

import pathlib

import ida_entry
import ida_funcs
import ida_hexrays
import ida_ida
import ida_lines
import ida_pro
import idc


def describe(address: int, label: str) -> list[str]:
    function = ida_funcs.get_func(address)
    start = function.start_ea if function is not None else address
    name = idc.get_func_name(start) or idc.get_name(address) or "<unnamed>"
    lines = ["=" * 80, f"{label}: 0x{address:08X} function=0x{start:08X} {name}", "=" * 80]
    try:
        lines.append(str(ida_hexrays.decompile(start)))
    except Exception as error:
        lines.append(f"<decompilation failed: {error}>")
        if function is not None:
            cursor = function.start_ea
            while cursor < function.end_ea:
                text = ida_lines.generate_disasm_line(cursor, 0)
                if text:
                    lines.append(f"0x{cursor:08X} {ida_lines.tag_remove(text)}")
                cursor = idc.next_head(cursor, function.end_ea)
    return lines


def main() -> None:
    arguments = list(idc.ARGV[1:])
    if not arguments:
        raise SystemExit("usage: IdaInspectEntrypoints.py OUTPUT [ADDRESS ...]")
    output = pathlib.Path(arguments[0])
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = describe(ida_ida.inf_get_start_ea(), "PE ENTRYPOINT")
    for index in range(ida_entry.get_entry_qty()):
        ordinal = ida_entry.get_entry_ordinal(index)
        address = ida_entry.get_entry(ordinal)
        name = ida_entry.get_entry_name(ordinal) or f"ordinal_{ordinal}"
        lines.extend(describe(address, f"EXPORT {name} ordinal={ordinal}"))
    for raw_address in arguments[1:]:
        address = int(raw_address, 0)
        lines.extend(describe(address, f"REQUESTED {raw_address}"))
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Exported entrypoint pseudocode to {output}")
    ida_pro.qexit(0)


if __name__ == "__main__":
    main()
