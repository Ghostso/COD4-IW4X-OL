"""Build a minimal x86 ace-ats32.dll compatibility stub.

The original ace-ats32.dll is a VMProtect-protected anti-tamper module.  For
the offline single-player target we do not need it.  This script emits a tiny
PE32 DLL with the same five exported names and no imports or CRT dependency.

Usage:
  python -X utf8 CODOLServer/_mainline/make_ace_ats_stub.py <out.dll>
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path


# Base.dll also uses 0x10000000.  This stub has no absolute in-image
# references, so a different preferred base is safe and avoids a relocation
# collision that presents as ERROR_MOD_NOT_FOUND.
IMAGE_BASE = 0x5A000000
SECTION_VA = 0x1000
SECTION_RAW = 0x200
SECTION_SIZE = 0x200

EXPORT_DIR_RVA = SECTION_VA + 0x100
FUNCS_RVA = SECTION_VA + 0x130
NAMES_RVA = SECTION_VA + 0x150
ORDINALS_RVA = SECTION_VA + 0x170
STRINGS_RVA = SECTION_VA + 0x190


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) & ~(boundary - 1)


def function_bytes(return_value: int) -> bytes:
    if return_value == 0:
        return b"\x33\xc0\xc3"              # xor eax,eax; ret
    return b"\xb8" + struct.pack("<I", return_value) + b"\xc3"


def build() -> bytes:
    names = [b"CreateObject", b"DllEntry2", b"GetObject1",
             b"GetObject2", b"Init"]
    returns = [0, 1, 0, 1, 1]

    code = bytearray()
    function_rvas = []
    for value in returns:
        function_rvas.append(SECTION_VA + len(code))
        code.extend(function_bytes(value))
    if len(code) > 0x100:
        raise ValueError("code grew past reserved export area")

    section = bytearray(SECTION_SIZE)
    section[:len(code)] = code

    name_rvas = []
    string_cursor = STRINGS_RVA
    for name in names:
        name_rvas.append(string_cursor)
        off = string_cursor - SECTION_VA
        section[off:off + len(name) + 1] = name + b"\x00"
        string_cursor += len(name) + 1

    dll_name_rva = string_cursor
    dll_name = b"ace-ats32.dll\x00"
    off = dll_name_rva - SECTION_VA
    section[off:off + len(dll_name)] = dll_name

    export = struct.pack(
        "<IIHHIIIIIII",
        0,                       # Characteristics
        0,                       # TimeDateStamp
        0, 0,                    # Major/Minor version
        dll_name_rva,            # Name
        1,                       # Ordinal base
        len(names),              # NumberOfFunctions
        len(names),              # NumberOfNames
        FUNCS_RVA,               # AddressOfFunctions
        NAMES_RVA,               # AddressOfNames
        ORDINALS_RVA,            # AddressOfNameOrdinals
    )
    section[EXPORT_DIR_RVA - SECTION_VA:
            EXPORT_DIR_RVA - SECTION_VA + len(export)] = export

    funcs = b"".join(struct.pack("<I", rva) for rva in function_rvas)
    section[FUNCS_RVA - SECTION_VA:
            FUNCS_RVA - SECTION_VA + len(funcs)] = funcs

    name_ptrs = b"".join(struct.pack("<I", rva) for rva in name_rvas)
    section[NAMES_RVA - SECTION_VA:
            NAMES_RVA - SECTION_VA + len(name_ptrs)] = name_ptrs

    ordinals = b"".join(struct.pack("<H", i) for i in range(len(names)))
    section[ORDINALS_RVA - SECTION_VA:
            ORDINALS_RVA - SECTION_VA + len(ordinals)] = ordinals

    size_of_image = align(SECTION_VA + SECTION_SIZE, 0x1000)
    headers = bytearray(0x200)
    headers[0:2] = b"MZ"
    struct.pack_into("<I", headers, 0x3C, 0x80)
    headers[0x80:0x84] = b"PE\x00\x00"

    # IMAGE_FILE_HEADER
    struct.pack_into(
        "<HHIIIHH",
        headers, 0x84,
        0x014C,                  # IMAGE_FILE_MACHINE_I386
        1,                       # NumberOfSections
        0,
        0,
        0,
        0x00E0,                  # SizeOfOptionalHeader
        0x2102,                  # EXECUTABLE_IMAGE | 32BIT_MACHINE | DLL
    )

    # IMAGE_OPTIONAL_HEADER32
    opt = bytearray(0xE0)
    struct.pack_into(
        "<HBBIIIIIIIIIHHHHHHIIIIHHIIIIII",
        opt, 0,
        0x10B,                   # PE32
        0, 0,
        SECTION_SIZE,
        SECTION_SIZE,
        0,
        0,                       # AddressOfEntryPoint
        SECTION_VA,              # BaseOfCode
        SECTION_VA,              # BaseOfData
        IMAGE_BASE,
        SECTION_VA,              # SectionAlignment
        SECTION_RAW,             # FileAlignment
        6, 0,                    # OS version
        0, 0,                    # Image version
        6, 0,                    # Subsystem version
        0,
        size_of_image,
        SECTION_RAW,             # SizeOfHeaders
        0,
        2,                       # IMAGE_SUBSYSTEM_WINDOWS_GUI
        0,
        0x100000,                # SizeOfStackReserve
        0x1000,
        0x100000,                # SizeOfHeapReserve
        0x1000,
        0,
        16,
    )
    # DataDirectory[0] = export table
    struct.pack_into("<II", opt, 0x60, EXPORT_DIR_RVA, 0x120)
    headers[0x98:0x98 + len(opt)] = opt

    # IMAGE_SECTION_HEADER
    section_header = struct.pack(
        "<8sIIIIIIHHI",
        b".text\x00\x00\x00",
        SECTION_SIZE,
        SECTION_VA,
        SECTION_SIZE,
        SECTION_RAW,
        0, 0,
        0, 0,
        0x60000020,              # CODE | INITIALIZED_DATA | READ
    )
    headers[0x178:0x178 + len(section_header)] = section_header
    return bytes(headers + section)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(build())
    print("wrote %s (%d bytes)" % (out, out.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
