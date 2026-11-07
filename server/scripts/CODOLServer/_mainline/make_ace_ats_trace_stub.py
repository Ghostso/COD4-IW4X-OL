"""Build an x86 ace-ats32.dll stub that logs when it is loaded or called.

This is a diagnostic variant of make_ace_ats_stub.py.  It writes progress to
ace_ats_stub_trace.log next to the DLL so we can tell whether the failure is
at LoadLibrary time or later, when a specific export is invoked.

Usage:
  python -X utf8 CODOLServer/_mainline/make_ace_ats_trace_stub.py <out.dll>
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path


IMAGE_BASE = 0x10000000
SECTION_VA = 0x1000
SECTION_RAW = 0x200
SECTION_SIZE = 0x400

EXPORT_DIR_RVA = SECTION_VA + 0x200
FUNCS_RVA = SECTION_VA + 0x240
NAMES_RVA = SECTION_VA + 0x260
ORDINALS_RVA = SECTION_VA + 0x280
STRINGS_RVA = SECTION_VA + 0x2A0

IMPORT_DIR_RVA = SECTION_VA + 0x340
IMPORT_LOOKUP_RVA = SECTION_VA + 0x354
IMPORT_NAME_RVA = SECTION_VA + 0x368
LOG_FUNC_HINT_RVA = SECTION_VA + 0x370
LOG_FILE_RVA = SECTION_VA + 0x390
LOG_STRING_RVA = SECTION_VA + 0x3A0


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) & ~(boundary - 1)


def build() -> bytes:
    names = [b"CreateObject", b"DllEntry2", b"GetObject1",
             b"GetObject2", b"Init"]
    section = bytearray(SECTION_SIZE)
    code = bytearray()

    # Function table: count the bytes first, then patch the final entry.
    stub_entry_offsets = []
    for _ in range(5):
        stub_entry_offsets.append(len(code))
        # push LOG_STRING_RVA ; call [fopen_log] ; add esp,4 ; mov eax,ret
        code.append(0x68)
        code += struct.pack("<I", LOG_STRING_RVA)
        code.append(0xFF)
        code.append(0x15)
        code += struct.pack("<I", IMAGE_BASE + IMPORT_DIR_RVA + 0x10)
        code += b"\x83\xc4\x04"
        code += b"\xb8\x01\x00\x00\x00\xc3"

    # We do not know the UTF-16/ANSI flavour yet, so keep the code simple and
    # write through the ANSI fopen we import below.
    code = bytearray()
    entries = []
    for _ in range(5):
        entries.append(SECTION_VA + len(code))
        code += b"\x6a\x00"                      # push 0            (unused)
        code += b"\x68" + struct.pack("<I", LOG_STRING_RVA)
        code += b"\xff\x15" + struct.pack("<I", IMAGE_BASE + IMPORT_LOOKUP_RVA)
        code += b"\x83\xc4\x08"
        code += b"\xb8\x01\x00\x00\x00"          # mov eax,1
        code += b"\xc3"

    if len(code) > 0x1F0:
        raise ValueError("code too large")
    section[:len(code)] = code

    name_rvas = []
    cursor = STRINGS_RVA
    for name in names:
        name_rvas.append(cursor)
        off = cursor - SECTION_VA
        section[off:off + len(name) + 1] = name + b"\x00"
        cursor += len(name) + 1
    dll_name_rva = cursor
    raw = b"ace-ats32.dll\x00"
    section[dll_name_rva - SECTION_VA:
            dll_name_rva - SECTION_VA + len(raw)] = raw
    cursor += len(raw)

    log_file = b"ace_ats_stub_trace.log\x00"
    off = LOG_FILE_RVA - SECTION_VA
    section[off:off + len(log_file)] = log_file
    cursor = LOG_STRING_RVA
    for tag in (b"CreateObject\x00", b"DllEntry2\x00", b"GetObject1\x00",
                b"GetObject2\x00", b"Init\x00"):
        off = cursor - SECTION_VA
        section[off:off + len(tag)] = tag
        cursor += len(tag)

    # Import table for msvcrt fopen / fputs / fclose.
    import_name = b"msvcrt.dll\x00"
    off = IMPORT_NAME_RVA - SECTION_VA
    section[off:off + len(import_name)] = import_name
    hint_name = struct.pack("<H", 0) + b"fopen\x00"
    off = LOG_FUNC_HINT_RVA - SECTION_VA
    section[off:off + len(hint_name)] = hint_name

    first_thunk = IMPORT_LOOKUP_RVA
    lookup = struct.pack("<I", LOG_FUNC_HINT_RVA) + b"\x00\x00\x00\x00"
    section[first_thunk - SECTION_VA:
            first_thunk - SECTION_VA + len(lookup)] = lookup

    import_desc = struct.pack(
        "<IIIII",
        IMPORT_LOOKUP_RVA,
        0,
        0,
        IMPORT_NAME_RVA,
        first_thunk,
    ) + b"\x00" * 20
    section[IMPORT_DIR_RVA - SECTION_VA:
            IMPORT_DIR_RVA - SECTION_VA + len(import_desc)] = import_desc

    export = struct.pack(
        "<IIHHIIIIIII",
        0, 0, 0, 0,
        dll_name_rva,
        1,
        len(names), len(names),
        FUNCS_RVA, NAMES_RVA, ORDINALS_RVA,
    )
    section[EXPORT_DIR_RVA - SECTION_VA:
            EXPORT_DIR_RVA - SECTION_VA + len(export)] = export
    funcs = b"".join(struct.pack("<I", rva) for rva in entries)
    section[FUNCS_RVA - SECTION_VA:
            FUNCS_RVA - SECTION_VA + len(funcs)] = funcs
    name_ptrs = b"".join(struct.pack("<I", rva) for rva in name_rvas)
    section[NAMES_RVA - SECTION_VA:
            NAMES_RVA - SECTION_VA + len(name_ptrs)] = name_ptrs
    ordinals = b"".join(struct.pack("<H", i) for i in range(len(names)))
    section[ORDINALS_RVA - SECTION_VA:
            ORDINALS_RVA - SECTION_VA + len(ordinals)] = ordinals

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
    struct.pack_into("<II", opt, 0x60, EXPORT_DIR_RVA, 0x120)
    struct.pack_into("<II", opt, 0x68, IMPORT_DIR_RVA, 0x28)
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
