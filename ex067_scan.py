#!/usr/bin/env python3
"""Batch static scans for the EX-067 GameID and mapped-memory dataflow."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from capstone.x86 import (
    X86_OP_IMM,
    X86_OP_MEM,
    X86_OP_REG,
)

from ex066_common import PEImage


ROOT = Path(__file__).resolve().parent
MODULES = {
    "core": ROOT / "WeGame" / "tcls" / "tcls_core.exe",
    "proxy": ROOT / "COD OL" / "TenProxy.dll",
    "tcls": ROOT / "COD OL" / "TCLS" / "Tenio" / "TCLS.dll",
    "clientbase": ROOT / "COD OL" / "TCLS" / "ClientBase.dll",
    "tpsvcbase": ROOT / "COD OL" / "TCLS" / "tpsvcBase.dll",
    "base": ROOT / "COD OL" / "codoMP_client_shipRetailBase.dll",
    "iips": ROOT / "COD OL" / "IIPS" / "IIPSLaunchRestore.dll",
    "client": ROOT / "COD OL" / "TCLS" / "Client.exe",
    "codo": ROOT / "COD OL" / "codoMP_client_shipRetail.exe",
}


def memory_expr(image: PEImage, mem) -> str:
    parts: list[str] = []
    if mem.segment:
        parts.append(image.md.reg_name(mem.segment))
    if mem.base:
        parts.append(image.md.reg_name(mem.base))
    if mem.index:
        scale = f"*{mem.scale}" if mem.scale != 1 else ""
        parts.append(image.md.reg_name(mem.index) + scale)
    if mem.disp or not parts:
        sign = "+" if parts and mem.disp >= 0 else ""
        parts.append(f"{sign}0x{abs(mem.disp):X}" if mem.disp else "0")
    return "[" + " ".join(parts) + "]"


def signed(value: int, bits: int = 32) -> int:
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def scan_displacements(image: PEImage, displacements: set[int]) -> None:
    by_disp: dict[int, list[tuple[int, str, str, str]]] = defaultdict(list)
    immediates: dict[int, list[tuple[int, str, str]]] = defaultdict(list)
    for insn in image.iter_code():
        rva = insn.address - image.base
        for op in insn.operands:
            if op.type == X86_OP_MEM and op.mem.disp in displacements:
                by_disp[op.mem.disp].append(
                    (rva, insn.mnemonic, insn.op_str, memory_expr(image, op.mem))
                )
            if op.type == X86_OP_IMM and op.imm in displacements:
                immediates[op.imm].append((rva, insn.mnemonic, insn.op_str))
    for value in sorted(displacements):
        print(f"DISP 0x{value:X}")
        for rva, mnemonic, op_str, mem in by_disp.get(value, []):
            print(f"  {rva:06X}  {mnemonic:<8} {op_str:<40} {mem}")
        for rva, mnemonic, op_str in immediates.get(value, []):
            print(f"  {rva:06X}  {mnemonic:<8} {op_str:<40} IMM")


def scan_memory_writes(image: PEImage, base_regs: set[int]) -> None:
    tracked = {
        memory_expr(image, op.mem)
        for insn in image.iter_code()
        for op in insn.operands
        if op.type == X86_OP_MEM and op.mem.base in base_regs
    }
    writes: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    reads: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for insn in image.iter_code():
        rva = insn.address - image.base
        if insn.id in (0,):
            continue
        # Capstone's x86 operand access data is used when available.
        access = getattr(insn, "regs_access", lambda: ((), ()))()
        # Destination memory operand is the first operand for common writes.
        if insn.operands and insn.operands[0].type == X86_OP_MEM:
            expr = memory_expr(image, insn.operands[0].mem)
            if expr in tracked:
                writes[expr].append((rva, insn.mnemonic, insn.op_str))
        for op in insn.operands:
            if op.type == X86_OP_MEM:
                expr = memory_expr(image, op.mem)
                if expr in tracked:
                    reads[expr].append((rva, insn.mnemonic, insn.op_str))
    for expr in sorted(tracked):
        if writes.get(expr):
            print(f"MEM {expr}")
            for rva, mnemonic, op_str in writes[expr]:
                print(f"  W {rva:06X}  {mnemonic:<8} {op_str}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("module", choices=MODULES)
    parser.add_argument("--disp", nargs="*", default=[])
    parser.add_argument("--write-base", nargs="*", default=[])
    args = parser.parse_args()

    image = PEImage(MODULES[args.module])
    print(f"{args.module}: base=0x{image.base:X} size=0x{image.size:X}")
    if args.disp:
        scan_displacements(image, {int(value, 0) for value in args.disp})
    if args.write_base:
        base_regs = set()
        for name in args.write_base:
            reg_id = getattr(image.md, "reg_name", None)
            for reg in range(1, 256):
                try:
                    if image.md.reg_name(reg) == name:
                        base_regs.add(reg)
                        break
                except Exception:
                    pass
        scan_memory_writes(image, base_regs)


if __name__ == "__main__":
    main()
