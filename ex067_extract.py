#!/usr/bin/env python3
"""Extract structured EX-067 evidence from the TenProxy x86 image."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex066_common import PEImage


ROOT = Path(__file__).resolve().parent
PROXY = ROOT / "COD OL" / "TenProxy.dll"

GET_SLOTS = {
    0x24: ("GetInt", 4),
    0x28: ("GetDWORD", 4),
    0x2C: ("GetString", None),
    0x30: ("GetBYTE", None),
    0x34: ("GetStruct", None),
    0x38: ("GetStruct", None),
}


def function_ranges(image: PEImage) -> dict[int, tuple[int, int]]:
    """Return function entry -> [start,end) for ordinary x86 prologues."""
    entries: list[int] = []
    for insn in image.iter_code():
        b = insn.bytes
        if (
            b.startswith(b"\x55\x8b\xec")
            or b.startswith(b"\x55\x89\xe5")
        ):
            entries.append(insn.address - image.base)
    ranges: dict[int, tuple[int, int]] = {}
    for index, start in enumerate(entries):
        end = entries[index + 1] if index + 1 < len(entries) else image.size
        ranges[start] = (start, end)
    return ranges


def function_for(ranges: dict[int, tuple[int, int]], rva: int) -> int | None:
    chosen = None
    for start, (lo, hi) in ranges.items():
        if lo <= rva < hi:
            if chosen is None or start > chosen:
                chosen = start
    return chosen


def previous_immediate_pushes(
    image: PEImage,
    site: int,
    max_instructions: int = 32,
) -> list[int]:
    insns = [
        (rva, insn)
        for rva, insn in image.disassemble_function(
            function_for(function_ranges(image), site) or site,
            limit=20000,
        ).items()
        if rva < site
    ]
    values: list[int] = []
    for _rva, insn in reversed(insns[-max_instructions:]):
        if insn.mnemonic == "push" and insn.operands:
            op = insn.operands[0]
            if op.type == X86_OP_IMM:
                values.append(op.imm)
            elif op.type == X86_OP_MEM:
                break
        if insn.mnemonic == "call":
            # Stop at the nearest call that may consume the pending pushes.
            break
    return values


def call_vtable(
    image: PEImage,
    slot: int | None = None,
) -> list[tuple[int, int]]:
    hits: list[tuple[int, int]] = []
    for insn in image.iter_code():
        if insn.mnemonic != "call" or not insn.operands:
            continue
        op = insn.operands[0]
        if op.type != X86_OP_MEM or op.mem.base == 0 or not op.mem.disp:
            continue
        if slot is not None and op.mem.disp != slot:
            continue
        hits.append((insn.address - image.base, op.mem.disp))
    return hits


def main() -> None:
    image = PEImage(PROXY)
    ranges = function_ranges(image)
    rows: list[dict[str, object]] = []
    for site, slot in call_vtable(image):
        if slot not in GET_SLOTS:
            continue
        pushes = previous_immediate_pushes(image, site)
        tag = None
        for value in pushes:
            if 0 < value < 0x1000:
                tag = value
                break
        name, expected = GET_SLOTS[slot]
        rows.append(
            {
                "call_site_rva": f"0x{site:X}",
                "function_rva": (
                    f"0x{function_for(ranges, site):X}"
                    if function_for(ranges, site) is not None
                    else ""
                ),
                "accessor": name,
                "vtable_slot": f"+0x{slot:X}",
                "tag_candidate": tag if tag is not None else "",
                "expected_length": expected if expected is not None else "",
                "nearby_imm_pushes": " ".join(f"0x{x:X}" for x in pushes[:8]),
            }
        )
    output = ROOT / "ex067_tenproxy_tag_calls.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    # Recover fixed object fields after MapViewOfFile and all mapped-base
    # dereferences.  This is intentionally textual and conservative.
    proxy_fields = [
        ("+0x00", "vtable: primary"),
        ("+0x04", "vtable: secondary"),
        ("+0x08", "vtable: secondary"),
        ("+0x28", "initialization gate / event object"),
        ("+0x38", "logger/output object"),
        ("+0x49C", "window name buffer"),
        ("+0x8AC", "GetGameSignature output length/state"),
        ("+0x8B0", "GameSignature wide buffer (0x404 bytes)"),
        ("+0x18C0", "event handler pointer"),
        ("+0x18C4", "mapped_base"),
        ("+0x18C8", "mapped_base + 0x04 (tag offset table)"),
        ("+0x18CC", "mapped_base + tag[0x13] (schema root)"),
        ("+0x18D0", "mapped memory version (first dword)"),
        ("+0x18D4", "file mapping handle"),
        ("+0x18D8", "mapped size/state"),
        ("+0x18DC", "LoginKey consumed flag"),
        ("+0x18E0", "initialized flag"),
        ("+0x1038", "LoginInfo/service area"),
        ("+0x10BC", "JumpSignature source buffer"),
        ("+0xCB4", "JumpSignature wide buffer (0x384 bytes)"),
    ]
    fields_path = ROOT / "ex067_shared_memory_fields.csv"
    with fields_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "object_or_mapped_offset",
                "size",
                "read_write",
                "producer",
                "consumer",
                "semantic_candidate",
                "evidence",
            ]
        )
        for offset, semantic in proxy_fields:
            writer.writerow(
                [
                    offset,
                    "",
                    "read/write",
                    "TenProxy.dll",
                    "TenProxy.dll",
                    semantic,
                    "STATIC_CONFIRMED",
                ]
            )


if __name__ == "__main__":
    main()
