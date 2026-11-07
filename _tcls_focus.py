from __future__ import annotations

import hashlib
import struct
from pathlib import Path

import capstone
import pefile
from capstone.x86 import X86_OP_IMM, X86_OP_MEM


ROOT = Path(__file__).resolve().parent
TCLS = ROOT / "COD OL" / "TCLS" / "Tenio" / "TCLS.dll"
CLIENTBASE = ROOT / "COD OL" / "TCLS" / "ClientBase.dll"


def load(path):
    pe = pefile.PE(str(path), fast_load=False)
    data = path.read_bytes()
    mode = capstone.CS_MODE_64 if pe.FILE_HEADER.Machine == 0x8664 else capstone.CS_MODE_32
    md = capstone.Cs(capstone.CS_ARCH_X86, mode)
    md.detail = True
    return pe, data, md


def sec_for(pe, rva):
    for sec in pe.sections:
        lo = sec.VirtualAddress
        hi = lo + max(sec.Misc_VirtualSize, sec.SizeOfRawData)
        if lo <= rva < hi:
            return sec
    return None


def raw_to_rva(pe, raw):
    for sec in pe.sections:
        if sec.PointerToRawData <= raw < sec.PointerToRawData + sec.SizeOfRawData:
            return sec.VirtualAddress + raw - sec.PointerToRawData
    return None


def rva_to_raw(pe, rva):
    sec = sec_for(pe, rva)
    if sec is None:
        return None
    delta = rva - sec.VirtualAddress
    if delta >= sec.SizeOfRawData:
        return None
    return sec.PointerToRawData + delta


def va(pe, rva):
    return pe.OPTIONAL_HEADER.ImageBase + rva


def imports(pe):
    result = {}
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for desc in pe.DIRECTORY_ENTRY_IMPORT:
            dll = desc.dll.decode("latin1", "replace")
            for imp in desc.imports:
                name = imp.name.decode("latin1", "replace") if imp.name else f"ord{imp.ordinal}"
                result[imp.address] = f"{dll}!{name}"
    return result


def text_section(pe):
    for sec in pe.sections:
        if sec.Characteristics & 0x20000000:
            return sec
    raise RuntimeError("no executable section")


def disasm_range(pe, data, md, start_va, end_va):
    sec = sec_for(pe, start_va - pe.OPTIONAL_HEADER.ImageBase)
    raw_start = rva_to_raw(pe, start_va - pe.OPTIONAL_HEADER.ImageBase)
    raw_end = rva_to_raw(pe, end_va - pe.OPTIONAL_HEADER.ImageBase - 1)
    if sec is None or raw_start is None or raw_end is None:
        raise RuntimeError(f"range outside raw section: 0x{start_va:X}-0x{end_va:X}")
    blob = data[raw_start:raw_end + 1]
    result = []
    offset = 0
    while offset < len(blob):
        insn = next(md.disasm(blob[offset:], start_va + offset), None)
        if insn is None:
            offset += 1
            continue
        result.append(insn)
        offset += insn.size
    return result


def fmt(insn, imp):
    note = ""
    if insn.mnemonic == "call" and insn.operands:
        op = insn.operands[0]
        if op.type == X86_OP_MEM and op.mem.base == 0 and op.mem.index == 0:
            note = " ; " + imp.get(op.mem.disp, f"IAT?0x{op.mem.disp:X}")
        elif op.type == X86_OP_IMM:
            note = f" ; -> 0x{op.imm:X}"
    return (f"0x{insn.address:X} {insn.bytes.hex():<24} "
            f"{insn.mnemonic:<8} {insn.op_str}{note}").encode(
                "ascii", "backslashreplace"
            ).decode("ascii")


def print_range(path, start_rva, end_rva):
    pe, data, md = load(path)
    imp = imports(pe)
    print(f"FILE {path} sha256={hashlib.sha256(data).hexdigest()}")
    print(f"RANGE RVA 0x{start_rva:X}-0x{end_rva:X} VA 0x{va(pe,start_rva):X}-0x{va(pe,end_rva):X}")
    for insn in disasm_range(pe, data, md, va(pe, start_rva), va(pe, end_rva)):
        print(fmt(insn, imp))


def find_pattern_refs(path, patterns):
    pe, data, md = load(path)
    imp = imports(pe)
    text = text_section(pe)
    text_raw = data[text.PointerToRawData:text.PointerToRawData + text.SizeOfRawData]
    print(f"FILE {path} imagebase=0x{pe.OPTIONAL_HEADER.ImageBase:X}")
    for name, value in patterns.items():
        needle = value.to_bytes(4, "little")
        refs = []
        pos = 0
        while True:
            pos = text_raw.find(needle, pos)
            if pos < 0:
                break
            refs.append(va(pe, text.VirtualAddress + pos))
            pos += 1
        print(f"VALUE {name} 0x{value:X} refs={len(refs)}")
        for ref in refs:
            start = max(va(pe, text.VirtualAddress), ref - 0x80)
            end = min(va(pe, text.VirtualAddress) + text.SizeOfRawData, ref + 0x90)
            print(f"  REF 0x{ref:X}")
            for insn in disasm_range(pe, data, md, start, end):
                print("    " + fmt(insn, imp))


def main():
    print("== TCLS commandline/launch regions ==")
    for start, end in ((0x3D780, 0x3DA80), (0x3C780, 0x3C9A0), (0x3CD20, 0x3CF10)):
        print_range(TCLS, start, end)
    print("== TCLS import refs ==")
    pe, data, md = load(TCLS)
    imp = imports(pe)
    for iat, name in sorted(imp.items()):
        if any(x in name for x in ("CreateProcessW", "GetCommandLineW", "CreateFileMapping", "OpenFileMapping", "MapViewOfFile")):
            print(f"IAT {name} 0x{iat:X}")
    print("== ClientBase dynamic/API/string regions ==")
    pe, data, md = load(CLIENTBASE)
    for raw in (0x1D3BB0, 0x1D3C00, 0x1D3CE0, 0x1D7200, 0x1D7318, 0x1F110C, 0x1F1370):
        rva = raw_to_rva(pe, raw)
        print(f"RAW 0x{raw:X} -> RVA 0x{rva:X} VA 0x{va(pe,rva):X} section={sec_for(pe,rva).Name!r}")
        print(data[raw:raw + 320].hex(" "))
    print("== ClientBase import/API values ==")
    imp = imports(pe)
    for iat, name in sorted(imp.items()):
        if any(x in name for x in ("LoadLibrary", "GetProcAddress", "CreateProcess", "GetCommandLine", "FileMapping", "OpenFileMapping", "MapViewOfFile", "CommandLineToArgv", "CreatePipe", "ShellExecute")):
            print(f"IAT {name} 0x{iat:X}")
    find_pattern_refs(CLIENTBASE, {
        "ascii_TCLS_shared_raw_as_rva": 0x1D5000,
        "ascii_CLIENT_raw_as_rva": 0x1D8718,
        "ascii_TASLOGIN_raw_as_rva": 0x1D8724,
    })


if __name__ == "__main__":
    main()
