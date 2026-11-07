"""Find CODOL functions which may back an in-process authoritative server.

Run through IDA, for example:
  idat.exe -A -S"tools/reverse/IdaFindServerBindings.py diagnostics/ida/server-bindings.txt" game.i64
"""

from __future__ import annotations

import pathlib
import re

import ida_funcs
import ida_pro
import idautils
import idc


PATTERNS = (
    r"com_.*frame",
    r"cl_.*frame",
    r"sys_.*millisecond",
    r"db_.*xasset",
    r"cm_.*trace",
    r"cm_.*clip",
    r"pmove",
    r"pm_.*move",
    r"bg_.*move",
    r"scr_.*script",
    r"scr_.*thread",
    r"scriptfile",
    r"playerstate",
    r"usercmd",
    r"netfield",
)
MATCHER = re.compile("|".join(f"(?:{pattern})" for pattern in PATTERNS), re.IGNORECASE)


def function_label(address: int) -> str:
    function = ida_funcs.get_func(address)
    if function is None:
        return f"0x{address:08X} <no function>"
    name = idc.get_func_name(function.start_ea) or "sub_unknown"
    return f"0x{function.start_ea:08X} {name}"


def main() -> None:
    arguments = list(idc.ARGV[1:])
    if len(arguments) != 1:
        raise SystemExit("usage: IdaFindServerBindings.py OUTPUT")

    output = pathlib.Path(arguments[0])
    output.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    lines.append("MATCHING IDA NAMES")
    lines.append("=" * 80)
    for address, name in idautils.Names():
        if MATCHER.search(name):
            lines.append(f"0x{address:08X} {name} owner={function_label(address)}")

    lines.append("")
    lines.append("MATCHING STRINGS AND FUNCTION XREFS")
    lines.append("=" * 80)
    for string in idautils.Strings():
        value = str(string)
        if not MATCHER.search(value):
            continue
        lines.append(f"0x{string.ea:08X} {value!r}")
        owners = {
            function_label(reference.frm)
            for reference in idautils.XrefsTo(string.ea)
        }
        for owner in sorted(owners):
            lines.append(f"  xref {owner}")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Exported CODOL server-binding candidates to {output}")
    ida_pro.qexit(0)


if __name__ == "__main__":
    main()
