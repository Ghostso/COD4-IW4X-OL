#!/usr/bin/env python3
"""Small offline PE/disassembly probe used for EX-066 evidence recovery."""

from __future__ import annotations

import argparse
import re
from collections import deque

import capstone as cs
from capstone.x86 import (
    X86_OP_IMM,
    X86_OP_MEM,
    X86_OP_REG,
)

from ex065_tcls_img import Img


MODULES = {
    "tcls_core": r"WeGame\tcls\tcls_core.exe",
    "tenproxy": r"COD OL\TenProxy.dll",
    "tcls": r"COD OL\TCLS\Tenio\TCLS.dll",
    "clientbase": r"COD OL\TCLS\ClientBase.dll",
    "tpsvcbase": r"COD OL\TCLS\tpsvcBase.dll",
    "base": r"COD OL\codoMP_client_shipRetailBase.dll",
    "iipsrestore": r"COD OL\IIPS\IIPSLaunchRestore.dll",
    "client": r"COD OL\TCLS\Client.exe",
    "codo": r"COD OL\codoMP_client_shipRetail.exe",
}


def make_md() -> cs.Cs:
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    return md


def wide_string(img: Img, rva: int, limit: int = 120) -> str | None:
    raw = img.rva2raw(rva)
    if raw is None:
        return None
    data = img.data[raw:raw + limit * 2]
    out: list[str] = []
    for i in range(0, len(data) - 1, 2):
        code = data[i] | (data[i + 1] << 8)
        if code == 0:
            break
        if not (32 <= code < 127):
            return None
        out.append(chr(code))
    return "".join(out) if len(out) >= 3 else None


def ascii_string(img: Img, rva: int, limit: int = 120) -> str | None:
    raw = img.rva2raw(rva)
    if raw is None:
        return None
    data = img.data[raw:raw + limit].split(b"\x00", 1)[0]
    if len(data) >= 3 and all(32 <= b < 127 for b in data):
        return data.decode("ascii")
    return None


def annotation(img: Img, md: cs.Cs, insn: cs.CsInsn) -> str:
    notes: list[str] = []
    if insn.mnemonic == "call" and insn.operands:
        op = insn.operands[0]
        if op.type == X86_OP_IMM:
            notes.append(f"-> sub_{op.imm - img.base:X}")
        elif op.type == X86_OP_MEM:
            target = None
            if op.mem.base == 0:
                target = op.mem.disp - img.base
            elif op.mem.base in (
                cs.x86.X86_REG_ECX,
                cs.x86.X86_REG_EDX,
                cs.x86.X86_REG_EAX,
                cs.x86.X86_REG_EBX,
                cs.x86.X86_REG_ESI,
                cs.x86.X86_REG_EDI,
            ):
                target = None
            if target in img.imports:
                dll, name = img.imports[target]
                notes.append(f"{dll}!{name}")
            elif op.mem.base:
                reg = md.reg_name(op.mem.base)
                notes.append(f"IND [{reg}+0x{op.mem.disp:X}]")
            else:
                notes.append(f"IND [0x{op.mem.disp:X}]")
        elif op.type == X86_OP_REG:
            notes.append(f"IND {md.reg_name(op.reg)}")

    for op in insn.operands:
        if op.type != X86_OP_IMM:
            continue
        target = op.imm - img.base
        if not (0 <= target < img.size):
            continue
        w = wide_string(img, target)
        a = ascii_string(img, target)
        if w:
            notes.append(f'L"{w}"')
        elif a and len(a) >= 4:
            notes.append(f'"{a}"')
    return "  ; " + " ".join(notes) if notes else ""


def disasm(
    img: Img,
    md: cs.Cs,
    start: int,
    count: int,
    stop_at_ret: bool = False,
) -> list[tuple[int, cs.CsInsn]]:
    rva = start
    out: list[tuple[int, cs.CsInsn]] = []
    for _ in range(count):
        insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
        if insn is None:
            break
        out.append((rva, insn))
        rva += insn.size
        if stop_at_ret and (insn.mnemonic.startswith("ret") or
                            insn.mnemonic in ("int3", "hlt", "ud2")):
            break
    return out


def dump(img: Img, md: cs.Cs, start: int, count: int,
         stop_at_ret: bool = False) -> None:
    for rva, insn in disasm(img, md, start, count, stop_at_ret):
        print(
            f"{rva:08X}  {insn.bytes.hex():<24} "
            f"{insn.mnemonic:<8} {insn.op_str}{annotation(img, md, insn)}"
        )


def find_callers(img: Img, md: cs.Cs, targets: set[int],
                 direct_only: bool = True) -> list[tuple[int, int]]:
    lo, hi = img.codesec()
    hits: list[tuple[int, int]] = []
    rva = lo
    while rva < hi:
        insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
        if insn is None:
            rva += 1
            continue
        if insn.mnemonic in ("call", "jmp") and insn.operands:
            op = insn.operands[0]
            if op.type == X86_OP_IMM and op.imm - img.base in targets:
                hits.append((rva, op.imm - img.base))
            elif not direct_only and op.type == X86_OP_MEM and op.mem.base == 0:
                target = op.mem.disp - img.base
                if target in targets:
                    hits.append((rva, target))
        rva += insn.size
    return hits


def find_refs(img: Img, target_rva: int) -> list[int]:
    needle = (img.base + target_rva).to_bytes(4, "little")
    out: list[int] = []
    pos = 0
    while True:
        raw = img.data.find(needle, pos)
        if raw < 0:
            break
        rva, _sec = img.raw2rva(raw)
        if rva is not None:
            out.append(rva)
        pos = raw + 1
    return out


def find_import_callers(img: Img, md: cs.Cs, names: set[str]) -> list[tuple[int, str, int]]:
    iat_to_name = {
        rva: name for rva, (_dll, name) in img.imports.items()
        if name in names
    }
    lo, hi = img.codesec()
    hits: list[tuple[int, str, int]] = []
    rva = lo
    while rva < hi:
        insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
        if insn is None:
            rva += 1
            continue
        if insn.mnemonic == "call" and insn.operands:
            op = insn.operands[0]
            if op.type == X86_OP_MEM and op.mem.base == 0:
                target = op.mem.disp - img.base
                if target in iat_to_name:
                    hits.append((rva, iat_to_name[target], target))
        rva += insn.size
    return hits


def function_entry(img: Img, anchor: int, max_back: int = 0x500) -> int | None:
    lo, _hi = img.codesec()
    start = max(lo, anchor - max_back)
    pattern = re.compile(b"\x55\x8b\xec")
    best = None
    for pos in range(start - img.base, anchor - img.base):
        if pattern.match(img.by_rva, pos):
            best = pos
    if best is not None:
        return best
    for pos in range(anchor - img.base, start - img.base, -1):
        if img.by_rva[pos] in (0xC3, 0xCC, 0xC2):
            return pos + 1
    return None


def load(name: str) -> tuple[Img, cs.Cs]:
    img = Img(MODULES[name])
    return img, make_md()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("module", choices=MODULES)
    ap.add_argument("--disasm", help="START[,COUNT], e.g. 0x89EEE,180")
    ap.add_argument("--callers", help="comma-separated target RVAs")
    ap.add_argument("--import-calls", help="comma-separated API names")
    ap.add_argument("--refs", help="comma-separated target RVAs")
    ap.add_argument("--stop-ret", action="store_true")
    args = ap.parse_args()

    img, md = load(args.module)
    print(f"{args.module}: base=0x{img.base:X} size=0x{img.size:X}")
    if args.disasm:
        fields = args.disasm.split(",")
        start = int(fields[0], 0)
        count = int(fields[1], 0) if len(fields) > 1 else 100
        dump(img, md, start, count, args.stop_ret)
    if args.callers:
        targets = {int(x, 0) for x in args.callers.split(",")}
        for site, target in find_callers(img, md, targets):
            print(f"CALL {site:08X} -> {target:08X}")
    if args.import_calls:
        names = set(args.import_calls.split(","))
        for site, name, iat in find_import_callers(img, md, names):
            print(f"IMPORT {site:08X} {name} IAT={iat:08X}")
    if args.refs:
        for target in (int(x, 0) for x in args.refs.split(",")):
            print(f"REFS {target:08X}: " +
                  ", ".join(f"{x:08X}" for x in find_refs(img, target)))


if __name__ == "__main__":
    main()
