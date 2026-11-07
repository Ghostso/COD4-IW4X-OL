#!/usr/bin/env python3
"""EX-051 static scan for IIPS initialization environment contract.

Read-only static analysis of iips.dll: PE metadata, exports, imports,
relevant strings, direct indirect API call sites, and simple branch
decoding around import calls.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32


ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
IIPS = ROOT / r"COD OL\IIPS\iips.dll"


def section_data(pe, name):
    for s in pe.sections:
        n = s.Name.rstrip(b"\0").decode("latin1", "ignore")
        if n == name:
            return bytes(s.data), s.VirtualAddress, s.Misc_VirtualSize
    raise KeyError(name)


def collect_iat(pe):
    iat_to_name = {}
    name_to_iat = {}
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        dll = entry.dll.decode("latin1", "ignore")
        for imp in entry.imports:
            nm = imp.name.decode("latin1", "ignore") if imp.name else f"ord{imp.ordinal}"
            full = dll + "!" + nm
            iat_to_name[imp.address] = full
            name_to_iat.setdefault((dll, nm), []).append(imp.address)
    return iat_to_name, name_to_iat


def disasm_range(code, base, start_va, end_va):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    return list(md.disasm(code, base, start_va, end_va))


def get_insns(code, base, raw_va):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    return list(md.disasm(code, base, raw_va))


def search_bytes(data, pattern):
    out = []
    start = 0
    while True:
        i = data.find(pattern, start)
        if i < 0:
            break
        out.append(i)
        start = i + 1
    return out


def va_to_file(pe, va):
    for s in pe.sections:
        start = pe.OPTIONAL_HEADER.ImageBase + s.VirtualAddress
        end = start + max(s.Misc_VirtualSize, s.SizeOfRawData)
        if start <= va < end:
            off = s.PointerToRawData + (va - start)
            if off < len(pe.__data__):
                return off
    return None


def file_to_va(pe, file_off):
    for s in pe.sections:
        if s.PointerToRawData <= file_off < s.PointerToRawData + s.SizeOfRawData:
            return pe.OPTIONAL_HEADER.ImageBase + s.VirtualAddress + (file_off - s.PointerToRawData)
    return None


def main():
    data = IIPS.read_bytes()
    sha = hashlib.sha256(data).hexdigest().upper()
    pe = pefile.PE(str(IIPS))
    pe.parse_data_directories()
    base = pe.OPTIONAL_HEADER.ImageBase
    print(f"IIPS_PATH={IIPS}")
    print(f"IIPS_SIZE={len(data)}")
    print(f"IIPS_SHA256={sha}")
    print(f"IMAGEBASE=0x{base:x} ENTRY=0x{pe.OPTIONAL_HEADER.AddressOfEntryPoint:x}")

    print("\nSECTIONS")
    for s in pe.sections:
        print(f"{s.Name.decode('latin1','ignore').strip(chr(0))} VA=0x{s.VirtualAddress:x} VSZ=0x{s.Misc_VirtualSize:x} RAW=0x{s.PointerToRawData:x} RASZ=0x{s.SizeOfRawData:x}")

    print("\nEXPORTS")
    if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            nm = e.name.decode("latin1", "ignore") if e.name else f"ord{e.ordinal}"
            print(f"0x{e.address:x} {nm}")

    print("\nIMPORTS")
    iat_to_name, _ = collect_iat(pe)
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        dll = entry.dll.decode("latin1", "ignore")
        print("DLL", dll)
        for imp in entry.imports:
            nm = imp.name.decode("latin1", "ignore") if imp.name else f"ord{imp.ordinal}"
            print(f"0x{imp.address:x} {nm} ord={imp.ordinal}")

    print("\nRELEVANT_STRINGS")
    interesting = [
        b"IIPSHostApp.exe",
        b"IIPSERR_CACHE_INIT",
        b"IIPSERR_ERROR_INIT",
        b"LaunchIIPSHostApp failed",
        b"Failed to get function CreateIFSLibDll",
        b"Failed to create ifs lib",
        b"Failed to get proc DestoryIFSLibDll",
        b"CreateIFSLibDll",
        b"DestoryIFSLibDll",
        b"ifs2.dll",
        b"IFS2\\",
        b"IIPS/IIPSHostApp.ini",
        b"IIPS/IIPSHostApp.exe",
        b"Global\\IIPSShareState_MMF_",
        b"Global\\IIPSShareState_Mutex_",
        b"GetResourceManagerII",
        b"ReleaseResourceManagerII",
        b"Environment List Box",
        b"iipsinit",
        b"IFSDllVerifyApiCompatable",
    ]
    for pat in interesting:
        idxs = search_bytes(data, pat)
        if idxs:
            vas = []
            for off in idxs[:20]:
                va = file_to_va(pe, off)
                vas.append(f"0x{va:x} (file 0x{off:x})" if va else f"file 0x{off:x}")
            print(f"{pat.decode('latin1','ignore')} hits={len(idxs)}: " + ", ".join(vas))

    print("\nINDIRECT_CALL_SITES")
    text, text_va, text_size = None, None, None
    for s in pe.sections:
        if s.Name.rstrip(b"\0") == b".text":
            text = s.get_data()
            text_va = base + s.VirtualAddress
            text_size = s.Misc_VirtualSize
            break
    code = text
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    insns = list(md.disasm(code, text_va))
    count = 0
    for ins in insns:
        if ins.mnemonic != "call":
            continue
        # direct E8 call or indirect via register/mem
        if "[" not in ins.op_str:
            continue
        # only indirect memory IAT call
        if ins.op_str.startswith("dword ptr ["):
            m = re.search(r"0x([0-9a-fA-F]{8})", ins.op_str)
            if not m:
                continue
            target = int(m.group(1), 16)
            api = iat_to_name.get(target, hex(target))
            if "!" not in api:
                continue
            count += 1
            # decode following 10 instructions
            tail = []
            idx = insns.index(ins) + 1
            for t in insns[idx:idx+12]:
                mark = ""
                if t.mnemonic in ("test", "cmp"):
                    mark = "<--"
                if t.mnemonic.startswith("j"):
                    mark = "<--"
                tail.append((t.address, t.mnemonic, t.op_str, mark))
            print(f"CALL {count} {hex(ins.address)} {api}")
            for a,m,o,mark in tail:
                print(f"  {hex(a)} {m} {o} {mark}")

    print("\nSTRING_XREF_TEXT")
    # find 4-byte little endian VA references in .text
    text_raw = pe.sections[0].PointerToRawData
    text_blob = data[text_raw:text_raw+len(code)]
    for pat in interesting:
        offs = search_bytes(data, pat)
        for off in offs:
            va = file_to_va(pe, off)
            if not va:
                continue
            pat_bytes = int(va).to_bytes(4, "little")
            refs = search_bytes(text_blob, pat_bytes)
            if refs:
                for rf in refs[:20]:
                    ref_va = text_va + rf
                    print(f"{pat.decode('latin1','ignore')} VA={hex(va)} ref_text={hex(ref_va)}")


if __name__ == "__main__":
    main()
