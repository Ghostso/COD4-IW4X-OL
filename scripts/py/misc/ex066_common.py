"""Shared static-analysis helpers for the EX-066 protocol closure.

The target family mixes x86 executables/DLLs and one x64 helper.  This module
keeps all image handling and instruction decoding in one place so the EX-066
scripts can report RVAs consistently.
"""

from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Iterator, Optional

import capstone as cs
import pefile
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG


COND_JUMPS = {
    "ja", "jae", "jb", "jbe", "jc", "je", "jg", "jge", "jl", "jle",
    "jna", "jnae", "jnb", "jnbe", "jnc", "jne", "jng", "jnge", "jnl",
    "jnle", "jno", "jnp", "jns", "jnz", "jo", "jp", "jpe", "jpo", "js",
    "jz",
}


@dataclass(frozen=True)
class Section:
    name: str
    rva: int
    vsize: int
    raw: int
    raw_size: int
    characteristics: int

    @property
    def executable(self) -> bool:
        return bool(self.characteristics & 0x20000000)


class PEImage:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.pe = pefile.PE(str(self.path), fast_load=True)
        self.pe.parse_data_directories()
        self.data = self.path.read_bytes()
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.size = self.pe.OPTIONAL_HEADER.SizeOfImage
        self.entry = self.pe.OPTIONAL_HEADER.AddressOfEntryPoint
        self.machine = self.pe.FILE_HEADER.Machine
        self.is64 = self.machine == 0x8664
        self.by_rva = bytearray(self.size)
        self.sections: list[Section] = []
        for sec in self.pe.sections:
            name = sec.Name.decode(errors="replace").rstrip("\x00")
            item = Section(
                name,
                sec.VirtualAddress,
                sec.Misc_VirtualSize,
                sec.PointerToRawData,
                sec.SizeOfRawData,
                sec.Characteristics,
            )
            self.sections.append(item)
            n = min(item.vsize, item.raw_size)
            self.by_rva[item.rva:item.rva + n] = (
                self.data[item.raw:item.raw + n]
            )
        self.imports: dict[int, tuple[str, str]] = {}
        if hasattr(self.pe, "DIRECTORY_ENTRY_IMPORT"):
            for desc in self.pe.DIRECTORY_ENTRY_IMPORT:
                dll = desc.dll.decode(errors="replace")
                for imp in desc.imports:
                    name = (
                        imp.name.decode(errors="replace")
                        if imp.name
                        else "ord%d" % imp.ordinal
                    )
                    self.imports[imp.address - self.base] = (dll, name)
        self.exports: dict[int, str] = {}
        if hasattr(self.pe, "DIRECTORY_ENTRY_EXPORT"):
            for exp in self.pe.DIRECTORY_ENTRY_EXPORT.symbols:
                if exp.name:
                    self.exports[exp.address] = exp.name.decode(errors="replace")
        self.md = cs.Cs(
            cs.CS_ARCH_X86,
            cs.CS_MODE_64 if self.is64 else cs.CS_MODE_32,
        )
        self.md.detail = True

    def read(self, rva: int, size: int) -> bytes:
        if rva < 0 or size < 0:
            return b""
        return bytes(self.by_rva[rva:rva + size])

    def va(self, rva: int) -> int:
        return self.base + rva

    def rva(self, va: int) -> Optional[int]:
        result = va - self.base
        return result if 0 <= result < self.size else None

    def section_for_rva(self, rva: int) -> Optional[Section]:
        for sec in self.sections:
            if sec.rva <= rva < sec.rva + max(sec.vsize, sec.raw_size):
                return sec
        return None

    def is_executable(self, rva: int) -> bool:
        sec = self.section_for_rva(rva)
        return bool(sec and sec.executable)

    def code_sections(self) -> list[tuple[int, int]]:
        return [
            (sec.rva, sec.rva + sec.vsize)
            for sec in self.sections
            if sec.executable
        ]

    def rva_to_raw(self, rva: int) -> Optional[int]:
        sec = self.section_for_rva(rva)
        if not sec or rva - sec.rva >= sec.raw_size:
            return None
        return sec.raw + (rva - sec.rva)

    def raw_to_rva(self, offset: int) -> Optional[tuple[int, str]]:
        for sec in self.sections:
            if sec.raw <= offset < sec.raw + sec.raw_size:
                return sec.rva + (offset - sec.raw), sec.name
        return None

    def ascii_at(self, rva: int, limit: int = 512) -> Optional[str]:
        raw = self.rva_to_raw(rva)
        if raw is None:
            return None
        end = self.data.find(b"\x00", raw, min(len(self.data), raw + limit))
        if end < 0:
            return None
        return self.data[raw:end].decode(errors="replace")

    def utf16_at(self, rva: int, limit: int = 1024) -> Optional[str]:
        raw = self.rva_to_raw(rva)
        if raw is None:
            return None
        end = raw
        while end + 1 < min(len(self.data), raw + limit):
            if self.data[end:end + 2] == b"\x00\x00":
                break
            end += 2
        return self.data[raw:end].decode("utf-16-le", errors="replace")

    def disasm_one(self, rva: int):
        return next(self.md.disasm(self.read(rva, 16), self.va(rva)), None)

    def iter_code(
        self,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> Iterator:
        if start is None or end is None:
            ranges = self.code_sections()
        else:
            ranges = [(start, end)]
        for lo, hi in ranges:
            rva = lo
            while rva < hi:
                insn = self.disasm_one(rva)
                if insn is None:
                    rva += 1
                    continue
                yield insn
                rva += insn.size

    def immediate_refs(self, va: int, width: int = 4) -> list[int]:
        needle = int(va).to_bytes(width, "little")
        hits: list[int] = []
        for lo, hi in self.code_sections():
            raw_lo = self.rva_to_raw(lo)
            raw_hi = self.rva_to_raw(hi - 1)
            if raw_lo is None or raw_hi is None:
                continue
            start = raw_lo
            stop = raw_hi + 1
            while True:
                pos = self.data.find(needle, start, stop)
                if pos < 0:
                    break
                pair = self.raw_to_rva(pos)
                if pair:
                    hits.append(pair[0])
                start = pos + 1
        return sorted(set(hits))

    def find_wide_strings(self, regex: str) -> list[tuple[int, str]]:
        pattern = re.compile(regex.encode("utf-16-le"))
        out: list[tuple[int, str]] = []
        for match in pattern.finditer(self.data):
            pair = self.raw_to_rva(match.start())
            if pair:
                out.append((pair[0], match.group().decode("utf-16-le")))
        return out

    def find_ascii_strings(self, regex: str) -> list[tuple[int, str]]:
        pattern = re.compile(regex.encode("ascii"))
        out: list[tuple[int, str]] = []
        for match in pattern.finditer(self.data):
            pair = self.raw_to_rva(match.start())
            if pair:
                out.append((pair[0], match.group().decode("ascii")))
        return out

    def find_function_start(self, rva: int, max_back: int = 0x10000) -> int:
        """Recover a conservative MSVC function start nearest before rva."""
        lo = max(self.section_for_rva(rva).rva, rva - max_back)
        candidates: list[int] = []
        for cur in range(lo, rva + 1):
            insn = self.disasm_one(cur)
            if not insn:
                continue
            b = insn.bytes
            if (
                (b.startswith(b"\x55\x8b\xec"))
                or (b.startswith(b"\x55\x89\xe5"))
                or (b.startswith(b"\x64\xa1"))
                or (
                    len(b) >= 9
                    and b[0:3] in (b"\x6a\xff\x68", b"\x68\xff")
                    and b.find(b"\x64\xa1") < 16
                )
            ):
                candidates.append(cur)
        if not candidates:
            return rva
        # Prefer the last candidate that is still followed by a linear path to
        # the target.  A simple nearest-prologue fallback is sufficient here.
        return candidates[-1]

    def callers_to(self, target_rva: int) -> list[int]:
        target_va = self.va(target_rva)
        out: list[int] = []
        for insn in self.iter_code():
            if insn.mnemonic != "call" or not insn.operands:
                continue
            op = insn.operands[0]
            if op.type == X86_OP_IMM and op.imm == target_va:
                out.append(insn.address - self.base)
        return out

    def resolve_call(self, insn) -> Optional[str]:
        if insn.mnemonic != "call" or not insn.operands:
            return None
        op = insn.operands[0]
        if op.type == X86_OP_IMM:
            rva = self.rva(op.imm)
            if rva is not None:
                exp = self.exports.get(rva)
                if exp:
                    return "sub_%X(%s)" % (rva, exp)
                return "sub_%X" % rva
        if op.type == X86_OP_MEM and op.mem.base == 0:
            rva = self.rva(op.mem.disp)
            if rva in self.imports:
                dll, name = self.imports[rva]
                return "%s!%s" % (dll, name)
        return None

    def disassemble_function(
        self,
        entry: int,
        limit: int = 12000,
    ) -> "OrderedDict[int, object]":
        insns: OrderedDict[int, object] = OrderedDict()
        todo = deque([entry])
        seen: set[int] = set()
        while todo:
            start = todo.popleft()
            if start in seen:
                continue
            seen.add(start)
            rva = start
            while self.is_executable(rva):
                if rva in insns:
                    break
                insn = self.disasm_one(rva)
                if insn is None:
                    break
                insns[rva] = insn
                if len(insns) >= limit:
                    return insns
                mnemonic = insn.mnemonic
                if mnemonic.startswith("ret") or mnemonic in (
                    "int3", "hlt", "ud2",
                ):
                    break
                if mnemonic == "jmp":
                    if insn.operands and insn.operands[0].type == X86_OP_IMM:
                        target = self.rva(insn.operands[0].imm)
                        if target is not None and self.is_executable(target):
                            todo.append(target)
                    break
                if mnemonic in COND_JUMPS:
                    if insn.operands and insn.operands[0].type == X86_OP_IMM:
                        target = self.rva(insn.operands[0].imm)
                        if target is not None and self.is_executable(target):
                            todo.append(target)
                    rva += insn.size
                    continue
                rva += insn.size
        return insns

    def instruction_window(
        self,
        center: int,
        before: int = 0x50,
        after: int = 0x60,
        follow: bool = False,
    ) -> list[object]:
        if follow:
            fn = self.find_function_start(center)
            insns = self.disassemble_function(fn)
            return [
                insn
                for insn in insns.values()
                if center - before <= insn.address - self.base <= center + after
            ]
        out: list[object] = []
        rva = max(0, center - before)
        while rva <= center + after:
            insn = self.disasm_one(rva)
            if insn is None:
                rva += 1
                continue
            out.append(insn)
            rva += insn.size
        return out

    def format_insn(self, insn, mark_call: bool = True) -> str:
        mark = ""
        if mark_call:
            called = self.resolve_call(insn)
            if called:
                mark = "  ; %s" % called
            elif insn.operands:
                for op in insn.operands:
                    if op.type == X86_OP_IMM:
                        rva = self.rva(op.imm)
                        if rva is None:
                            continue
                        sec = self.section_for_rva(rva)
                        if sec and sec.name in (".rdata", ".data"):
                            text = self.ascii_at(rva, 160)
                            if text and len(text) >= 3:
                                mark += '  ; "%s"' % text[:100]
                                break
                            wide = self.utf16_at(rva, 240)
                            if wide and len(wide) >= 3:
                                mark += '  ; L"%s"' % wide[:100]
                                break
        return "0x%05X  %-24s %s %s%s" % (
            insn.address - self.base,
            insn.bytes.hex(),
            insn.mnemonic,
            insn.op_str,
            mark,
        )


def unique_in_order(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))
