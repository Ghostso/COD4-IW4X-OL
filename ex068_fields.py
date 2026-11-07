#!/usr/bin/env python3
"""Recover read/write sites for EX-068 shared-memory fields.

This is intentionally heuristic: it reports candidate writes and nearby
constants, and labels them STATIC_REACHABLE unless a direct instruction
operand makes the field update unambiguous.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex066_common import PEImage


ROOT = Path(__file__).resolve().parent
MODULES = {
    "codo": ROOT / "COD OL" / "codoMP_client_shipRetail.exe",
    "base": ROOT / "COD OL" / "codoMP_client_shipRetailBase.dll",
    "proxy": ROOT / "COD OL" / "TenProxy.dll",
    "clientbase": ROOT / "COD OL" / "TCLS" / "ClientBase.dll",
    "core": ROOT / "WeGame" / "tcls" / "tcls_core.exe",
    "iips_restore": ROOT / "COD OL" / "IIPS" / "IIPSLaunchRestore.dll",
    "iips": ROOT / "COD OL" / "IIPS" / "iips.dll",
}

FIELDS = {
    "GameSignature": [0x04],
    "JumpSignature": [0x1A, 0x1B],
    "GameID": [0x30, 0x34],
    "GamePID": [0x18, 0x1C],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("module", choices=MODULES)
    parser.add_argument("--tag", action="append")
    args = parser.parse_args()

    wanted = set(args.tag or FIELDS)
    image = PEImage(MODULES[args.module])
    rows: list[dict[str, object]] = []
    for field, values in FIELDS.items():
        if field not in wanted:
            continue
        for value in values:
            for insn in image.iter_code():
                site = insn.address - image.base
                for op_index, operand in enumerate(insn.operands):
                    if (
                        operand.type == X86_OP_MEM
                        and operand.mem.disp == value
                        and op_index == 0
                        and insn.mnemonic
                        not in ("cmp", "test", "push", "call", "jmp")
                    ):
                        rows.append(
                            {
                                "field": field,
                                "offset": f"+0x{value:X}",
                                "site": f"0x{site:X}",
                                "function": f"0x{image.find_function_start(site):X}",
                                "instruction": f"{insn.mnemonic} {insn.op_str}",
                                "evidence": "STATIC_REACHABLE",
                            }
                        )
                    if operand.type == X86_OP_IMM and operand.imm == value:
                        rows.append(
                            {
                                "field": field,
                                "offset": f"0x{value:X}",
                                "site": f"0x{site:X}",
                                "function": f"0x{image.find_function_start(site):X}",
                                "instruction": f"{insn.mnemonic} {insn.op_str}",
                                "evidence": "STATIC_REACHABLE",
                            }
                        )
    output = ROOT / f"ex068_{args.module}_field_sites.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "field",
                "offset",
                "site",
                "function",
                "instruction",
                "evidence",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {output} rows={len(rows)}")


if __name__ == "__main__":
    main()
