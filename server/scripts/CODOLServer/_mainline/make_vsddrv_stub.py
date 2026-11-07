"""Build a minimal x86 VSDDrvDLLD.dll compatibility stub.

TenProtect's ClientBase.dll (0x100E9A30) does:

    LoadLibraryA("VSDDrvDLLD.dll")
    GetProcAddress(h, "DLLCreateVSDIDrvObj")
    call DLLCreateVSDIDrvObj(...)

and pops "file corrupted or missing" when GetProcAddress returns NULL.  The
real module is VMProtect-protected, so this stub provides exactly the two
expected export names.  The NULL variant returns no object; use the object
variant if the caller dereferences the result.

Usage:
  python -X utf8 CODOLServer/_mainline/make_vsddrv_stub.py <out.dll>
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path


IMAGE_BASE = 0x5B000000
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
        return b"\x33\xc0\xc3"
    return b"\xb8" + struct.pack("<I", return_value) + b"\xc3"


def build() -> bytes:
    # Two load paths exist in the TCLS shell:
    #   CreateVSDIDrvObj / ReleaseVSDIDrvObj
    #   DLLCreateVSDIDrvObj / DLLReleaseVSDIDrvObj
    # Provide both contracts so neither loader treats the module as damaged.
    named = [b"CreateVSDIDrvObj", b"ReleaseVSDIDrvObj",
             b"DLLCreateVSDIDrvObj", b"DLLReleaseVSDIDrvObj"]
    returns = [0, 1, 0, 1]
    section = bytearray(SECTION_SIZE)
    code = bytearray()
    entry_rvas = []
    for value in returns:
        entry_rvas.append(SECTION_VA + len(code))
        code.extend(function_bytes(value))
    section[:len(code)] = code

    name_rvas = []
    cursor = STRINGS_RVA
    for name in named:
        name_rvas.append(cursor)
        off = cursor - SECTION_VA
        section[off:off + len(name) + 1] = name + b"\x00"
        cursor += len(name) + 1
    dll_name_rva = cursor
    dll_name = b"VSDDrvDLLD.dll\x00"
    off = dll_name_rva - SECTION_VA
    section[off:off + len(dll_name)] = dll_name

    export = struct.pack(
        "<IIHHIIIIIII",
        0, 0, 0, 0,
        dll_name_rva,
        1,
        len(returns),
        len(named),
        FUNCS_RVA,
        NAMES_RVA,
        ORDINALS_RVA,
    )
    section[EXPORT_DIR_RVA - SECTION_VA:
            EXPORT_DIR_RVA - SECTION_VA + len(export)] = export
    section[FUNCS_RVA - SECTION_VA:
            FUNCS_RVA - SECTION_VA + len(entry_rvas) * 4] = b"".join(
                struct.pack("<I", rva) for rva in entry_rvas)
    section[NAMES_RVA - SECTION_VA:
            NAMES_RVA - SECTION_VA + len(name_rvas) * 4] = b"".join(
                struct.pack("<I", rva) for rva in name_rvas)
    section[ORDINALS_RVA - SECTION_VA:
            ORDINALS_RVA - SECTION_VA + len(named) * 2] = b"".join(
                struct.pack("<H", i) for i in range(len(named)))

    headers = bytearray(0x200)
    headers[0:2] = b"MZ"
    struct.pack_into("<I", headers, 0x3C, 0x80)
    headers[0x80:0x84] = b"PE\x00\x00"
    struct.pack_into("<HHIIIHH", headers, 0x84,
                     0x014C, 1, 0, 0, 0, 0x00E0, 0x2102)
    opt = bytearray(0xE0)
    struct.pack_into("<HBBIIIIIIIIIHHHHHHIIIIHHIIIIII", opt, 0,
                     0x10B, 0, 0, SECTION_SIZE, SECTION_SIZE, 0, 0,
                     SECTION_VA, SECTION_VA, IMAGE_BASE,
                     SECTION_VA, SECTION_RAW, 6, 0, 0, 0, 6, 0, 0,
                     align(SECTION_VA + SECTION_SIZE, 0x1000),
                     SECTION_RAW, 0, 2, 0, 0x100000, 0x1000,
                     0x100000, 0x1000, 0, 16)
    struct.pack_into("<II", opt, 0x60, EXPORT_DIR_RVA, 0x100)
    headers[0x98:0x98 + len(opt)] = opt
    section_header = struct.pack("<8sIIIIIIHHI",
                                 b".text\x00\x00\x00",
                                 SECTION_SIZE, SECTION_VA,
                                 SECTION_SIZE, SECTION_RAW,
                                 0, 0, 0, 0, 0x60000020)
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
