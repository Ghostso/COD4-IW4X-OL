from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

import capstone
import pefile
from capstone.x86 import X86_OP_IMM, X86_OP_MEM


ROOT = Path(__file__).resolve().parent
MODULES = {
    "tcls": ROOT / "COD OL" / "TCLS" / "Tenio" / "TCLS.dll",
    "clientbase": ROOT / "COD OL" / "TCLS" / "ClientBase.dll",
    "client": ROOT / "COD OL" / "TCLS" / "Client.exe",
}

TARGETS = {
    "tcls": [
        b'"%s" -q 0 %s',
        b'"%s" -q %u %s',
        b'"%s" -pp %s %s',
        b'"%s" %s %s',
        b"--tcls --tcls-uId=",
        b"CLauncher::StartGameClient",
        b"CLauncher::StartGame",
        b"Create Process",
        b"Set Cliet work directory",
        b"CMain::StartGameClient",
    ],
    "clientbase": [
        b"-q:",
        b"uid=",
        b"key=",
        b"ID=",
        b"TCLS_SHAREDMEMEMORY",
        b"TCLS_TASMEMORY_",
        b"MonitorCreateProcess",
        b"CLIENT.EXE",
        b"TASLOGIN.EXE",
        b"CreateProcessW",
        b"CreateProcessA",
        b"CreateFileMappingA",
        b"CreateFileMappingW",
        b"OpenFileMappingA",
        b"OpenFileMappingW",
        b"MapViewOfFile",
        b"CommandLineToArgvW",
    ],
    "client": [
        b"CreateProcessW",
        b"ShellExecuteExW",
        b"GetCommandLineA",
        b"client.exe",
        b"Client.exe",
        b"TCLS",
    ],
}


def encoded_needles(text: bytes):
    """Return both common encodings used by these PE string pools."""
    values = [text]
    try:
        values.append(text.decode("ascii").encode("utf-16le"))
    except UnicodeDecodeError:
        pass
    return values


def section_for(pe: pefile.PE, rva: int):
    for section in pe.sections:
        lo = section.VirtualAddress
        hi = lo + max(section.Misc_VirtualSize, section.SizeOfRawData)
        if lo <= rva < hi:
            return section
    return None


def raw_to_rva(pe: pefile.PE, raw: int):
    for section in pe.sections:
        lo = section.PointerToRawData
        hi = lo + section.SizeOfRawData
        if lo <= raw < hi:
            return section.VirtualAddress + raw - lo
    return None


def rva_to_raw(pe: pefile.PE, rva: int):
    section = section_for(pe, rva)
    if section is None:
        return None
    delta = rva - section.VirtualAddress
    if delta >= section.SizeOfRawData:
        return None
    return section.PointerToRawData + delta


def section_name(section) -> str:
    return section.Name.rstrip(b"\0").decode("latin1", "replace") if section else "?"


def ascii_at(data: bytes, pe: pefile.PE, va: int):
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    raw = rva_to_raw(pe, rva)
    if raw is None:
        return None
    end = data.find(b"\0", raw, min(len(data), raw + 512))
    if end < 0:
        return None
    blob = data[raw:end]
    if not blob:
        return ""
    if sum(32 <= x < 127 or x in (9, 10, 13) for x in blob) / len(blob) < 0.85:
        return None
    return blob.decode("latin1", "replace")


def utf16_at(data: bytes, pe: pefile.PE, va: int):
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    raw = rva_to_raw(pe, rva)
    if raw is None or raw + 1 >= len(data):
        return None
    end = raw
    limit = min(len(data) - 1, raw + 1024)
    while end + 1 < limit:
        if data[end:end + 2] == b"\0\0":
            break
        end += 2
    blob = data[raw:end]
    if not blob or len(blob) % 2:
        return None
    try:
        return blob.decode("utf-16le", "replace")
    except UnicodeDecodeError:
        return None


def string_at(data: bytes, pe: pefile.PE, va: int):
    return ascii_at(data, pe, va) or utf16_at(data, pe, va)


def make_decoder(pe: pefile.PE):
    decoder = capstone.Cs(
        capstone.CS_ARCH_X86,
        capstone.CS_MODE_64 if pe.FILE_HEADER.Machine == 0x8664 else capstone.CS_MODE_32,
    )
    decoder.detail = True
    return decoder


def iter_code(pe: pefile.PE, data: bytes, decoder):
    for section in pe.sections:
        if not section.Characteristics & 0x20000000:
            continue
        raw = data[section.PointerToRawData:section.PointerToRawData + section.SizeOfRawData]
        start = pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress
        for insn in decoder.disasm(raw, start):
            yield insn


def code_sections(pe: pefile.PE):
    return [
        section for section in pe.sections
        if section.Characteristics & 0x20000000
    ]


def raw_in_code(pe: pefile.PE, raw: int) -> bool:
    return any(
        section.PointerToRawData <= raw < section.PointerToRawData + section.SizeOfRawData
        for section in code_sections(pe)
    )


def raw_to_va(pe: pefile.PE, raw: int):
    rva = raw_to_rva(pe, raw)
    return pe.OPTIONAL_HEADER.ImageBase + rva if rva is not None else None


def instruction_covering(pe: pefile.PE, data: bytes, decoder, raw: int):
    """Decode each possible nearby start and retain instructions covering raw."""
    found = []
    for start_raw in range(max(0, raw - 15), raw + 1):
        if not raw_in_code(pe, start_raw):
            continue
        start_va = raw_to_va(pe, start_raw)
        if start_va is None:
            continue
        blob = data[start_raw:min(len(data), raw + 16)]
        for insn in decoder.disasm(blob, start_va):
            item_raw = start_raw + (insn.address - start_va)
            if item_raw <= raw < item_raw + insn.size:
                found.append(insn)
                break
            if item_raw > raw:
                break
    unique = {}
    for insn in found:
        unique[insn.address] = insn
    return list(unique.values())


def direct_code_refs(pe: pefile.PE, data: bytes, decoder, values):
    refs = []
    needles = []
    for value in values:
        if not 0 <= value <= 0xFFFFFFFF:
            continue
        needles.append((value, struct.pack("<I", value)))
    for value, needle in needles:
        pos = 0
        while True:
            pos = data.find(needle, pos)
            if pos < 0:
                break
            if raw_in_code(pe, pos):
                for insn in instruction_covering(pe, data, decoder, pos):
                    refs.append((insn, value, pos))
            pos += 1
    unique = {}
    for insn, value, raw in refs:
        unique[(insn.address, value)] = (insn, value, raw)
    return list(unique.values())


def imports(pe: pefile.PE):
    result = {}
    if not hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        return result
    for desc in pe.DIRECTORY_ENTRY_IMPORT:
        dll = desc.dll.decode("latin1", "replace")
        for imp in desc.imports:
            name = imp.name.decode("latin1", "replace") if imp.name else f"ord{imp.ordinal}"
            result[imp.address] = f"{dll}!{name}"
    return result


def operand_values(insn):
    values = []
    for operand in insn.operands:
        if operand.type == X86_OP_IMM:
            values.append((operand.imm, "imm"))
        elif operand.type == X86_OP_MEM and operand.mem.base == 0 and operand.mem.index == 0:
            values.append((operand.mem.disp, "abs-mem"))
    return values


def likely_function_start(pe: pefile.PE, data: bytes, decoder, address: int) -> int:
    section = section_for(pe, address - pe.OPTIONAL_HEADER.ImageBase)
    if section is None:
        return address
    start = pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress
    end = address
    blob = data[section.PointerToRawData:section.PointerToRawData + section.SizeOfRawData]
    base = start
    candidates = []
    for insn in decoder.disasm(blob, base):
        if insn.address > end:
            break
        b = insn.bytes
        if b.startswith(b"\x55\x8b\xec") or b.startswith(b"\x55\x89\xe5"):
            candidates.append(insn.address)
    return candidates[-1] if candidates else address


def disasm_window(pe, data, decoder, center, before=0x70, after=0x90):
    section = section_for(pe, center - pe.OPTIONAL_HEADER.ImageBase)
    if section is None:
        return []
    lo = max(pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress, center - before)
    hi = min(
        pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress + section.SizeOfRawData,
        center + after,
    )
    raw_lo = section.PointerToRawData + (lo - (pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress))
    raw_hi = raw_lo + (hi - lo)
    return list(decoder.disasm(data[raw_lo:raw_hi], lo))


def fmt_insn(insn, imp_map, pe, data):
    annotation = ""
    if insn.mnemonic == "call" and insn.operands:
        op = insn.operands[0]
        if op.type == X86_OP_MEM and op.mem.base == 0 and op.mem.index == 0:
            annotation = f" ; {imp_map.get(op.mem.disp, 'IAT?')}"
        elif op.type == X86_OP_IMM:
            annotation = f" ; -> 0x{op.imm:X}"
    for value, _ in operand_values(insn):
        text = string_at(data, pe, value)
        if text is not None and len(text) >= 3:
            annotation += f" ; STR {text!r}"
            break
    text = f"0x{insn.address:X} {insn.bytes.hex():<24} {insn.mnemonic:<8} {insn.op_str}{annotation}"
    return text.encode("ascii", "backslashreplace").decode("ascii")


def find_target_occurrences(name, pe, data):
    print(f"\n## {name}: imagebase=0x{pe.OPTIONAL_HEADER.ImageBase:X} size=0x{pe.OPTIONAL_HEADER.SizeOfImage:X}")
    decoder = make_decoder(pe)
    imp_map = imports(pe)
    print(f"imports={len(imp_map)}")
    for import_name in (
        "CreateProcessW", "CreateProcessA", "ShellExecuteExW", "GetCommandLineW",
        "GetCommandLineA", "CreateFileMappingA", "CreateFileMappingW",
        "OpenFileMappingA", "OpenFileMappingW", "MapViewOfFile", "CommandLineToArgvW",
    ):
        matches = [(va, text) for va, text in imp_map.items() if text.endswith("!" + import_name)]
        for va, text in matches:
            callers = [
                insn for insn, value, raw in direct_code_refs(
                    pe, data, decoder, [va]
                )
                if insn.mnemonic == "call"
                and insn.operands
                and insn.operands[0].type == X86_OP_MEM
                and insn.operands[0].mem.base == 0
                and insn.operands[0].mem.index == 0
                and insn.operands[0].mem.disp == va
            ]
            print(f"IMPORT {text} IAT=0x{va:X} callers={len(callers)}")
            for insn in callers:
                fn = likely_function_start(pe, data, decoder, insn.address)
                print(f"  CALL 0x{insn.address:X} fn~0x{fn:X}")
                for item in disasm_window(pe, data, decoder, insn.address, 0x90, 0x70):
                    print("    " + fmt_insn(item, imp_map, pe, data))

    for needle in TARGETS[name]:
        positions = []
        for encoded in encoded_needles(needle):
            pos = 0
            while True:
                pos = data.find(encoded, pos)
                if pos < 0:
                    break
                positions.append((pos, encoded))
                pos += 1
        positions = sorted(set(positions))
        if not positions:
            print(f"TARGET {needle!r}: NONE")
            continue
        print(f"TARGET {needle!r}: occurrences={len(positions)}")
        for raw, encoded in positions[:20]:
            rva = raw_to_rva(pe, raw)
            va = pe.OPTIONAL_HEADER.ImageBase + rva if rva is not None else None
            sec = section_name(section_for(pe, rva)) if rva is not None else "?"
            enc_name = "utf16le" if encoded.endswith(b"\0") and len(encoded) >= 2 and encoded[1] == 0 else "ascii"
            print(f"  STRING raw=0x{raw:X} rva=0x{rva:X} va=0x{va:X} section={sec} encoding={enc_name}")
            if va is None:
                continue
            refs = []
            for insn, value, raw_ref in direct_code_refs(pe, data, decoder, [va, rva]):
                kind = "va" if value == va else "rva"
                refs.append((insn, kind, value))
            print(f"  CODE_REFS={len(refs)}")
            for insn, kind, value in refs[:80]:
                fn = likely_function_start(pe, data, decoder, insn.address)
                print(f"    REF 0x{insn.address:X} kind={kind} value=0x{value:X} fn~0x{fn:X} {insn.mnemonic} {insn.op_str}")
                for item in disasm_window(pe, data, decoder, insn.address, 0x30, 0x50):
                    print("      " + fmt_insn(item, imp_map, pe, data))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("modules", nargs="*", choices=sorted(MODULES), default=sorted(MODULES))
    args = parser.parse_args()
    for name in args.modules:
        path = MODULES[name]
        pe = pefile.PE(str(path), fast_load=False)
        data = path.read_bytes()
        print(f"\n### FILE {path} sha256={__import__('hashlib').sha256(data).hexdigest()}")
        print(f"entry=0x{pe.OPTIONAL_HEADER.ImageBase + pe.OPTIONAL_HEADER.AddressOfEntryPoint:X}")
        find_target_occurrences(name, pe, data)


if __name__ == "__main__":
    main()
