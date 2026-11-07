"""Build an x86 VSDDrvDll.dll stub that returns a non-NULL fake object.

The diagnostic NULL variant proved that replacing VSDDrvDll.dll prevents
ACE-DRV32.dll from loading, but the client still showed a modal error.  This
variant returns a small object whose vtable contains many failure-returning
methods.  It is still diagnostic-only and never loads a driver.

Usage:
  python -X utf8 CODOLServer/_mainline/make_vsddrv_object_stub.py <out.dll>
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path


IMAGE_BASE = 0x5B000000
SECTION_VA = 0x1000
SECTION_RAW = 0x200
SECTION_SIZE = 0x800

RET0_RVA = SECTION_VA + 0x00
RET1_RVA = SECTION_VA + 0x03
CREATE_RVA = SECTION_VA + 0x06
RELEASE_RVA = SECTION_VA + 0x0C
UNNAMED3_RVA = SECTION_VA + 0x12
UNNAMED4_RVA = SECTION_VA + 0x18

VTABLE_RVA = SECTION_VA + 0x100
OBJECT_RVA = SECTION_VA + 0x300

EXPORT_DIR_RVA = SECTION_VA + 0x400
FUNCS_RVA = SECTION_VA + 0x440
NAMES_RVA = SECTION_VA + 0x460
ORDINALS_RVA = SECTION_VA + 0x480
STRINGS_RVA = SECTION_VA + 0x4A0


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) & ~(boundary - 1)


def ret(value: int) -> bytes:
    if value == 0:
        return b"\x33\xc0\xc3"
    return b"\xb8" + struct.pack("<I", value) + b"\xc3"


def build() -> bytes:
    section = bytearray(SECTION_SIZE)
    code = bytearray()
    code += ret(0)
    code += ret(1)
    code += b"\xb8" + struct.pack("<I", IMAGE_BASE + OBJECT_RVA) + b"\xc3"
    code += ret(1)
    code += ret(1)
    code += ret(1)
    section[:len(code)] = code

    # 128 methods returning 1: a slightly more permissive fake object, since
    # the NULL variant showed the caller dereferences the result.
    vtable = b"".join(struct.pack("<I", IMAGE_BASE + RET1_RVA)
                      for _ in range(128))
    section[VTABLE_RVA - SECTION_VA:
            VTABLE_RVA - SECTION_VA + len(vtable)] = vtable
    struct.pack_into("<I", section, OBJECT_RVA - SECTION_VA,
                     IMAGE_BASE + VTABLE_RVA)

    named = [b"DLLCreateVSDIDrvObj", b"DLLReleaseVSDIDrvObj"]
    entry_rvas = [CREATE_RVA, RELEASE_RVA, UNNAMED3_RVA, UNNAMED4_RVA]
    name_ptrs = []
    cursor = STRINGS_RVA
    for name in named:
        name_ptrs.append(cursor)
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
        len(entry_rvas),
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
            NAMES_RVA - SECTION_VA + len(name_ptrs) * 4] = b"".join(
                struct.pack("<I", rva) for rva in name_ptrs)
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
